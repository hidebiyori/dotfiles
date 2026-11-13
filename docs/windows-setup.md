# Windows 11 / WSL2 のセットアップ

プロジェクト追加時のパスは [README 冒頭の早見表](../README.md#windows-codex-でプロジェクトを追加するとき)を参照する。
Windows アプリは `bin/install-windows.ps1`、WSL 内は `bin/install.sh` で構築する。
左 Win → Alt は、通常セットアップとは別の[キー設定手順](windows-keyboard.md)で適用する。

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

- `~/git/dotfiles` が既にある場合は、変更のない `main` が `origin/main` を追跡し、origin がこのリポジトリであることを確認して fast-forward 更新する。
  別の接続先・作業ブランチ・未コミットの変更があれば停止する。
  HTTPS / SSH と `.git` 接尾辞の有無に対応し、取得後のコードでセットアップを実行する。セットアップ内での Git 再取得は行わない。
- 指定名の WSL2 を再利用する。WSL1 は作り直さず、バックアップ後の明示的な変換を案内する。
- Windows の実際の Downloads をリンクし、通常版 VS Code の既定プロファイルへ設定をコピーする。
  Downloads の実ディレクトリは維持し、同一内容のコピーは省く。Windows 連携を使えなければ省略を表示する。
- WSL には Linux GUI アプリ、日本語入力、ChromeOS 用のリンク・ランチャーを導入しない。
  Node / npm と認証情報は Windows 側と共有しない。開発リポジトリと依存ディレクトリは WSL の `~/git` に置く。

## Windows 版 Codex と WSL の併用

Computer Use で Windows アプリを操作し、開発に WSL のツールを使う場合は、
エージェントを **Windows native**、統合ターミナルを **WSL** にする。導入後にアプリ内で設定する。

1. **Settings → Agent environment → Windows native** を選ぶ。エージェントは PowerShell でコマンドを実行する。
2. **Integrated terminal shell → WSL** を選ぶ。エージェントとは独立した設定で、新しいターミナルに適用される。
3. エージェントの設定を変更した場合は、進行中の作業を終えてアプリを再起動する。
4. [README のパス](../README.md#windows-codex-でプロジェクトを追加するとき)で対象フォルダーを追加する。

Computer Use は **Settings → Computer use** で利用可否を確認し、案内に沿って有効にする。
Windows をロック解除して対象アプリを表示する。操作中は Computer Use が同じデスクトップのマウスとキーボードを使う。
[公式の Computer Use の手順](https://learn.chatgpt.com/docs/computer-use)。

WSL に置いたリポジトリの Git・ビルド・テストは WSL 側で実行する。新しい統合ターミナルで対象フォルダーへ移動し、
`pwd` が `/home/<Linuxユーザー名>/git/<リポジトリ名>`、`uname -s` が `Linux` になることを確認する。
エージェントの PowerShell から WSL のコマンドを呼ぶ場合は、ディストリビューションと Linux 側の作業ディレクトリを指定する。

```powershell
wsl.exe -d Ubuntu --cd '/home/<Linuxユーザー名>/git/<リポジトリ名>' -- git status --short
```

WSL 側のファイルを UNC パスで開く場合、Windows 側でのファイル操作や Git の状態表示に制約が出ることがある。
サンドボックスで `wsl.exe` の起動が制限される場合は、WSL の統合ターミナルで `git` などを直接実行する。
開発作業が Linux 中心でエージェントに WSL のツールを直接使わせたい場合は、**Agent environment → WSL** を選んでアプリを再起動する。
[公式の Windows / WSL 設定](https://learn.chatgpt.com/docs/windows/windows-app#windows-subsystem-for-linux-wsl)。

Windows 側の Codex 保存先と共通指示の同期は [Codex の管理手順](codex.md#配置と同期)を参照する。

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

## Brother HL-L3230CDW の登録

Windows 11 x64 で、同じ LAN にあるプリンターを Brother 純正ドライバーと標準 TCP/IP ポート（RAW、9100）で登録する。
必要な PC で [専用スクリプト](../bin/setup-windows-printer.ps1)を個別に実行する。紙への印刷は登録後に Chrome などのアプリから行う。

1. プリンター本体のネットワーク設定リストなどで IPv4 アドレスを確認する。
   Windows から名前解決できる場合は、プリンターのホスト名も指定できる。
   [Brother のネットワーク設定レポート](https://support.brother.co.jp/j/s/support/html/hll3230cdwb_jpn/ug/html/GUID-44BEFA90-16C6-48A6-8A51-4A2D1A14D01F_63.html)
2. Brother 公式サイトの Windows 11 向け「プリンタードライバー」をダウンロードして展開し、`gdi\BROCH17A.INF` のパスを控える。
   Windows に機種専用ドライバーが登録済みなら `-DriverInf` を省略できる。
   [HL-L3230CDW の公式ダウンロード](https://support.brother.co.jp/j/b/downloadlist.aspx?c=jp&lang=ja&os=10075&prod=hll3230cdw)
3. 下の例のリポジトリ、ホスト名、INF のパスを置き換える。`-WhatIf` で変更予定を確認し、適用時は
   **管理者として開いた Windows PowerShell** で同じコマンドから `-WhatIf` を外して実行する。

```powershell
$repo = '\\wsl$\Ubuntu\home\<Linuxユーザー名>\git\dotfiles'
$printerAddress = 'printer.local'
$driverInf = 'C:\path\to\driver\gdi\BROCH17A.INF'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\bin\setup-windows-printer.ps1" -PrinterHostAddress $printerAddress -DriverInf $driverInf -WhatIf
```

同じ設定で再実行すると既存のキューとポートを再利用する。同名で接続先やドライバーが異なる場合は停止する。
ポートとドライバーの構成を確認し、以前のキューを置き換える場合は、印刷待ちがないことを確認して Windows の設定から取り除く。
画面で追加する場合は Windows の［プリンターとスキャナー］で手動追加を選び、TCP/IP デバイスとして接続先を指定する。
ドライバーの自動選択のチェックを外し、［ディスク使用］で上記の INF を指定して **Brother HL-L3230CDW series** を選ぶ。
プリンター名を **Brother HL-L3230CDW** にし、ポートが標準 TCP/IP の RAW、9100 になっていることを確認する。

Chrome の印刷画面で送信先に表示されなければ、［送信先］欄の下の［もっと見る］から **Brother HL-L3230CDW** を選ぶ。
この選択のための再起動は不要。初回は本体のそばで1ページを1部印刷し、紙への出力を確認する。
印刷が意図せず続く場合は本体の［キャンセル］を押し、Windows の印刷キューでも該当ジョブを取り消す。
[Chrome の印刷手順](https://support.google.com/chrome/answer/1069693?hl=ja)

## 更新とエラー時の扱い

設定だけを再適用する場合は WSL 内の `u`、導入済みツールと Windows 側の管理対象アプリの更新は `up` を使う。
不足するアプリやツールを追加する場合は、初期セットアップの PowerShell スクリプトを再実行する。
[共通の再実行方針](../README.md#更新と再実行)に従い、導入済みアプリと同一設定を再利用する。
初期セットアップ用 PowerShell スクリプトの終了コードは、完了が `0`、再起動 / ユーザー作成待ちが `2`、エラーが `1`。
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
