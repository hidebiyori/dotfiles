# Windows 11 / WSL2 の初回セットアップ

このリポジトリでは、Windows に WSL2 の Debian / Ubuntu を用意し、
その中で `bin/install.sh` を実行して開発環境を構築する。
Windows 側には VS Code と WSL 拡張を置き、Node・npm・Firebase CLI などは WSL 側で使う。

WSL を GUI で一つずつ手動インストールする必要はない。
Windows の `wsl --install -d Ubuntu` が必要な機能の有効化と WSL・Ubuntu の導入をまとめて行う。
ただし、現在の `bin/install.sh` は WSL が利用できる状態から開始する Bash スクリプトで、
Windows 側の準備を呼び出す PowerShell スクリプトはこのリポジトリにはない。
WSL の導入コマンドは [Microsoft の公式手順](https://learn.microsoft.com/windows/wsl/install)に従う。

## 全体の流れ

| 順番 | 実行する場所 | 作業 |
| --- | --- | --- |
| 1 | Windows の管理者 PowerShell | WSL2 と Ubuntu を導入 |
| 2 | Windows / Ubuntu 初回起動 | 必要な再起動、Linux ユーザー名とパスワードの設定 |
| 3 | Windows の通常の PowerShell | Windows 版 VS Code と WSL 拡張を導入 |
| 4 | WSL の Ubuntu ターミナル | Git を用意し、このリポジトリを取得・確認・実行 |
| 5 | 新しく開いた WSL ターミナル | ツールの確認、必要な認証とプロジェクトの準備 |

既に済んでいる段階は省く。Windows の PowerShell に Bash 用のコマンドを貼らず、
各段階の実行場所を確認する。Git Bash で一括スクリプトを実行する手順ではない。

## 1. Windows 側で WSL2 と Ubuntu を導入する

このリポジトリの Windows 向け一括セットアップ対象は Windows 11 の WSL2。
PC の仮想化機能が利用可能で、Windows の管理者権限とダウンロード用の通信が必要になる。

既存の WSL がある場合は、まず通常の PowerShell で確認する。
未導入時に利用できない旨が表示された場合は、下の導入へ進む。

```powershell
wsl --status
wsl --list --verbose
```

使う Ubuntu / Debian が既に存在し、`VERSION` が `2` なら導入を省き、次の段階へ進む。
既存のディストリビューションを削除・作り直す必要はない。

新規導入では、スタートメニューから PowerShell を「管理者として実行」し、次を実行する。
普段使う Windows アカウントで昇格する。別の管理者アカウントで作業すると、
WSL の導入先ユーザーが異なる場合がある。

```powershell
wsl --install -d Ubuntu
```

コマンドの案内に従って Windows を再起動する。
必要な Windows 機能、WSL のカーネル、Ubuntu の取得はこのコマンドに任せられる。
新規導入は WSL2 が既定になる。
[WSL の環境構築](https://learn.microsoft.com/windows/wsl/setup/environment)を参照。

Debian やバージョンを指定した Ubuntu を選ぶ場合は、`wsl --list --online` で名前を確認し、
`Ubuntu` をその名前に置き換える。以降の `wsl -d Ubuntu` なども同じ名前に合わせる。
現行スクリプトの mise 導入手順は Debian 11 以降 / Ubuntu 22.04 以降を対象としている。

## 2. Ubuntu を初回起動し、一般ユーザーを作る

再起動後、スタートメニューの Ubuntu、または通常の PowerShell から起動する。

```powershell
wsl -d Ubuntu
```

初回の案内に従って Linux ユーザー名とパスワードを設定する。
Windows のアカウントとは別で、このパスワードは後の `sudo` でも使う。
パスワード入力時に文字が表示されないのは通常の動作。
作成したユーザーは次回以降の既定ユーザーになる。
[Linux ユーザーの初期設定](https://learn.microsoft.com/windows/wsl/setup/environment#set-up-your-linux-username-and-password)を参照。

Ubuntu 側で `whoami` を実行し、作成した一般ユーザーであることを確認する。
`root` で `bin/install.sh` を実行すると root のホームへ設定してしまうため、
スクリプト全体を `sudo bash ...` で実行しない。

別の PowerShell で WSL2 であることも確認する。

```powershell
wsl --list --verbose
```

既存環境が `VERSION 1` の場合だけ、データをバックアップした上で次の変換を検討する。
`--set-default-version 2` は今後の新規導入の既定値で、既存環境の変換にはならない。
変換には時間や空き容量が必要になる。
[WSL の基本コマンド](https://learn.microsoft.com/windows/wsl/basic-commands#set-wsl-version-to-1-or-2)を参照。

```powershell
wsl --set-version Ubuntu 2
```

## 3. Windows 版 VS Code と WSL 拡張を導入する

普段使う Windows アカウントの通常の PowerShell で実行する。
導入済みのものは省く。

```powershell
winget install --id Microsoft.VisualStudioCode --exact --source winget
```

インストール後は PowerShell を開き直し、PATH を反映してから実行する。

```powershell
code --version
code --install-extension ms-vscode-remote.remote-wsl
```

`winget` が使えない場合は Windows の「アプリ インストーラー」を確認するか、
[VS Code 公式の Windows 用インストーラー](https://code.visualstudio.com/docs/setup/windows)を使う。
`code` が見つからない場合も、この段階で Windows 側の PATH を確認する。
Linux 版 VS Code を WSL 内に追加する必要はない。
[VS Code の WSL 手順](https://code.visualstudio.com/docs/remote/wsl)を参照。

## 4. WSL 内で dotfiles を取得・実行する

ここからは Ubuntu / Debian のターミナルで、作成した一般ユーザーとして実行する。
Windows 側の Git や Node を先に入れる必要はない。

Git が未導入の場合だけ、WSL 内で導入する。

```bash
sudo apt update
sudo apt install -y ca-certificates git
```

リポジトリは Linux 側の `~/git/dotfiles` に置く。
`bin/install.sh` はこの場所を使うため、別の場所の clone から実行してもここを取得・更新する。
既に clone があれば clone 操作を省き、未コミットの変更がないか確認する。

```bash
mkdir -p "${HOME}/git"
git clone https://github.com/hidebiyori/dotfiles.git "${HOME}/git/dotfiles"
cd "${HOME}/git/dotfiles"
less bin/install.sh
```

実行前に次を確認する。

- WSL 側の既存の `.bashrc`・`.bash_profile`・`.ssh/config`・Git 設定・Codex 指示などは、
  `src/` の設定へのリンクで置き換えられる。残したい設定を事前に退避する。
- Windows 側の通常版 VS Code の `%APPDATA%\Code\User\settings.json` と
  `keybindings.json` も上書きコピーされる。既存設定を退避し、VS Code を閉じてから実行する。
- スクリプトは開始時にリポジトリを `git pull` し、apt の更新・upgrade、Node LTS の設定、
  Firebase CLI の導入も行う。設定ファイルの配置だけでなく、通信と既存ツールの更新を伴う。

内容の確認・退避を済ませた後、別の操作として実行する。

```bash
bash bin/install.sh
```

`sudo` のパスワード入力と apt の確認に応答する。途中でエラーが出た場合は、
最後に表示されたエラーを解消して同じコマンドを再実行する。
一部の設定が既に反映されている可能性があり、自動で元へ戻る仕組みではない。
`Success:` の表示だけで Windows 連携まで成功したとは扱わず、次の確認も行う。

### このスクリプトが WSL で行うこと

| 対象 | 現在の処理 |
| --- | --- |
| リポジトリ・共通設定 | `~/git/dotfiles` の取得 / pull、`src/` の設定・スキルをホームへリンク |
| OS パッケージ | apt update / upgrade、screen・ca-certificates・curl・git・vim・python3-venv の導入 |
| mise | 導入済みなら再利用。未導入なら extrepo で配布元を追加し apt で導入 |
| Node / npm | mise で実行時点の Node LTS をグローバル設定 |
| Firebase CLI | mise の Node で firebase-tools をグローバル導入 |
| スキル用 Python | `~/.local/share/codex-skill-python` に venv と PyYAML 6.0.3 を準備。導入済みなら再利用 |
| Downloads | PowerShell で取得した Windows の実際の Downloads へリンク。WSL 側の既存の実ディレクトリは維持 |
| VS Code の共通設定 | Windows の通常版・既定プロファイルへ settings.json と keybindings.json をコピー |
| Flutter | `INSTALL_FLUTTER=1 bash bin/install.sh` と明示した場合だけ導入・更新 |

WSL では ChromeOS 用の MyDrive リンク・日本語入力・Linux 版 VS Code・最大化ランチャーは設定しない。
日本語入力は Windows Terminal / Windows 版 VS Code の Windows 側 IME を使う。

## 5. 完了確認と普段の使い方

WSL のターミナルを開き直し、WSL 内で確認する。

```bash
command -v git mise node npm firebase
mise --version
mise doctor
node --version
npm --version
mise which node
firebase --version
"${HOME}/.local/share/codex-skill-python/bin/python" -c 'import yaml; print(yaml.__version__)'
readlink "${HOME}/Downloads"
```

Node が mise 配下の Linux 用バイナリを指し、Windows の `/mnt/c/.../node.exe` などを
使っていないことを確認する。PyYAML の出力は `6.0.3`。
Downloads は、WSL 側の既存の実ディレクトリを維持した場合にはリンクにならない。
Windows 連携を省いたというメッセージがある場合は、下の対処を確認する。

ホームでターミナルを開くと、既存の設定どおり screen と作業用タブが起動する。
`app01-flutter`・`app02-nextjs` や個人メモを参照するタブ / 別名は、
それらのリポジトリやデータを取得するものではない。
タブ内に移動先がないという表示があれば、必要なプロジェクトを別途準備する。

VS Code を使うときは WSL 側のプロジェクト内で `code .` を実行し、
ウィンドウ左下に `WSL: Ubuntu` など対象の接続が表示されることを確認する。
初回は WSL 側の VS Code Server のダウンロードも発生する。
[VS Code の WSL 接続](https://code.visualstudio.com/docs/remote/wsl#_open-a-remote-folder-or-workspace)を参照。

開発リポジトリと `node_modules` は `/mnt/c` ではなく WSL 側の `~/git` 以下へ置く。
Windows と WSL の Node・npm・依存ディレクトリは共有しない。
[WSL のファイル保存先](https://learn.microsoft.com/windows/wsl/setup/environment#file-storage)を参照。

更新・再適用は WSL 内で `u` を実行する。リポジトリ・OS パッケージ・開発ツールの更新と、
Windows 側 VS Code 設定の上書きも再び行う。
既存の SSH 鍵や認証情報、個人データを新しい PC へ自動移行する処理はない。
GitHub の push 認証、Firebase 等のログイン、プロジェクトの依存導入は個別に行う。
Codex 本体・gh・gcloud・Docker・Android SDK の導入も一括スクリプトの対象外。
VS Code の設定ファイルをコピーしても拡張機能本体は導入されない。
Prettier 等の必要な拡張は、各プロジェクトに合わせて追加する。
[拡張機能の導入先](https://code.visualstudio.com/docs/remote/wsl#_managing-extensions)も確認する。

## どこまで自動化できるか

現時点でも、WSL の準備は Windows のコマンド、WSL 内の環境構築は `bin/install.sh` にまとめられる。
PC 初期化直後から一つのスクリプトで再起動をまたいで完了する入口は未実装。

| 作業 | 自動化の範囲 / 現在の状態 |
| --- | --- |
| WSL・Ubuntu の導入 | `wsl --install -d Ubuntu` でまとめて導入できる。現行 Bash スクリプトの外で実行 |
| VS Code・WSL 拡張の導入 | 上記の winget / code コマンドで導入できる。現行 Bash スクリプトの外で実行 |
| WSL 内の設定・開発ツール | 現行 `bin/install.sh` で自動化済み。ただし sudo と apt の対話入力あり |
| 管理者権限の承認・必要な再起動 | 今の手順では利用者が承認・再起動を行う |
| Linux ユーザー名・パスワード | 今の手順では初回起動時に利用者が設定 |
| 各サービスの認証 | 個別に実施。認証情報をスクリプトや Git へ埋め込まない |

さらに自動化するなら、Windows 側の PowerShell スクリプトを入口にして、
次の二段階に分ける構成にできる。以下は追加実装の案で、現時点では未実装。

1. Windows 側で既存の WSL・ディストリビューション・VS Code を確認して、足りないものだけを導入する。
   WSL の導入には `wsl --install -d Ubuntu --no-launch` を使い、必要な再起動の段階で一旦終了する。
2. 再起動と Linux ユーザー作成後、同じ入口を再実行して WSL の起動・WSL2・一般ユーザーを確認し、
   リポジトリ取得と内容確認を挟んで `bin/install.sh` へ引き継ぐ。

`--no-launch` は Ubuntu の自動起動を省くオプションで、再起動やユーザー作成を完了するものではない。
[WSL の install オプション](https://learn.microsoft.com/windows/wsl/basic-commands#install)を参照。
PowerShell で各段階をつないでも、現行 Bash スクリプトの sudo・apt の入力は残る。
完全無人化には、ユーザー作成、再起動後の再開、対話処理と失敗時の扱いも別途設計する必要がある。

## うまく進まない場合

| 状況 | 確認・対処 |
| --- | --- |
| WSL の導入が失敗する | Windows の更新状態、管理者権限、BIOS / UEFI の仮想化設定を確認し、[公式の対処手順](https://learn.microsoft.com/windows/wsl/troubleshooting#installation-issues)へ進む |
| WSL / Ubuntu の取得が 0.0% で止まる | 通常の導入を止めて原因を確認し、必要なら `wsl --install --web-download -d Ubuntu` を使う。[公式の代替手順](https://learn.microsoft.com/windows/wsl/install#install-wsl-command)を参照。通信量を減らす指定ではない |
| VS Code 設定・Downloads の連携を省いたと表示される | WSL 内で `command -v powershell.exe wslpath` が通るか確認する。Windows 実行ファイルとの連携や Windows フォルダへのアクセスを復旧してから再適用する |
| Node が Windows 側や古い nvm 配下を指す | WSL のターミナルを開き直し、[README の mise 移行手順](../README.md#node-を-nvm-から-mise-に移行する)で PATH と設定を確認する |
| PC の負荷が高い | 必要なら Windows 側の WSL 設定 / `%UserProfile%\.wslconfig` でメモリ・CPU・swap を調整する。一括スクリプトは変更しない。[公式の設定項目](https://learn.microsoft.com/windows/wsl/wsl-config#main-wsl-settings)を参照 |

## 検証範囲

この手順はリポジトリ内のスクリプトと Microsoft / VS Code の公式ドキュメントを照合して記載した。
WSL 分岐にはコマンドをスタブ化したローカルテストがあるが、
Windows 実機での WSL 初回導入・再起動・winget・VS Code 接続を検証したものではない。
