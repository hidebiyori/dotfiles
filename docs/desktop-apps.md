# デスクトップアプリの管理

管理対象は Codex デスクトップ版、Chrome、VS Code の3つ。
Codex デスクトップ版は現在の公式配布名である **ChatGPT** を導入し、その中の Codex を使う。
ターミナル用の Codex CLI は別物で、この一覧では導入しない。
[公式のデスクトップ版セットアップ](https://learn.chatgpt.com/docs/quickstart?setup=app)を参照。

## OS ごとの分担

| 環境 | Codex デスクトップ版 | Chrome | VS Code |
| --- | --- | --- | --- |
| Windows | Store の `9PLM9XGG6VKS` | winget の `Google.Chrome` | winget の `Microsoft.VisualStudioCode` と WSL 拡張 |
| Mac | Homebrew cask の `chatgpt` | cask の `google-chrome` | cask の `visual-studio-code` |
| Chromebook | Linux 側に公式 `chatgpt` deb | ChromeOS 標準版を利用 | Linux 側に公式 `code` deb |
| WSL | Windows 側のアプリを利用 | Windows 側のアプリを利用 | Windows 版 + WSL 拡張を利用 |

Windows は [Windows セットアップ手順](windows-setup.md)の PowerShell スクリプトを使う。
Mac と Chromebook は従来の `bin/install.sh` / `u` に組み込んでいる。
Chromebook の Chrome は ChromeOS が管理するため、Linux 側に Chrome / Chromium を追加しない。
WSL でも Linux 用のデスクトップアプリは導入しない。

## Windows

`bin/install-windows.ps1` の `Get-ManagedWindowsApps` に、アプリ名・完全な ID・source をまとめている。
最初の Git clone を不要にするため、入口とアプリ一覧は単独の PowerShell ファイルで配布できる形にしている。
対象を増減するときは、この一覧とテスト・手順を更新する。

通常は winget で各 ID の導入状態を確認し、不足分だけ導入する。
確認エラーを未導入と扱わず、インストールや更新に失敗した場合もその場で停止する。
`-UpgradeApps` を指定した場合だけ、管理対象 ID の `winget upgrade` も実行する。
全アプリを対象とする `winget upgrade --all` は使わない。

「導入済み」「更新不要」「新しいバージョンではない」という既知の終了コードは、
同じ ID・source を指定した再確認で導入済みと判定できた場合だけ許容する。
初回確認とインストールの間に他の処理が導入した場合も再実行を妨げない。
判定には [WinGet 公式の HRESULT 定義](https://github.com/microsoft/winget-cli/blob/master/src/AppInstallerSharedLib/Public/AppInstallerErrors.h)を使い、
通信エラーやハッシュ不一致等を一律に無視することはしない。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -AppsOnly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -AppsOnly -UpgradeApps
```

上の2行は用途に応じてどちらかを実行する。ファイル未取得の場合は Windows 手順から始める。
Store の ID は [OpenAI 公式の Windows 手順](https://learn.chatgpt.com/docs/windows/windows-app)を参照したもの。
`OpenAI.Codex` 等の名前からデスクトップ版の ID を推測して導入しない。

## Mac

`bin/install.sh` の `setMacDesktopApps` が対象 cask を管理する。
Homebrew が既に入っている端末でも、不足しているアプリを追加する。
Homebrew に未登録でも `/Applications` または `~/Applications` に対象の `.app` があれば維持し、
管理元の切替や削除は自動では行わない。

通常の再実行では、導入済みアプリへの `brew install` を省く。
対象の Homebrew 管理アプリを明示的に更新する場合:

```bash
UPGRADE_DESKTOP_APPS=1 bash ~/git/dotfiles/bin/install.sh
```

これは対象アプリへの `brew upgrade --cask --greedy` に加え、通常の一括セットアップも行う。
既存の `brew update` / `brew upgrade` によるその他のパッケージ更新も従来どおり実行する。
手動導入を維持したアプリはこの指定でも Homebrew 管理へ変更せず、その導入元で更新する。

Homebrew の `codex` は CLI、古い `codex-app` は非推奨の別 cask。
新規導入は `chatgpt` を使う。既存の Codex.app の削除やデータ移行は行わない。
[chatgpt cask](https://formulae.brew.sh/cask/chatgpt)、
[旧 codex-app cask](https://formulae.brew.sh/cask/codex-app)を参照。

## Chromebook / Linux

`setCodexDesktop` と `setVisualStudioCode` が導入を担当する。
ChatGPT パッケージや VS Code コマンドが既にあれば、配布ファイルの再取得を省く。
不足時は公式の deb を使い、amd64 / arm64 に合う配布物を選ぶ。

Codex / ChatGPT の Linux 版はプレビュー。
新規自動導入は、現在公式対象の Debian 13 / Ubuntu 24.04・26.04 に限る。
Crostini 固有の全機能を保証するものではない。
対象外の OS では導入済みパッケージを再利用できるが、新規導入を無理に進めず停止する。
OS 自体をこのスクリプトでアップグレードすることはない。
[公式 Linux 手順と対応環境](https://learn.chatgpt.com/docs/linux/linux-app)を参照。

取得した deb は `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles` に保持し、再実行時に再利用する。
apt へ渡す前にパッケージ名とアーキテクチャを確認する。
VS Code は公式更新 API から取得したバージョンに配布 URL を合わせ、SHA256 も検証する。
更新メタデータもキャッシュし、既存キャッシュを使う場合も deb の SHA256 を再確認する。
取得途中の `.part` は完成したキャッシュとして使わず、取得失敗時は導入しない。
ChatGPT の初回 deb は公式 HTTPS 配布元を使い、名前・アーキテクチャの確認を署名検証と同一には扱わない。

Linux 版 ChatGPT の初回パッケージは、以後の更新用の署名付き OpenAI リポジトリも設定する。
通常の apt update / upgrade で更新し、毎回最新 deb をダウンロードし直さない。
アプリを個別に更新する場合の公式手順:

```bash
sudo apt update
sudo apt install --only-upgrade chatgpt
```

VS Code の更新も、導入パッケージが設定した公式リポジトリを確認した上で apt で行う。
既存のコマンドが別方式の導入である場合、管理元を自動で切り替えない。

## 共通の範囲

アプリのサインイン、ブラウザの同期、Codex のアカウント設定は利用者が行う。
設定・認証情報・会話履歴等の端末間コピーは行わない。
VS Code の設定コピーだけでは拡張機能本体は導入されないため、
WSL 拡張以外の Prettier 等は必要なプロジェクトに合わせて追加する。

スクリプトはアプリを起動・終了するためのものではない。
導入元のインストーラーが要求する承認や、利用者による必要な再起動は残る。
テストでは外部コマンドをスタブ化し、既存の導入を維持する分岐、対象限定の更新、
連続実行、更新不要、途中の失敗からの再開と本当のエラー時の停止を確認する。
共通設定や更新の範囲は [README の再実行方針](../README.md#再実行時の動作)も参照。
実アプリの新規導入や UI 動作は実機での確認が必要。
