# Windows 11 / WSL2 のセットアップ

プロジェクト追加時のパスは [README 冒頭の早見表](../README.md#windows-codex-でプロジェクトを追加するとき)を参照する。
Windows アプリは `bin/install-windows.ps1`、WSL 内は `bin/install.sh` で構築する。
左 Win → Alt と Print Screen は、通常セットアップとは別の[キー設定手順](windows-keyboard.md)で適用する。

## 初回に実行すること

普段使うアカウントで、**管理者ではない通常の PowerShell** を開く。
`winget` がなければ Microsoft Store の「アプリ インストーラー」を導入・更新する。
スクリプトを保存して内容を確認する。

```powershell
Invoke-WebRequest -UseBasicParsing -Uri https://raw.githubusercontent.com/hidebiyori/dotfiles/main/bin/install-windows.ps1 -OutFile "$env:USERPROFILE\install-windows.ps1"
notepad.exe "$env:USERPROFILE\install-windows.ps1"
```

確認後、別の操作として実行する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1"
```

`ExecutionPolicy Bypass` はこの子プロセスだけに適用する。組織の管理ポリシーで拒否される場合は管理者へ確認する。
WSL 内の設定に加え、Windows の `%APPDATA%\Code\User` の設定と Codex 共通指示も置き換える。
残す設定を事前に退避し、WSL のセットアップ中は VS Code を閉じておく。

| 段階 | 処理と利用者の操作 |
| --- | --- |
| Windows アプリ | Codex / ChatGPT・Chrome・VS Code・GitHub CLI と WSL 拡張の不足分を導入。必要な承認に応答する |
| WSL 未導入 | WSL の導入時だけ管理者承認を求めて終了。案内に従って Windows を再起動する |
| Linux 初期設定 | スタートメニューから対象のディストリビューションを起動し、一般ユーザーとパスワードを作成して `exit` |
| WSL 準備済み | Git の準備、`~/git/dotfiles` の clone / 更新、一括セットアップ。sudo / apt の入力に応答する |

再起動・ユーザー作成後は、**同じ実行コマンドをもう一度実行**する。
管理者承認にも同じ Windows アカウントを使う。ユーザー作成とパスワード設定は手動で行う。
Windows 側の clone や Linux 側への手動コピーは不要。

## 実行オプション

既定のディストリビューション名は `Ubuntu`。別の登録名を使う場合は毎回同じ名前を指定する。
利用できる名前は `wsl --list --online`、導入済みの名前とバージョンは `wsl --list --verbose` で確認する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -Distribution Ubuntu-24.04
```

Windows アプリだけの導入・再適用:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -AppsOnly
```

対象アプリの更新も行う場合は `-UpgradeApps` を加える。
Steam も導入する場合は `-IncludeSteam` を加える。通常のセットアップと `-AppsOnly` のどちらでも指定できる。
Steam だけの導入・確認方法は [Steam（任意）](desktop-apps.md#steam任意)を参照する。
導入元・対象一覧・更新方針は[アプリ管理](desktop-apps.md)を参照する。
スクリプト自体の更新は、最初のダウンロードと内容確認を再度行う。

## 既存データと Windows 連携

- `~/git/dotfiles` が既にある場合は、変更のない `main` かつ origin がこのリポジトリであることを確認して fast-forward 更新する。
  別の接続先・作業ブランチ・未コミットの変更があれば停止する。
- 指定名の WSL2 を再利用する。WSL1 は作り直さず、バックアップ後の明示的な変換を案内する。
- Windows の実際の Downloads をリンクし、通常版 VS Code の既定プロファイルへ設定をコピーする。
  Downloads の実ディレクトリは維持し、同一内容のコピーは省く。Windows 連携を使えなければ省略を表示する。
- WSL には Linux GUI アプリ、日本語入力、ChromeOS 用のリンク・ランチャーを導入しない。
  Node / npm と認証情報は Windows 側と共有しない。開発リポジトリと依存ディレクトリは WSL の `~/git` に置く。

## Codex を WSL で使う設定

導入後にアプリ内で一度設定する。セットアップスクリプトはこの設定を変更しない。

1. **Settings → Agent environment → WSL** を選ぶ。
2. **Integrated terminal shell → WSL** も選ぶ。エージェントとは独立した設定。
3. 進行中の作業を終えてアプリを再起動する。
4. [README のパス](../README.md#windows-codex-でプロジェクトを追加するとき)で対象フォルダーを追加する。

新しいチャットで `pwd` が `/home/<Linuxユーザー名>/git/<リポジトリ名>`、`uname -s` が `Linux` になることを確認する。
統合ターミナルも新しく開いて確認する。
Windows 側の Codex 保存先と共通指示の同期は [Codex の管理手順](codex.md#配置と同期)を参照する。

[公式の Windows / WSL 設定](https://learn.chatgpt.com/docs/windows/windows-app#windows-subsystem-for-linux-wsl)。

## 導入後の確認と認証

Windows の `wsl --list --verbose` で対象の VERSION が `2` であることを確認する。
新しい WSL ターミナルでは次を確認する。

```bash
command -v git gh mise node npm firebase
mise doctor
node --version
npm --version
mise which node
mise which npm
firebase --version
```

Node / npm が WSL の mise 配下を指すことを確認する。
VS Code はプロジェクト内で `code .` を実行し、左下の `WSL: Ubuntu` 等の表示を確認する。
初回の VS Code Server のダウンロードは別途発生する。

GitHub の[初回認証](development-tools.md#github-cli-の初回認証)は WSL 内で行う。
`~/bin/wsl-browser` は、WSL の Bash で `BROWSER` が未設定なら Windows の既定ブラウザーを使う。
反映にはターミナルを開き直す。自動で開けない場合は表示された URL とコードで手動認証できる。
既存の `GH_BROWSER` は優先される。`powershell.exe` が見つからなければ WSL の Windows 実行ファイル連携と PATH を確認する。

Windows ネイティブの Node、gcloud、Docker、Android SDK は導入対象外。
Windows 版 Codex の Git 機能に必要な場合は、通常の PowerShell で Git を追加する。

```powershell
winget install --id Git.Git --exact --source winget
```

## 更新とエラー時の扱い

Windows 側は PowerShell スクリプト、WSL 内は `u` で再適用する。
[共通の再実行方針](../README.md#更新と再実行)に従い、導入済みアプリと同一設定を再利用する。
終了コードは完了が `0`、再起動 / ユーザー作成待ちが `2`、エラーが `1`。
状態確認・通信・権限・ハッシュ検証等の失敗は停止する。原因を解消して同じコマンドを再実行する。

sudo / apt の進捗と入力待ちは元の PowerShell に表示する。パスワード入力中は文字が表示されない。
apt の CLI 互換性警告だけでは失敗と判断しない。
確認が必要な場合は別の WSL ターミナルで `ps -C apt,dpkg,sudo -o pid,ppid,stat,etime,comm` を使う。
稼働中に別のセットアップを重ねたり、ロックファイルを削除したりしない。

[WSL のトラブル対応](https://learn.microsoft.com/windows/wsl/troubleshooting#installation-issues)、
[VS Code の PATH](https://code.visualstudio.com/docs/setup/windows)、
[WSL のリソース設定](https://learn.microsoft.com/windows/wsl/wsl-config#main-wsl-settings)。

Bash と Windows PowerShell 5.1 / PowerShell 7 のテストは外部コマンドをスタブ化して実行する。
実際の初回導入・再起動・アプリの接続は実機確認が必要。
