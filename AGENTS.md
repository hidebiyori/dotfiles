# dotfiles の変更・検証

- GitHub の `main` は ruleset で保護している。PR と `linux` / `windows` の CI 成功、
  マージ前のブランチ最新化を必須とし、`main` の force push と削除は禁止する。
  承認人数は 0、通常の bypass は設けていない。シークレットスキャンと push protection は有効。
  保護の共通手順と再確認事項は [リポジトリ保守](docs/repository-maintenance.md#既定ブランチの保護)を参照する。
- 共通設定は `src/` で管理する。秘密情報と非公開プロジェクトの名前・パス・設定値は公開ファイルへ追加しない。
- `.bashrc` の作業用パス・エイリアス・Vim の配置と `.screenrc` のタブ構成・起動コマンドは、
  利用者が手動配置するシンボリックリンクやローカルの作業場所を参照するために必要。
  明示的な依頼なしに、これらと関連する設定・参照先を変更・削除・改名・自動再配置しない。
  リンク先が存在しないことやパスに技術名が含まれることを、不要と判断する根拠にしない。
  手動配置用のローカル名と、非公開リポジトリの実名・URL の公開は区別する。
- 全プロジェクト向けの判断規則は `src/.codex/AGENTS.md`、複数プロジェクトで再利用する手順は `docs/` に置く。
  個別プロジェクトの構成・公開先・認証方式は、そのプロジェクトの `AGENTS.md` と文書で管理する。
- 会話から得た共通知見の採用・一般化・公開前確認は `docs/learnings.md` に従う。非公開の対象を特定できる情報を、出典リンクやコミット・PR にも含めない。
- README はセットアップの入口と日常的な操作の早見表に絞り、詳細手順を重複させない。
  解決済みの不具合・移行経緯・調査日誌は文書へ残さない。
- mise の共通ツール指定は `src/.config/mise/config.toml` に集約する。
  インストーラーから設定を書き換えず、呼び出し元プロジェクトの設定に依存させない。
- 検証のために一括セットアップを実行しない。外部コマンドをスタブ化した既存テストを使う。

```bash
for file in bin/*.sh lib/install/*.sh src/.bash_profile src/.bashrc src/bin/git-* src/bin/wsl-browser; do
  bash -n "$file" || exit
done
python3 -B -m unittest discover -s tests -v
python3 -B bin/check-markdown-links.py .
git diff --check
```

Windows の検証は PowerShell で `./tests/test_windows.ps1` を実行する。
ローカルで実行できなければ、GitHub Actions の Windows PowerShell 5.1 / PowerShell 7 の結果を確認する。
テストが成功しても、実際のアプリ導入・WSL 初回起動・UI 動作の確認とは区別する。
