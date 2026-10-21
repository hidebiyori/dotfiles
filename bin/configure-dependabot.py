#!/usr/bin/env python3
"""Keep Dependabot alerts enabled and disable security update PRs via GitHub CLI."""

import argparse
import json
import os
import re
import subprocess
import sys
import time


class ConfigError(Exception):
    pass


class GitHub:
    def __init__(self, repository):
        self.base = f"repos/{repository}"
        self.requested = False

    def request(self, method, suffix="", expected=(200,)):
        # Leave at least one second after each completed request. Do not retry
        # permission errors or rate limits, or print API bodies / gh diagnostics.
        if self.requested:
            time.sleep(1)
        self.requested = True
        try:
            result = subprocess.run(
                ["gh", "api", "--hostname", "github.com", "--include",
                 "--method", method, "-H", "Accept: application/vnd.github+json",
                 "-H", "X-GitHub-Api-Version: 2022-11-28", self.base + suffix],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                encoding="utf-8", timeout=30,
                env={**os.environ, "GH_PROMPT_DISABLED": "1"})
        except FileNotFoundError:
            raise ConfigError("導入済みの GitHub CLI (gh) が必要です") from None
        except (OSError, subprocess.TimeoutExpired):
            raise ConfigError("GitHub API に接続できませんでした") from None
        response = re.fullmatch(
            r"HTTP/\S+ (\d{3})[^\n]*\n.*?\n\n(.*)", result.stdout, re.DOTALL)
        if response is None:
            raise ConfigError("GitHub API の HTTP 応答を確認できませんでした")
        status = int(response[1])
        if status not in expected or (result.returncode and status < 400):
            raise ConfigError(f"GitHub API が失敗しました (HTTP {status})")
        return status, response[2]


def object_body(body):
    try:
        value = json.loads(body)
    except ValueError:
        raise ConfigError("GitHub API の JSON 応答を確認できませんでした") from None
    if not isinstance(value, dict):
        raise ConfigError("GitHub API の JSON オブジェクトを確認できませんでした")
    return value


def security_updates(api):
    status, body = api.request("GET", "/automated-security-fixes", (200, 404))
    if status == 404:
        return False
    enabled = object_body(body).get("enabled")
    if not isinstance(enabled, bool):
        raise ConfigError("Dependabot security updates の状態を確認できませんでした")
    return enabled


def alerts(api):
    status, _ = api.request("GET", "/vulnerability-alerts", (204, 404))
    return status == 204


def verify_state(api, read_state, expected, message):
    # Successful writes can briefly be followed by the old state. Retry only
    # these reads; API errors still stop immediately and writes are never retried.
    for attempt in range(3):
        if read_state(api) == expected:
            return
        if attempt < 2:
            time.sleep(2)
    raise ConfigError(message)


def configure(repository, write=False):
    api = GitHub(repository)
    _, body = api.request("GET")
    metadata = object_body(body)
    # A 404 from a feature endpoint means disabled only after repository access
    # and admin permission have been established. Reject redirects to other repos.
    full_name = metadata.get("full_name")
    if not isinstance(full_name, str) or full_name.lower() != repository.lower():
        raise ConfigError("対象リポジトリ名を確認できませんでした")
    permissions = metadata.get("permissions")
    if not isinstance(permissions, dict) or permissions.get("admin") is not True:
        raise ConfigError("対象リポジトリの管理権限が必要です")
    updates_enabled = security_updates(api)
    alerts_enabled = alerts(api)
    print(f"REPOSITORY {repository}")
    print("Dependabot security updates: " + ("enabled" if updates_enabled else "disabled"))
    print("Dependabot alerts: " + ("enabled" if alerts_enabled else "disabled"))
    if not write:
        print("PLAN: security updates を停止し、alerts を有効にする")
        print("プレビューのみ。反映するには --write を指定してください")
        return
    if updates_enabled:
        api.request("DELETE", "/automated-security-fixes", (204,))
        # Disable automatic PRs before enabling alerts, which may discover issues.
        verify_state(api, security_updates, False,
                     "Dependabot security updates の停止を確認できませんでした")
    if not alerts_enabled:
        api.request("PUT", "/vulnerability-alerts", (204,))
    if updates_enabled or not alerts_enabled:
        message = "設定が反映されていません。管理ポリシーと権限を確認してください"
        verify_state(api, security_updates, False, message)
        verify_state(api, alerts, True, message)
    print("VERIFIED: security updates=disabled, alerts=enabled")
    print("通常更新 PR・auto-triage rules・メール通知は文書のチェックリストで確認してください")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="対象の OWNER/REPO (github.com)")
    parser.add_argument("--write", action="store_true", help="GitHub 側の設定を反映し再確認する")
    args = parser.parse_args(argv)
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}",
                         args.repository) or args.repository.split("/")[-1] in (".", "..")):
        parser.error("repository は URL ではなく OWNER/REPO で指定してください")
    try:
        configure(args.repository, args.write)
        return 0
    except ConfigError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
