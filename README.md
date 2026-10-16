# dotfiles

hidebiyori の複数端末で、シェル等の共通設定と開発ツールを一括セットアップ・更新するためのリポジトリ。

- `src/`: Bash・Vim・Git・Codex 等の設定ファイル。ホームディレクトリへシンボリックリンクで配置する。
- `bin/install.sh`: このリポジトリの取得・更新、設定のリンク、OS 別のセットアップ、
  デスクトップアプリ・mise・Node / npm（mise）・Firebase 等の導入をまとめて行う。Flutter は任意。
- `bin/install-windows.ps1`: Windows アプリの導入と WSL の準備、WSL 内の Git 取得・一括セットアップへの入口。
- 一括セットアップ対象は Mac、Chromebook の Linux 開発環境、Windows 11 の WSL2（Debian / Ubuntu）。
  Linux 分岐は apt を使用し、WSL では ChromeOS 専用処理を省く。
  Windows ネイティブの Git Bash では必要な設定・手順を個別に利用する。
- セットアップは既存の設定ファイルをリンクで置き換えるため、残したい設定は事前に退避する。
  パッケージ更新や開発ツールのダウンロードも伴う。mise だけを入れる場合は下記の個別手順を使う。

## 導入・更新の方針

- OS のパッケージマネージャー（apt / Homebrew / winget）を優先する。
- 取得したスクリプトをそのままシェルへ流す方法はなるべく使わない。
  `curl ... | sh` だけでなく `bash -c "$(curl ...)"` も避ける。
  スクリプトが必要な場合はファイルとして取得し、配布元と内容を確認してから実行する。
  配布元が署名・チェックサムを提供していれば、それも検証する。
- インストール済みの mise が生成する `eval "$(mise activate bash)"` や
  Homebrew の shellenv はローカルの信頼したコマンドの出力を読み込むために使う。
- 通信量を抑えるため、導入済みツールを活用し、検証のためだけの再インストールは行わない。
- 公開リポジトリの取得 URL に `GH_TOKEN` は使用せず、実行コマンドのトレースも無効にする。
  以前のセットアップで origin に認証情報付きの HTTPS URL が保存されていた場合は、
  同じ取得先であることを確認して公開 URL に置き換える。既存の SSH 接続先は維持する。
  push 等の認証は Git の credential helper や SSH で別途設定する。

初回は Git が導入済みの端末で次を実行する（既存の clone がある場合は取得を省く）。

```bash
mkdir -p "${HOME}/git"
git clone https://github.com/hidebiyori/dotfiles.git "${HOME}/git/dotfiles"
cd "${HOME}/git/dotfiles"
less bin/install.sh
```

内容を確認した後、別の操作として実行する。

```bash
bash bin/install.sh
```

完了後はターミナルを開き直す。更新・再適用は従来どおり `u`。
一括スクリプトはリポジトリの pull とツールの更新も行うため、
上記は実行内容を固定・検証する仕組みではない。
変更を事前確認したい場合は `git fetch` と `git diff HEAD..origin/main` で確認する。
Homebrew 未導入時の既存処理も配布アーカイブを取得・展開して実行するため、
可能なら事前に公式手順で Homebrew を導入し、配布元を信頼できることを確認する。

### 再実行時の動作

初回導入後も、同じコマンドや `u` で何度でも再適用できるようにしている。
ここでの冪等性は「導入済みのものや同じ設定を再利用する」という意味で、バージョンの固定ではない。
apt / Homebrew、Node LTS、npm、Firebase CLI 等の更新は再実行時にも行う。

- 同じ設定を指すリンクは作り直さない。設定ディレクトリ全体を手動でリンクしている場合も、
  そのリンクを再利用し、リンク元のファイルを書き換えない。
- Windows 版 VS Code の設定は、内容が変わった場合だけコピーする。
  初回と同様、リポジトリと異なる設定は管理対象の内容へ置き換える。
- Downloads / MyDrive に実ディレクトリや通常ファイルがあれば維持する。
  同じリンクは再利用し、既存フォルダの中へリンクを追加しない。
- 導入済みアプリや Python 環境、既存の Homebrew を再利用する。
  Homebrew が通常の導入先や `~/.config/brew` にあり PATH に未反映の場合も再検出する。
- Git の更新は fast-forward に限る。履歴の分岐や更新を妨げるローカル変更は自動で解消しない。

通信・権限・パッケージ管理・チェックサム等の実際の失敗は停止して知らせる。
原因を解消後、同じコマンドを再実行する。途中までの反映を自動で巻き戻す処理はない。
Homebrew の初回導入後の `brew doctor` は診断のため、指摘があっても案内を表示して続ける。
Windows の再起動・ユーザー作成待ちとアプリの更新指定は、
[Windows 手順](docs/windows-setup.md#更新とエラー時の扱い)と[アプリ管理](docs/desktop-apps.md)を参照する。

## デスクトップアプリ

管理対象は Codex / ChatGPT デスクトップ版、Chrome、VS Code。
CLI の `codex` はこの一覧には含めない。

| 環境 | 入口 | アプリの導入元 |
| --- | --- | --- |
| Mac | `bin/install.sh` | Homebrew cask |
| Chromebook | `bin/install.sh` | Codex / ChatGPT と VS Code は公式 deb、Chrome は ChromeOS 標準版 |
| Windows | `bin/install-windows.ps1` | winget / Microsoft Store |
| WSL | Windows 側で準備後に `bin/install.sh` | Windows アプリを利用し、Linux GUI アプリは重複導入しない |

不足分を導入し、導入済みアプリの入れ直しを省く。手動導入した Mac アプリも維持する。
Linux の更新は既存の apt 処理を使い、Mac / Windows の対象アプリだけを明示更新する方法も用意している。
配布名・管理対象の変更箇所・更新方法は[アプリ管理の手順](docs/desktop-apps.md)を参照する。

## Windows 11 / WSL2

初回は **Windows の通常の PowerShell から `bin/install-windows.ps1` を実行する**。
Git for Windows も、手動の `git clone` も事前準備には不要。
[Windows セットアップ手順](docs/windows-setup.md)に、ファイルの取得・確認・実行方法をまとめている。

- Windows 側: Codex / ChatGPT デスクトップ版・Chrome・VS Code を winget で導入し、WSL 拡張も追加する。
- WSL 未準備時: WSL の導入だけ管理者承認を求める。必要な再起動と Linux ユーザー作成後、同じコマンドを再実行する。
- WSL 準備後: WSL 内に Git を用意し、`~/git/dotfiles` へ clone / 更新して `bin/install.sh` を実行する。
- Windows アプリだけなら `-AppsOnly`。管理対象アプリの更新も行うなら `-UpgradeApps` を明示する。

WSL 側の開発リポジトリと依存ディレクトリは `/mnt/c` へ置かず、Linux 側の `~/git` を使う。
Windows / WSL の Node・npm・認証情報は別々に扱う。
Windows 側の再適用は PowerShell スクリプト、WSL 側の更新・再適用は従来どおり `u`。

Codex の実行環境はスクリプトでは切り替えない。導入後にアプリの **Settings → Agent environment → WSL** を選び、
統合ターミナルも **Integrated terminal shell → WSL** に設定してアプリを再起動する。
詳細は [Codex を WSL で使う設定](docs/windows-setup.md#codex-を-wsl-で使う設定)を参照。

## GitHub CLI の初回認証

GitHub CLI（`gh`）は全対応環境のセットアップで導入する。
Mac は Homebrew、Chromebook / Debian・Ubuntu / WSL は apt、Windows は winget の `GitHub.cli` を使う。
Windows の `-AppsOnly` でも導入し、`-UpgradeApps` の明示更新対象にも含める。
認証は利用者が初回に行う。Codex がコマンドを実行する環境のターミナルで実行する。
WSL を使う場合は WSL 内で行い、Windows 側の認証とは別に確認する。

```bash
gh --version
gh auth login --hostname github.com --git-protocol https --web
gh auth status
```

表示された URL をブラウザーで開き、案内に従って自分の GitHub アカウントで認証する。
共通 Git 設定は GitHub / Gist の HTTPS 認証に PATH 上の `gh auth git-credential` を使う。
認証情報は各環境の `gh` が保持し、リポジトリには保存しない。
SSH の remote を使う場合は別途 SSH 認証が必要。認証済みなら再ログインは不要。
[GitHub CLI の認証コマンド](https://cli.github.com/manual/gh_auth_login)も参照。

PR 作成には対象リポジトリ（または fork）への push 権限と、コミット用の名前・メールも必要。
対象のリポジトリ内で確認し、未設定の項目は自分の情報で設定する。

```bash
git config --get user.name
git config --get user.email
git remote -v
```

## Flutter（任意）

通常の `bin/install.sh` / `u` では Flutter の導入・更新・precache・doctor を実行しない。
Flutter も必要な端末では、次のように一度の実行に限って指定する。

```bash
INSTALL_FLUTTER=1 bash bin/install.sh
```

このコマンドは Flutter だけでなく、通常の一括セットアップも行う。
既存の Flutter ディレクトリや Bash の Flutter 用 PATH・補助関数は維持する。
導入済みの Flutter を引き続き利用でき、明示的な補助コマンドによる更新も従来どおり行える。

## Codex

- ユーザー共通の指示は `src/.codex/AGENTS.md` で管理する。
- 既存の `bin/install.sh` が `~/.codex/AGENTS.md` へのシンボリックリンクを作成する。
- Codex の設定だけを適用する場合（既存ファイルがある場合は先に退避する）:

  ```bash
  mkdir -p "${HOME}/.codex"
  ln -s "${HOME}/git/dotfiles/src/.codex/AGENTS.md" "${HOME}/.codex/AGENTS.md"
  ```

- セットアップは `CODEX_HOME` が指定されていれば、その保存先にも `AGENTS.md` をコピーする。実行環境の絶対パスで指定する。
- WSL で `CODEX_HOME` が未指定の場合は、Windows 側の環境変数、未設定なら `%USERPROFILE%\.codex` を取得して配置する。Windows アプリからも読めるようコピーし、既存の指示は置き換える。
- `~/.codex` の共通指示リンクも維持する。認証・履歴・その他の設定ファイルは同期しない。
- コピー先はシンボリックリンクのようには即時同期されない。共通指示を編集・取得した後は `u` または [共通指示だけの再適用](docs/windows-setup.md#codex-共通指示の更新と同期)を実行する。
- 反映には Codex の新しいセッションを開始する。`AGENTS.override.md` がある場合はそちらが優先される。
- 方針: 作業が一段落し、必要な検証と差分確認を終えた変更だけをコミット・push し、原則として PR 作成・必須 CI 確認・マージまで進める。ローカルのみ・レビュー待ち等の個別指定は優先する。マージで公開が起動する場合は結果と必要な公開確認まで行う。

### Chromebook で Codex / ChatGPT を最大化して起動

Linux アプリが毎回小さいウィンドウで起動する場合は、次の設定を一度実行する。
追加パッケージの導入やアプリの再起動は行わない。

```bash
python3 ~/git/dotfiles/bin/setup-chatgpt-maximized.py
```

`~/.local/bin/chatgpt-maximized` とユーザー用の `chatgpt.desktop` を配置し、
通常のアプリアイコンから補正ランチャーを使う。
名前・アイコン・ファイル関連付けは既存の desktop entry を引き継ぐ。
次回、アプリを終了した状態からアイコンで起動すると、
`~/.codex/.codex-global-state.json` の最大化フラグを `true` に補正して起動する。
`CODEX_HOME` を指定している場合はその保存先を使う。
既に起動している場合は保存情報を変更せず、既存のアプリへ起動引数を渡す。
`/usr/bin/chatgpt` を直接実行する場合は補正されない。
`bin/install.sh` の WSL 以外の Linux セットアップでも、アプリ導入済みの場合に適用する。

補正前の保存情報は、同じフォルダの
`.codex-global-state.json.before-maximized-launcher` へ直前の一世代を退避する。
保存情報と退避ファイルは本人だけが読み書きできる権限で配置し、Git には含めない。
アプリの内部保存形式を利用するため、不正な JSON や想定外の保存形式では
保存情報を変更せず、通常の起動を続ける。

起動せずに補正処理だけを確認する場合:

```bash
~/.local/bin/chatgpt-maximized --prepare-only
```

元に戻す場合は、ユーザー用の `~/.local/share/applications/chatgpt.desktop` を削除する。
設定前にユーザー用の desktop entry が存在していた場合は、削除の代わりに
`~/.local/state/dotfiles/chatgpt.desktop.before-maximized-launcher` から復元する。
`XDG_DATA_HOME` / `XDG_STATE_HOME` がある場合は、それぞれの保存先を使う。
必要に応じて `update-desktop-database ~/.local/share/applications` を実行する。
ランチャーのリンクも不要なら `~/.local/bin/chatgpt-maximized` を削除する。

### Chromebook の Chrome / Playwright 接続

Playwright MCP は通常、既存の `~/.codex/config.toml` の `[mcp_servers.playwright]` で
`enabled = false` にし、必要なブラウザ検証の時だけチャット専用クライアントを起動・終了する。
実行パス・引数は残す。`AGENTS.md` への指示だけでは MCP の自動起動は止まらない。

ChromeOS 側の Chrome に導入済みの拡張機能を Linux 側から自動検出できない場合は、
[Playwright MCP の接続リンクを使う手順](docs/playwright-extension.md)を参照する。
共通の `AGENTS.md` からも参照し、他のプロジェクトで同じ接続方法を利用できる。

### Firebase / GitHub Actions の公開認証

別プロジェクトで設定した認証を調べる順序と、既存 ADC の利用、鍵を作らない
GitHub OIDC の方針は [Firebase 公開認証の手順](docs/firebase-deploy-auth.md)を参照する。
共通の `AGENTS.md` からも参照する。

## 個人共通のスキル

### スキル用 Python 環境

`bin/install.sh` は `~/.local/share/codex-skill-python` に共通の仮想環境を作り、
`bin/requirements-skill-python.txt` の PyYAML を導入する。
システム Python や各リポジトリの依存関係は変更せず、通常の `python3` の参照先も変えない。
導入済みで指定バージョンを満たす場合は通信・再インストールを省く。

今回の環境だけを準備する場合は、一括セットアップを実行せず次の手順を使う。

```bash
# Debian / Ubuntu / Chromebook / WSL: venv が未導入の場合のみ
sudo apt install python3-venv
# macOS: Python 3 が未導入の場合のみ brew install python
bash ~/git/dotfiles/bin/setup-skill-python.sh
```

任意のリポジトリから標準のスキル検証を実行できる。

```bash
~/.local/share/codex-skill-python/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/.agents/skills/npm-vulnerability-remediation
```

`CODEX_HOME` が異なる場合やスキルの配置が変わった場合は、検証スクリプトのパスを合わせる。
環境が壊れた場合は自動で削除しない。Python の更新後などに実行できなくなった場合は、
内容を確認して退避してからセットアップし直す。Windows ネイティブはこの手順の対象外。

### 管理するスキル

- 自作スキルは `src/.agents/skills/<skill-name>/SKILL.md` で管理する。
- `bin/install.sh` は各ファイルを `~/.agents/skills` 以下へリンクする。
- `japanese-commit`: 日本語の件名と複数行の本文で、変更内容・理由・検証結果を記載する。共通の `AGENTS.md` からコミット時の利用を指示する。
- `npm-vulnerability-remediation`: Dependabot の検知を確認し、`npm update` を優先して修正・検証する。`npm audit` は診断用に使い、残る問題は依存経路と対応条件を記録する。
- スキルだけを適用する場合（同名の既存フォルダがないことを確認して実行）:

  ```bash
  mkdir -p "${HOME}/.agents/skills"
  ln -s "${HOME}/git/dotfiles/src/.agents/skills/npm-vulnerability-remediation" "${HOME}/.agents/skills/npm-vulnerability-remediation"
  ```

- ファイル単位でインストールしたスキルを削除・改名した場合は、配置先に残る古いリンクも削除する。

## mise

既存の `bin/install.sh` / `u` で mise も一括導入する。
Mac は Homebrew、Chromebook / Debian・Ubuntu / WSL は extrepo と apt を使う。
PATH 上または `~/.local/bin/mise` に導入済みなら追加インストールを省く。
既存どおり OS のパッケージ更新や Node / npm・Firebase の導入も行う。Flutter は明示指定した場合のみ導入・更新する。
WSL では Windows 用の連携処理を選び、Chromebook 固有のリンク作成や GUI ツールの導入を省く。
Windows ネイティブは一括スクリプトの対象外で、下記の Git Bash 手順を使う。

以下は mise だけを個別に導入する場合の手順。

### Chromebook / Debian・Ubuntu / Windows の WSL

Chromebook は Linux 開発環境のターミナル、WSL は Linux 側で実行する。
対象は Debian 11 以降 / Ubuntu 22.04 以降（`cat /etc/os-release` で確認）。

```bash
sudo apt update
sudo apt install -y extrepo
sudo extrepo enable mise
sudo apt update
sudo apt install -y mise
```

最初の update は extrepo の取得用、2 回目は追加した mise リポジトリの取得用。
`extrepo enable mise` が失敗した場合はそこで止め、OS の対応状況やエラーを確認する。
Windows 側に導入した mise と WSL 側の mise・管理ツールは別々に扱う。

### macOS

Homebrew が導入済みで `brew --version` が通るターミナルで実行する。
未導入の場合は [Homebrew の公式手順](https://brew.sh/) で導入し、
インストーラーが示す shellenv の設定を済ませる。

```bash
brew install mise
```

この dotfiles の Bash 設定は標準の Homebrew（Apple Silicon / Intel）と
従来の `~/.config/brew` を考慮している。Zsh を使う場合は Bash 設定は読まれないため、
使用中の `${ZDOTDIR:-$HOME}/.zshrc` に次を一度だけ記載する。
Homebrew の shellenv 設定より後に置く。

```zsh
if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate zsh)"
fi
```

### Windows ネイティブ（Git Bash）

コマンドプロンプトで以下を実行し、インストール後は Git Bash を開き直す。

```bat
winget install --id jdx.mise --exact
```

Git Bash で `command -v mise` が通ることを確認し、次の Bash の有効化を行う。
見つからない場合は Windows 側の PATH に winget のインストール先が反映されているか確認する。
既存のセットアップ全体は Windows 対応済みではないため、`bin/install.sh` は実行せず、
mise の有効化ブロックだけを既存の `~/.bashrc` に追加する。
Windows ネイティブでは管理対象ツールやタスクも Windows に対応している必要がある。
Linux 向けの環境が必要な場合は、上記の WSL 手順を使う。

### Bash での有効化と確認

この dotfiles が配置済みなら `src/.bashrc` の設定で対話 Bash にのみ自動で有効化する。
未導入時は何もしない。PATH 上の mise を優先し、見つからなければ公式インストーラーの
配置先 `~/.local/bin/mise` を確認する。追加の activate 行は不要。
`.bash_profile` は既存の PATH を保持し、Flutter の設定後に `.bashrc` を読み込む。

未配置の場合は、既存の `~/.bashrc` に上記 `src/.bashrc` の mise ブロックだけを追加してもよい。
Bash ログインシェルでは既存の `~/.bash_profile` 等から `~/.bashrc` が読まれることも確認する。
Mac で Zsh を使う場合に `.bashrc` 全体を source しない。

ターミナルを開き直し、次で確認する。

```bash
command -v mise
mise --version
mise doctor
```

### Node / npm を mise で管理する

一括スクリプトは nvm を取得せず、次で Node の LTS と npm の最新安定版を共通の既定値として設定する。
npm は独立したツールとして mise で管理し、Node 付属版より優先する。
Firebase CLI は mise の Node と npm を明示してインストールするので、
非対話シェルや実行元プロジェクトの Node / npm 設定に依存しない。

```bash
mise use --global node@lts
mise use --global npm@latest
mise exec node@lts npm@latest -- npm install -g firebase-tools
```

この部分だけを実行すれば、OS 全体や Flutter を更新せずに Node / npm を移行できる。
すでに Node を mise で管理している端末では、2 行目だけで npm を追加できる。
`lts` / `latest` は固定バージョンではなく、一括スクリプトの再実行時には
新しい Node LTS と npm の最新安定版へ更新され得る。

`.bash_profile` の nvm 初期化は削除済み。既に開いているシェルには nvm の関数や
PATH が残るため、端末アプリを終了して開き直す（`r` だけでは残る）。
別のシェル設定に nvm の初期化や PATH がある場合も取り除く。
その後、次の結果が nvm 配下ではなく mise 管理の Node を指すことを確認する。

```bash
command -v node
node --version
npm --version
mise which node
mise which npm
firebase --version
```

以前の `~/.config/nvm`（別方式では `~/.nvm`）やグローバルパッケージは
自動削除・移行しない。必要なら切替前に `npm ls -g --depth=0` で一覧を控え、
必要なものだけ mise 側で再導入する。グローバルパッケージは Node のバージョンごとに
再導入が必要になる場合がある。プロジェクトの動作確認後、不要になった
nvm ディレクトリを手動で削除する。既存の Flutter 環境は削除しない。
`.nvmrc` があるだけで従来どおり自動選択されるとは扱わず、
プロジェクトに対応する Node バージョンを mise で設定する。

プロジェクトでバージョンを選ぶ例（設定ファイルの変更とダウンロードを伴う）:

```bash
mise use node@24
node --version
```

既存プロジェクトでは設定内容を確認してから `mise install` を実行する。
スクリプトや CI は対話シェルの activate に依存せず `mise exec -- <command>` を使う。
更新は導入元の apt / Homebrew / winget で行い、別方式で重複インストールしない。

参考: [mise の公式インストール手順](https://mise.jdx.dev/installing-mise.html)、
[シェルの有効化](https://mise.jdx.dev/cli/activate.html)、
[npm のバージョン管理](https://mise.jdx.dev/lang/node.html#pin-the-npm-version)。
