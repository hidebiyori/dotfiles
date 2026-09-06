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
