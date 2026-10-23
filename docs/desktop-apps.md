# デスクトップアプリの管理

Codex は公式配布名 **ChatGPT** のデスクトップアプリ内で使う。
このセットアップは Codex CLI を導入しない。[公式セットアップ](https://learn.chatgpt.com/docs/quickstart?setup=app)。

| 環境 | Codex / ChatGPT | Chrome | VS Code |
| --- | --- | --- | --- |
| Windows | Store `9PLM9XGG6VKS` | winget `Google.Chrome` | winget `Microsoft.VisualStudioCode` + WSL 拡張 |
| Mac | cask `chatgpt` | cask `google-chrome` | cask `visual-studio-code` |
| Chromebook | 公式 `chatgpt` deb | ChromeOS 標準版 | 公式 `code` deb |
| WSL | Windows 側を利用 | Windows 側を利用 | Windows 版 + WSL 拡張 |

GitHub CLI も Windows は winget `GitHub.cli`、Mac は Homebrew、Linux / WSL は apt で導入する。
アプリのサインイン・ブラウザー同期・アカウント設定は利用者が行う。
認証・履歴の端末間コピーは行わない。VS Code の WSL 拡張以外はプロジェクトに合わせて追加する。

## Windows

[Windows 手順](windows-setup.md#初回に実行すること)で PowerShell スクリプトを準備する。
通常は不足分だけ導入し、`-UpgradeApps` を指定した場合だけ対象 ID を更新する。
`winget upgrade --all` は使わない。

対象は `bin/install-windows.ps1` の `Get-ManagedWindowsApps` で管理する。
Store の ID を含め、製品名から導入 ID を推測しない。
「導入済み・更新不要」の既知の終了コードは、同じ ID / source の再確認に成功した場合だけ許容する。
通信・ハッシュ検証・状態確認の失敗は停止する。

導入済みの管理対象アプリだけを更新する場合は、リポジトリの `bin/upgrade-windows.ps1` を使う。
未導入アプリや WSL・拡張機能の新規導入は行わない。
WSL の `up` からもこのコマンドを呼ぶ。Windows Update は Windows の設定から実施する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl$\Ubuntu\home\<Linuxユーザー名>\git\dotfiles\bin\upgrade-windows.ps1"
```

パスは利用するディストリビューション名とユーザー名に合わせる。
Steam も導入済みなら `-IncludeSteam` を追加して更新できる。WSL の通常の `up` には含めない。

### Steam（任意）

Windows 版 Steam は `-IncludeSteam` を指定したときだけ、winget の `Valve.Steam` を対象に加える。
既定では導入・更新・状態確認を行わない。導入元は [Microsoft のパッケージ定義](https://github.com/microsoft/winget-pkgs/tree/master/manifests/v/Valve/Steam)で確認できる。
通常の PowerShell で、準備したスクリプトに指定する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -AppsOnly -IncludeSteam
```

通常の対象アプリと WSL 拡張の不足分も導入する。WSL のセットアップも行う場合は `-AppsOnly` を外す。
導入済みの Steam は再インストールしない。winget で更新する場合は、同じコマンドに `-UpgradeApps` も加える。
`-IncludeSteam` を省いた再実行でも、Steam の削除は行わない。

Steam だけを追加する場合は、一括セットアップを実行せず次を使う。

```powershell
winget install --id Valve.Steam --exact --source winget --accept-source-agreements --accept-package-agreements --disable-interactivity --silent --no-upgrade
```

必要に応じて Windows の管理者承認に応答する。導入後は次で登録を確認する。

```powershell
winget list --id Valve.Steam --exact --source winget
```

スタートメニューから Steam を開き、初回のクライアント更新とサインインを行う。
ゲームのインストールは Steam 内で選択する。クライアント更新やゲームの取得には追加の通信が発生する。

## Mac

`lib/install/macos.sh` の `setMacDesktopApps` が対象 cask を管理する。
導入済み cask と `/Applications` / `~/Applications` の手動導入アプリを再利用する。
Homebrew 管理の対象アプリを明示更新する場合:

```bash
up
```

formula と mise の共通ツールも更新する。初期セットアップでは不足分だけ導入し、
アプリの更新は行わない。更新対象の cask は ChatGPT / Chrome / VS Code / Google 日本語入力で、
導入済みのものだけ更新する。手動導入アプリの管理元は変更しない。
`--no-quit` を指定し、更新のために起動中の cask アプリを自動終了しない。
起動中などの理由で更新できなければ、必要なアプリを自分で閉じてから再実行する。

## Chromebook / Linux

`setCodexDesktop` と `setVisualStudioCode` が導入を担当する。
導入済みなら配布ファイルを再取得しない。Chrome / Chromium は追加せず ChromeOS 標準版を使う。
ChatGPT の新規導入対象は Debian 13 / Ubuntu 24.04・26.04、amd64 / arm64。
ディストリビューションのアップグレードは行わない。[公式 Linux 対応環境](https://learn.chatgpt.com/docs/linux/linux-app)。

取得した deb と更新メタデータは `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles` に保存する。
導入前に名前とアーキテクチャを確認し、VS Code は公式 API のバージョンと SHA256 も検証する。
途中の `.part` は再利用しない。ChatGPT 初回 deb の HTTPS 取得とメタデータ確認は署名検証とは区別する。
以後は導入パッケージが設定した公式リポジトリから apt で更新する。

```bash
sudo apt update
sudo apt install --only-upgrade chatgpt
```

VS Code も管理元の公式リポジトリから更新する。別方式の導入は自動で切り替えない。

### Chromebook で最大化して起動する

一括セットアップで適用する。個別に設定する場合:

```bash
python3 ~/git/dotfiles/bin/setup-chatgpt-maximized.py
```

ユーザー用の `chatgpt.desktop` から `~/.local/bin/chatgpt-maximized` を使う。
アプリ終了中の次回起動時に、Codex 保存先の `.codex-global-state.json` の最大化フラグを補正する。
既存の名前・アイコン・関連付けは引き継ぎ、起動中や不正な保存形式では状態を変更しない。
`/usr/bin/chatgpt` の直接実行には適用しない。`CODEX_HOME` があればその保存先を使う。

補正前の状態は同じフォルダーの `.codex-global-state.json.before-maximized-launcher` に一世代だけ退避する。
状態と退避ファイルは本人だけが読み書きできる権限とし、Git 管理しない。
起動せず補正だけ確認する場合は `~/.local/bin/chatgpt-maximized --prepare-only`。

解除する場合は `~/.local/share/applications/chatgpt.desktop` を削除する。
設定前のユーザー用 entry があれば、代わりに
`~/.local/state/dotfiles/chatgpt.desktop.before-maximized-launcher` から復元する。
`XDG_DATA_HOME` / `XDG_STATE_HOME` を指定していれば保存先を合わせる。
必要に応じて `update-desktop-database ~/.local/share/applications` を実行し、不要なランチャーリンクも削除する。

## 手動の表示・入力・ブラウザー設定

アプリの導入後に、端末ごとに選ぶ設定候補。OS・アプリの版によって設定名や対応項目が変わるため、
実際の画面で項目と好みを確認する。これらはインストーラーの自動設定対象には含まれない。

### Mac

- Finder: よく使うフォルダーをサイドバーへ追加し、すべてのファイル名拡張子・パスバー・ステータスバーを表示する。検索範囲は現在のフォルダーを候補にする。
- 表示: スクロールバーを常に表示し、Dockを小さめ・左側にする。時計の日付とバッテリー残量の割合を表示する。
- キーボード: キーのリピートを速く、リピート開始までを短くし、F1などを標準のファンクションキーとして使う。不要な音声入力ショートカットは解除する。
- トラックパッド: タップでクリック、弱めのクリック、速めの軌跡・スクロール、3本指のドラッグを候補にする。
- サウンド: 通知音と操作音を小さくするか無効にし、音量変更時のフィードバックも確認する。
- Google 日本語入力: 「かな」キーによるひらがな入力と、`Ctrl+;` による半角英数への表示切り替えを設定候補にする。

### Windows と電源設定

Windowsのキー割り当ては[専用のキー設定](windows-keyboard.md)を参照する。
通知領域とスタートアップ項目は、利用するアプリに合わせて選ぶ。
画面の消灯・ロック・本体のスリープは別々に確認し、バッテリー使用時と外部電源使用時で必要な動作を選ぶ。

### ブラウザー

- 起動時に前回のウィンドウ・タブを復元するかを選ぶ。
- 検索エンジン、ダウンロード先、ブックマークツールバー、必要な拡張機能を確認する。
- サインインと同期は[アプリ管理の分担](#デスクトップアプリの管理)に従って利用者が行う。

## 検証範囲

外部コマンドのスタブで導入・再実行・更新・失敗時の停止を検証する。
実際のアプリ導入と UI 動作は実機確認が必要。スクリプトは稼働中のアプリを起動・終了しない。
