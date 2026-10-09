# Chromebook の Chrome を Playwright MCP で接続する

Linux 開発環境から ChromeOS 側の Chrome を使うときの代替手順。
2026-10-09 にウェブ目録と Pluto のチャットで接続を確認した。
Playwright MCP の拡張接続方式を使い、導入済みツールだけで準備する。
他の OS や別バージョンの MCP で同じ動作になることは未確認。

## 適用する状況

通常の `browser_tabs` 等が `Playwright Extension not found` を返す一方、
ChromeOS 側の Chrome には Playwright Extension が導入されている場合に使う。
Linux 側の Chrome のプロファイルを調べたエラーだけでは、ChromeOS 側の拡張の有無は分からない。
通常の接続が使える場合は、そちらを優先する。

既存の接続はチャットごとの状態を持つ。別チャットの Node REPL の変数や MCP クライアントは継承されない。
他のチャットが使用中のプロセスを終了したり、同じ調査タブを選択して接続を奪ったりしない。
別プロジェクトでは、その対象サイトのタブを選択する。

## 1. 導入済みの実行環境を確認する

`~/.codex/config.toml` の Playwright MCP の `command` と `args` を確認する。
独自の `CODEX_HOME` を使っている場合は、そのディレクトリの設定を確認する。
設定全体や環境変数の値を出力せず、必要な実行パスだけを確認する。
未導入の場合はこの手順だけでは接続できない。自動でインストールしない。

この端末で確認したパスは次のとおり。Node の更新や MCP の配置変更時には実環境に合わせる。

- Node: `/home/hidebiyori/.local/share/mise/installs/node/24.21.0/bin/node`
- MCP CLI: `/home/hidebiyori/.local/share/playwright-mcp/node_modules/@playwright/mcp/cli.js`
- Chrome 拡張 ID: `mmlmfjhmonkocbjadbfplnigmagldckm`

## 2. Node REPL でチャット専用のクライアントを起動する

永続的な `node_repl` ツールで次の JavaScript を実行する。
`node_repl` が使えない環境ではこのコードをそのまま実行できないため、別の永続クライアントが必要になる。
通常の短命なコマンド実行や `functions.exec` の JavaScript 内だけで子プロセスを管理しない。

`--executable-path` に渡す小さなスクリプトは、Chrome を起動する代わりに接続 URL を保存する。
URL 中の中継先ホストを `127.0.0.1` にそろえ、ChromeOS 側の Chrome で開く。
一時ディレクトリはリポジトリ外に作成し、他の利用者に公開しない。

```javascript
var pwFs = await import('node:fs/promises');
var pwCp = await import('node:child_process');
var pwNode = '/home/hidebiyori/.local/share/mise/installs/node/24.21.0/bin/node';
var pwCli = '/home/hidebiyori/.local/share/playwright-mcp/node_modules/@playwright/mcp/cli.js';
var pwDirectory = await pwFs.mkdtemp(nodeRepl.homeDir + '/.codex/playwright-connect-');
await pwFs.chmod(pwDirectory, 0o700);
await pwFs.writeFile(pwDirectory + '/open-connection.mjs', `#!${pwNode}
import { writeFileSync } from 'node:fs';
const raw = process.argv.find(a => a.startsWith('chrome-extension://'));
if (!raw) process.exit(1);
const url = new URL(raw);
const relay = new URL(url.searchParams.get('mcpRelayUrl'));
relay.hostname = '127.0.0.1';
url.searchParams.set('mcpRelayUrl', relay.href);
writeFileSync(new URL('./connection-url.txt', import.meta.url), url.href, { mode: 0o600 });
`, { mode: 0o700 });
var pwClient = pwCp.spawn(pwNode, [pwCli, '--extension',
  '--executable-path', pwDirectory + '/open-connection.mjs',
  '--snapshot-mode', 'none'], { stdio: ['pipe', 'pipe', 'pipe'] });
var pwPending = new Map();
var pwSequence = 0;
var pwBuffer = '';
var pwState = { errors: '', connection: null };
pwClient.stderr.on('data', data => pwState.errors += data.toString());
pwClient.stdout.on('data', data => {
  pwBuffer += data.toString();
  var lines = pwBuffer.split('\n');
  pwBuffer = lines.pop();
  for (var line of lines) {
    try {
      var message = JSON.parse(line);
      if (pwPending.has(message.id)) {
        pwPending.get(message.id)(message);
        pwPending.delete(message.id);
      }
    } catch {}
  }
});
var pwRpc = (method, params) => new Promise(resolve => {
  var id = ++pwSequence;
  pwPending.set(id, resolve);
  pwClient.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
});
await pwRpc('initialize', { protocolVersion: '2024-11-05', capabilities: {},
  clientInfo: { name: 'project-browser-diagnostics', version: '1' } });
pwClient.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
var pwTools = (await pwRpc('tools/list', {})).result.tools;
var pwRunTool = pwTools.find(tool => tool.name.includes('run_code'));
if (!pwRunTool) throw new Error('Playwright run_code tool is unavailable');
pwRpc('tools/call', { name: pwRunTool.name,
  arguments: { code: 'async(page) => ({ url: page.url(), title: await page.title() })' }
}).then(result => pwState.connection = result);
nodeRepl.write({ directory: pwDirectory, waitingForConnection: true });
```

RPC の応答が返らない場合は、長時間の待機を繰り返さず、`pwClient.exitCode` と
`pwState.errors` を必要な範囲だけ確認する。チャットの Node REPL をリセットすると状態は失われる。

## 3. 接続 URL をユーザーに開いてもらう

別の Node REPL 呼び出しで、生成された URL を取得する。
ファイルがまだなければ、プロセスの状態を確認して少し待ってから再読取する。

```javascript
nodeRepl.write(await pwFs.readFile(pwDirectory + '/connection-url.txt', 'utf8'));
```

ユーザーに、この URL を ChromeOS 側の Chrome のアドレス欄に貼り付け、
対象プロジェクトのタブを選択してもらう。拡張の接続画面での選択はユーザー操作が必要。
表示するのは今回の接続に必要な URL だけにする。
接続 URL・ポート・接続 ID は毎回変わるため、文書・コミット・別チャットへ流用しない。

## 4. 接続結果と対象タブを確認する

```javascript
nodeRepl.write({ connection: pwState.connection, exited: pwClient.exitCode !== null });
```

`connection: null` は接続待ち。RPC の `error` や `result.isError` は成功として扱わない。
接続直後の移動で `Execution context was destroyed` が出た場合は、
リロードせずに次の読取を再試行し、実際の URL・タイトルを確認する。

```javascript
nodeRepl.write(await pwRpc('tools/call', { name: pwRunTool.name,
  arguments: { code: 'async(page) => ({ url: page.url(), title: await page.title() })' }
}));
```

以後は `pwTools` で取得した名前・スキーマを確認して `tools/call` を実行する。
`browser_run_code_unsafe` 内は制限された実行環境なので、Node や `URL` 等のグローバルがあると仮定しない。
サイトへの操作前に対象 URL を確認する。リロード・移動は編集中の入力を失わせる可能性がある。
通信エラーの調査では、接続前の通信が取得できるとは限らない。
必要な再読込の前に `requestfailed` を監視し、通信先・エラーを確認する。
広告などの URL のクエリ・フラグメントや認証値を不要に出力・保存しない。

## 終了と引き継ぎ

接続を維持する依頼がある間はクライアントを終了しない。
使い終わったら、このチャットで起動した `pwClient` だけを終了する。
他の MCP プロセスや Chrome を一括終了しない。
保存した接続 URL が不要になったら、自分で作成した `pwDirectory` だけを削除する。
MCP が `.playwright-mcp/` にログを生成する場合があるが、コミット対象には含めない。

共通指示は `src/.codex/AGENTS.md` にあり、`~/.codex/AGENTS.md` のリンクから
新しいチャットへ読み込まれる。現在進行中の別チャットにこの変更が自動で伝わるとは限らない。

参考: [OpenAI の MCP 接続ドキュメント](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。
上の接続 URL を保存する方法は、この端末で確認したローカルの代替手順。
