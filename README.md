# dotfiles

- dotfiles for hidebiyori
- install
  - `bash -c "$(curl -s https://raw.githubusercontent.com/hidebiyori/dotfiles/main/bin/install.sh)"`
  - restart terminal
- update: `u`

## Codex

- ユーザー共通の指示は `src/.codex/AGENTS.md` で管理する。
- 既存の `bin/install.sh` が `~/.codex/AGENTS.md` へのシンボリックリンクを作成する。
- Codex の設定だけを適用する場合（既存ファイルがある場合は先に退避する）:

  ```bash
  mkdir -p "${HOME}/.codex"
  ln -s "${HOME}/git/dotfiles/src/.codex/AGENTS.md" "${HOME}/.codex/AGENTS.md"
  ```

- `CODEX_HOME` を設定している環境では、リンク先をそのディレクトリに変更する。
- 反映には Codex の新しいセッションを開始する。`AGENTS.override.md` がある場合はそちらが優先される。
- 方針: 作業完了・検証後に今回の変更だけをコミットし、push は明示的な依頼時に行う。

## 個人共通のスキル

- 自作スキルは `src/.agents/skills/<skill-name>/SKILL.md` で管理する。
- `bin/install.sh` は各ファイルを `~/.agents/skills` 以下へリンクする。
- `npm-vulnerability-remediation`: Dependabot の検知を確認し、`npm update` を優先して修正・検証する。`npm audit` は診断用に使い、残る問題は依存経路と対応条件を記録する。
- スキルだけを適用する場合（同名の既存フォルダがないことを確認して実行）:

  ```bash
  mkdir -p "${HOME}/.agents/skills"
  ln -s "${HOME}/git/dotfiles/src/.agents/skills/npm-vulnerability-remediation" "${HOME}/.agents/skills/npm-vulnerability-remediation"
  ```

- ファイル単位でインストールしたスキルを削除・改名した場合は、配置先に残る古いリンクも削除する。
