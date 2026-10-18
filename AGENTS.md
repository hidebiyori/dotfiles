# dotfiles の変更・検証

- 共通設定は `src/` で管理する。秘密情報と非公開プロジェクトの名前・パス・設定値は公開ファイルへ追加しない。
- 全プロジェクト向けの判断規則は `src/.codex/AGENTS.md`、端末共通の手順は `docs/` に置く。
  個別プロジェクトの構成・公開先・認証方式は、そのプロジェクトの `AGENTS.md` と文書で管理する。
- README はセットアップの入口と日常的な操作の早見表に絞り、詳細手順を重複させない。
  解決済みの不具合・移行経緯・調査日誌は文書へ残さない。
- mise の共通ツール指定は `src/.config/mise/config.toml` に集約する。
  インストーラーから設定を書き換えず、呼び出し元プロジェクトの設定に依存させない。
- 検証のために一括セットアップを実行しない。外部コマンドをスタブ化した既存テストを使う。

```bash
bash -n bin/install.sh bin/setup-skill-python.sh src/.bash_profile src/.bashrc src/bin/wsl-browser
python3 -B -m unittest discover -s tests -v
git diff --check
```

Windows の検証は PowerShell で `./tests/test_windows.ps1` を実行する。
ローカルで実行できなければ、GitHub Actions の Windows PowerShell 5.1 / PowerShell 7 の結果を確認する。
テストが成功しても、実際のアプリ導入・WSL 初回起動・UI 動作の確認とは区別する。
