# Codex の共通指示とスキル

## 情報を置く場所

| 場所 | 管理する内容 |
| --- | --- |
| `src/.codex/AGENTS.md` | 全プロジェクトに共通する行動規則と、必要時に読む手順への参照 |
| dotfiles の `docs/` | 端末共通の操作・調査手順。非公開プロジェクトの名前や設定値を含めない |
| 各プロジェクトの `AGENTS.md` | そのプロジェクトの検証コマンド、構成、公開時の注意点 |
| 各プロジェクトの文書・設定 | Firebase のプロジェクト ID、Hosting target、workflow、公開先など |

README は利用者向けの入口とし、詳細手順の本文は目的別の文書にまとめる。
共通指示には、安定した動作に必要な判断規則を残す。解決済みの不具合や作業の経緯は Git の履歴で確認する。
認証情報の値はどの文書にも保存しない。

Firebase 公開認証の手順は **グローバル配布用の `src/.codex/AGENTS.md` から
`~/git/dotfiles/docs/firebase-deploy-auth.md` を参照している**。
Chrome / Playwright の接続手順も同様に参照する。
対象の作業時に手順を読み、実際のプロジェクト設定と権限を確認する。
個別プロジェクトの認証方式・公開先は、そのプロジェクト内に記載する。

[公式の指示ファイル読み込み順](https://learn.chatgpt.com/docs/agent-configuration/agents-md)では、
グローバル指示にプロジェクト内の指示を重ねる。同じ階層の `AGENTS.override.md` が優先される。

## 配置と同期

`bin/install.sh` は `src/.codex/AGENTS.md` を `~/.codex/AGENTS.md` へリンクする。
`CODEX_HOME` があれば、その絶対パスにもコピーする。
WSL で未指定なら Windows 側の `CODEX_HOME`、次に `%USERPROFILE%\.codex` をコピー先に使う。
Windows アプリ用には通常ファイルを配置する。認証・履歴・その他の設定は同期しない。

**編集先は `src/.codex/AGENTS.md`。Windows 側のコピーは編集・pull だけでは更新されない。**
`u` で再適用するか、パッケージ更新を伴わない次のコマンドを WSL 内で実行する。
独自の `CODEX_HOME` がある場合は対象アプリと同じ保存先を指定しておく。

```bash
bash -c 'source "$HOME/git/dotfiles/bin/install.sh"; setOptions; setCodexInstructions'
```

このコマンドは現在のチェックアウトからコピーし、リポジトリの取得・更新はしない。
指示の読み込みには新しいセッションを開始する。
WSL 内の Codex CLI の既定保存先は `~/.codex` で、Windows アプリとは別になる。

## 共通スキル

自作スキルは `src/.agents/skills/<skill-name>/SKILL.md` に置き、セットアップで
`~/.agents/skills` 以下へファイル単位でリンクする。

- `japanese-commit`: 日本語の件名と複数行の本文に変更内容・理由・検証結果を書く。
- `npm-vulnerability-remediation`: Dependabot の検知を確認し、対象を絞って依存更新・検証する。

スキルの Python 検証には[共通の仮想環境](development-tools.md#スキル用-python)を使う。
スキルを削除・改名した場合は、配置先に残る古いリンクも削除する。
