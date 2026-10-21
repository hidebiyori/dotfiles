import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin/configure-dependabot.py"
SPEC = importlib.util.spec_from_file_location("configure_dependabot", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DependabotConfigTests(unittest.TestCase):
    def setUp(self):
        self.updates = True
        self.alerts = False
        self.admin = True
        self.calls = []
        self.overrides = {}
        self.ignore_delete = False
        self.ignore_enable_alerts = False
        self.leak = "private-fixture-response"
        self.sleeps = self.enterContext(patch.object(MODULE.time, "sleep"))
        self.enterContext(patch.object(MODULE.subprocess, "run", side_effect=self.gh))

    def gh(self, command, **kwargs):
        self.assertEqual(command[:5], ["gh", "api", "--hostname", "github.com", "--include"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        method = command[command.index("--method") + 1]
        endpoint = command[-1]
        call = (method, endpoint)
        self.calls.append(call)
        if call in self.overrides:
            return self.overrides[call]
        if endpoint == "repos/example/project":
            status, body = 200, {"full_name": "example/project", "permissions": {"admin": self.admin}}
        elif endpoint.endswith("/automated-security-fixes"):
            if method == "DELETE":
                if not self.ignore_delete:
                    self.updates = False
                status, body = 204, None
            else:
                status, body = ((200, {"enabled": True, "paused": False}) if self.updates
                                else (404, {"message": self.leak}))
        elif endpoint.endswith("/vulnerability-alerts"):
            if method == "PUT":
                if not self.ignore_enable_alerts:
                    self.alerts = True
                status, body = 204, None
            else:
                status, body = (204, None) if self.alerts else (404, {"message": self.leak})
        else:
            self.fail("Unexpected API endpoint")
        return self.response(status, body)

    def response(self, status, body=None):
        text = json.dumps(body) if body is not None else ""
        return subprocess.CompletedProcess([], int(status >= 400),
                                           f"HTTP/2.0 {status} status\ncontent-type: application/json\n\n{text}",
                                           self.leak)

    def run_main(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = MODULE.main(["example/project", *args])
        self.assertNotIn(self.leak, stdout.getvalue() + stderr.getvalue())
        for delay in self.sleeps.call_args_list:
            self.assertGreaterEqual(delay.args[0], 1)
        self.assertEqual(self.sleeps.call_count, max(0, len(self.calls) - 1))
        return status, stdout.getvalue(), stderr.getvalue()

    def test_preview_only_reads_settings(self):
        status, stdout, _ = self.run_main()
        self.assertEqual(status, 0)
        self.assertIn("PLAN", stdout)
        self.assertTrue(self.updates)
        self.assertFalse(self.alerts)
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_write_disables_prs_before_enabling_alerts_and_verifies_both(self):
        status, stdout, _ = self.run_main("--write")
        self.assertEqual(status, 0)
        self.assertFalse(self.updates)
        self.assertTrue(self.alerts)
        self.assertIn("VERIFIED", stdout)
        delete = self.calls.index(("DELETE", "repos/example/project/automated-security-fixes"))
        enable = self.calls.index(("PUT", "repos/example/project/vulnerability-alerts"))
        self.assertLess(delete, enable)
        self.assertEqual(self.calls[delete + 1], ("GET", "repos/example/project/automated-security-fixes"))
        self.assertEqual([method for method, _ in self.calls[-2:]], ["GET", "GET"])

    def test_already_configured_write_is_read_only(self):
        self.updates, self.alerts = False, True
        status, stdout, _ = self.run_main("--write")
        self.assertEqual(status, 0)
        self.assertIn("VERIFIED", stdout)
        self.assertEqual([method for method, _ in self.calls], ["GET"] * 3)

    def test_missing_repository_or_admin_permission_is_not_treated_as_disabled(self):
        self.overrides[("GET", "repos/example/project")] = self.response(404, {"message": self.leak})
        self.assertEqual(self.run_main("--write")[0], 2)
        self.assertEqual(len(self.calls), 1)
        self.calls.clear()
        self.sleeps.reset_mock()
        self.overrides.clear()
        self.admin = False
        self.assertEqual(self.run_main("--write")[0], 2)
        self.assertEqual(len(self.calls), 1)

    def test_renamed_repository_is_rejected_before_any_feature_request(self):
        self.overrides[("GET", "repos/example/project")] = self.response(
            200, {"full_name": "another/project", "permissions": {"admin": True}})
        self.assertEqual(self.run_main("--write")[0], 2)
        self.assertEqual(len(self.calls), 1)

    def test_forbidden_and_rate_limited_requests_stop_without_retry(self):
        for code in (403, 429, 503):
            with self.subTest(code=code):
                self.calls.clear()
                self.sleeps.reset_mock()
                self.overrides[("GET", "repos/example/project/automated-security-fixes")] = self.response(
                    code, {"message": self.leak})
                status, _, stderr = self.run_main("--write")
                self.assertEqual(status, 2)
                self.assertIn(str(code), stderr)
                self.assertEqual(len(self.calls), 2)

    def test_unsuccessful_disable_does_not_enable_alerts_or_claim_success(self):
        self.ignore_delete = True
        status, stdout, _ = self.run_main("--write")
        self.assertEqual(status, 2)
        self.assertNotIn("VERIFIED", stdout)
        self.assertFalse(self.alerts)
        self.assertNotIn("PUT", [method for method, _ in self.calls])

    def test_unsuccessful_alert_enable_is_detected(self):
        self.ignore_enable_alerts = True
        status, stdout, _ = self.run_main("--write")
        self.assertEqual(status, 2)
        self.assertNotIn("VERIFIED", stdout)

    def test_malformed_response_or_transport_error_does_not_disclose_diagnostics(self):
        for response in (self.response(200, [self.leak]),
                         subprocess.CompletedProcess([], 0, "HTTP/2 200 OK\n\n" + self.leak, self.leak),
                         subprocess.CompletedProcess([], 1, "", self.leak)):
            with self.subTest(response=response):
                self.calls.clear()
                self.sleeps.reset_mock()
                self.overrides[("GET", "repos/example/project")] = response
                self.assertEqual(self.run_main("--write")[0], 2)
                self.assertEqual(len(self.calls), 1)

    def test_url_and_path_input_are_rejected_without_network(self):
        for repository in ("https://github.com/example/project", "example/project/extra", "example/.."):
            with self.subTest(repository=repository), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    MODULE.main([repository, "--write"])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
