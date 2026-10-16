# Windows 11 のセットアップ

Windows 側は `bin/install-windows.ps1`、WSL 内は既存の `bin/install.sh` で構築する。
最初に必要なのは PowerShell ファイルのダウンロードだけ。
**`git clone` はスクリプトが WSL 内の `~/git/dotfiles` へ行うため、Windows 側での clone は不要。**

## 初回に実行すること

Windows 11 の普段使うアカウントで、**管理者ではない通常の PowerShell** を開く。
Windows 標準の winget が使えることが前提。見つからなければ Microsoft Store の
「アプリ インストーラー」を導入・更新し、PowerShell を開き直す。
[winget の公式手順](https://learn.microsoft.com/windows/package-manager/winget/)も参照。

まずスクリプトを自分の Windows ホームへ保存し、内容を確認する。
このファイルは再起動後も同じ場所から使える。

```powershell
Invoke-WebRequest -UseBasicParsing -Uri https://raw.githubusercontent.com/hidebiyori/dotfiles/main/bin/install-windows.ps1 -OutFile "$env:USERPROFILE\install-windows.ps1"
notepad.exe "$env:USERPROFILE\install-windows.ps1"
```

内容を確認後、別の操作として実行する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1"
```

`ExecutionPolicy Bypass` はこの子プロセスだけに適用する。PC 全体の実行ポリシーは変更しない。
組織の管理ポリシー等で実行できない場合は、その設定を管理者に確認する。
スクリプトはアプリや WSL をダウンロードし、WSL 側のパッケージ更新と設定の置き換えも行う。
既存の Bash・Git・SSH・Codex 共通指示と、Windows 版 VS Code の
`%APPDATA%\Code\User\settings.json` / `keybindings.json` に残したい設定があれば、先に退避する。
WSL 内の一括セットアップ中は VS Code を閉じておく。

## スクリプトが進める順番

| 段階 | 処理 | 利用者が行うこと |
| --- | --- | --- |
| Windows アプリ | Codex / ChatGPT・Chrome・VS Code の不足分を winget で導入し、WSL 拡張を追加 | 必要なインストーラーの承認 |
| WSL が未導入 | 選択したディストリビューションを `wsl --install` で導入し、いったん終了 | WSL 導入時の管理者承認。指示があれば Windows を再起動 |
| Linux の初期設定 | root が既定ユーザーの場合は、一般ユーザーの設定を案内して終了 | スタートメニューから Ubuntu を起動し、Linux ユーザー名・パスワードを作成。シェルを `exit` で終了 |
| WSL が使用可能 | 一般ユーザーで Git の準備、`~/git/dotfiles` の clone / 更新、`bash bin/install.sh` | `sudo` のパスワードや apt の確認への応答 |

再起動やユーザー作成の段階では、完了とは表示せず終了する。
準備が済んだら、上の **同じ実行コマンドをもう一度実行** する。
Windows の再起動前に Ubuntu の導入が保留された場合も、再実行で導入を続ける。
通常は Windows 側で clone したり、手作業で Linux 側へファイルをコピーしたりする必要はない。

WSL の管理者承認も同じ Windows アカウントで行う。
別の管理者アカウントへ切り替えると WSL の導入先ユーザーが異なるため、この手順では扱わない。
新しい Windows / Linux ユーザーの作成やパスワード設定の無人化は行わない。

## 実行オプション

既定のディストリビューション名は `Ubuntu`。例えば Ubuntu 24.04 を選ぶ場合:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -Distribution Ubuntu-24.04
```

利用できる名前は `wsl --list --online` で確認する。
Debian を指定する場合も、以後同じ `-Distribution Debian` を付けて再実行する。
既に目的の WSL2 がある場合も、その登録名を指定する。

Windows アプリだけの導入・再適用:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -AppsOnly
```

管理対象の3アプリの更新も明示的に行う:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\install-windows.ps1" -AppsOnly -UpgradeApps
```

通常は導入済みアプリを再インストール・更新しない。
`-UpgradeApps` も管理対象の ID だけを指定し、`winget upgrade --all` は使わない。
スクリプトの対象一覧は `Get-ManagedWindowsApps` で管理する。
スクリプト自体は自動更新しないため、最新版を使うときは最初のダウンロード・内容確認を行う。

## WSL 内の clone と既存データの扱い

WSL 側の保存先は Linux ユーザーの `~/git/dotfiles`。
Windows 側の `%USERPROFILE%\install-windows.ps1` は入口となる単独ファイルで、Git リポジトリではない。

既存の `~/git/dotfiles` がある場合は、次を確認してから fast-forward 更新する。

- Git リポジトリであり、未コミットの変更がなく、`main` ブランチであること。
- origin がこのリポジトリの HTTPS または標準の GitHub SSH URL であること。

異なるディレクトリ・接続先・作業中のブランチや変更があれば停止し、自動削除・切替は行わない。
既存の WSL1 も作り直さず、バックアップ後の明示的な WSL2 変換を案内する。

## WSL 内で導入するもの

`bin/install.sh` が共通設定・スキル、apt パッケージ、mise、Node LTS / npm、
Firebase CLI、スキル用 Python を準備する。Flutter は従来どおり明示指定時だけ。
Windows の実際の Downloads へのリンクと、通常版 VS Code の既定プロファイルへの設定コピーも行う。
Downloads の既存の実ディレクトリは維持し、Windows 連携が使えない場合は省略を表示する。

WSL 内にはデスクトップアプリを重複導入しない。日本語入力は Windows 側の IME を使う。
ChromeOS 用の MyDrive リンク、Linux 用の日本語入力・VS Code・最大化ランチャーも WSL では導入しない。
ホームでの screen と既存の作業用タブは維持するが、個人プロジェクトやメモ自体を取得するものではない。

## 導入後の確認

Windows の通常の PowerShell で、WSL の `VERSION` が `2` であることを確認する。

```powershell
wsl --list --verbose
```

WSL のターミナルを新しく開いて確認する。

```bash
command -v git mise node npm firebase
mise doctor
node --version
npm --version
mise which node
firebase --version
```

Node が WSL の mise 配下を指し、Windows の `/mnt/c/.../node.exe` 等を使っていないことを確認する。
WSL の開発リポジトリと依存ディレクトリは `~/git` 以下に置き、Windows の Node / npm と共有しない。
VS Code は WSL のプロジェクト内で `code .` を実行し、左下に `WSL: Ubuntu` 等が表示されることを確認する。
初回の VS Code Server のダウンロードは別途発生する。

Codex は ChatGPT デスクトップアプリ内から使う。
Windows アプリの既定エージェントは Windows ネイティブなので、WSL 内で開発する場合は
アプリの設定でエージェントを WSL に切り替える。統合ターミナルも別途 WSL を選ぶ。
設定反映に必要なアプリの再起動は、進行中の作業を終えてから利用者が行う。
Windows と WSL の Codex の保存先・認証情報は自動共有しない。
[公式の Windows / WSL 設定](https://learn.chatgpt.com/docs/windows/windows-app#windows-subsystem-for-linux-wsl)を参照。

サインイン、GitHub の push 認証、プロジェクトの取得・依存導入は個別に行う。
Windows ネイティブの Git・Node、gh・gcloud・Docker・Android SDK は、この3アプリの一覧に含めていない。

## 更新とエラー時の扱い

Windows アプリは PowerShell スクリプト、WSL 内の共通設定・開発ツールは `u` で再適用する。
`u` には従来どおり apt upgrade、Node LTS / Firebase CLI の更新と VS Code 設定の上書きが含まれる。

スクリプトの終了コードは、依頼した範囲の完了が `0`、再起動 / ユーザー作成待ちが `2`、エラーが `1`。
winget の状態確認や WSL の起動に失敗した場合は、未導入と決めつけて再インストールせず停止する。
エラーを解消してから同じコマンドを再実行する。既に反映した設定を自動で元へ戻す処理はない。

WSL の導入エラーは [Microsoft の対処手順](https://learn.microsoft.com/windows/wsl/troubleshooting#installation-issues)、
`code` が見つからない場合は [VS Code の PATH 設定](https://code.visualstudio.com/docs/setup/windows)、
リソース上限の調整は [WSL の設定](https://learn.microsoft.com/windows/wsl/wsl-config#main-wsl-settings)を参照。

## 検証範囲と導入元

ローカルの Bash テストと、GitHub Actions の Windows PowerShell 5.1 / PowerShell 7 で、
コマンドをスタブ化して分岐・引き継ぎ・失敗時の停止を検証する。
実際の WSL 初回導入、再起動、winget のインストーラー、VS Code / Codex の接続は実機での確認が必要。

- [WSL の導入と初回ユーザー設定](https://learn.microsoft.com/windows/wsl/install)
- [winget の導入済みアプリ確認](https://learn.microsoft.com/windows/package-manager/winget/list)
- [Codex / ChatGPT デスクトップ版の公式 Windows 導入](https://learn.chatgpt.com/docs/windows/windows-app)
- [VS Code と WSL](https://code.visualstudio.com/docs/remote/wsl)
