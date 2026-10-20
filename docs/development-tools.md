# 開発ツール

## 手動配置のリンクとシェル設定

`.bashrc` の `AP1_ROOT`・`AP2_ROOT`・`DOC_MAIN` と関連エイリアス、Vim の配置、
`.screenrc` のタブ番号・起動コマンドは、手動で配置したシンボリックリンクや作業場所を参照する前提で使う。
参照先の取得・作成は利用者が行う。dotfiles の整理・公開情報の見直し・ツール管理の変更だけを理由に、
これらのパスや関連設定を変更・削除・改名しない。変更するのは利用者が明示的に指定した場合に限る。

## mise / Node / npm

グローバル設定は [`src/.config/mise/config.toml`](../src/.config/mise/config.toml) で管理し、
セットアップで `~/.config/mise/config.toml` へリンクする。
共通の既定値は Node の `lts` と npm の `latest`。npm は独立したツールとして管理する。
バージョン方針を変える場合はこのファイルを編集する。

`bin/install.sh` は設定を書き換えず、ホームを基準に Node / npm を導入する。
Firebase CLI も同じ環境で導入するため、実行元プロジェクトの指定や対話シェルの有効化に依存しない。
プロジェクトでは、そのリポジトリの `mise.toml` を優先する。
Windows と WSL のツール・依存ディレクトリは別々に扱う。

### mise だけを導入する

導入済みなら再インストールしない。一括セットアップでは Mac は Homebrew、Linux / WSL は extrepo と apt を使う。
個別に準備する場合は環境に対応する手順を選ぶ。

Debian 11 以降 / Ubuntu 22.04 以降 / Chromebook / WSL:

```bash
sudo apt update
sudo apt install -y extrepo
sudo extrepo enable mise
sudo apt update
sudo apt install -y mise
```

macOS は [Homebrew](https://brew.sh/) を準備して `brew install mise`。
Windows ネイティブは `winget install --id jdx.mise --exact` を使う。
Git Bash では mise の有効化だけを個別設定し、`bin/install.sh` 全体は実行しない。

この dotfiles の対話 Bash は `.bashrc` で mise を有効化する。
PATH 上、次に `~/.local/bin/mise` を確認する。ターミナルを開き直し、次で確認する。

```bash
mise doctor
mise which node
mise which npm
node --version
npm --version
```

Zsh では Homebrew の shellenv 設定より後の `.zshrc` に `eval "$(mise activate zsh)"` を追加する。
Bash 設定全体を Zsh から読み込まない。

### ツールの導入と更新

共通設定のリンク後、ツールだけ導入する場合:

```bash
mise install --cd "$HOME" --jobs 1 node npm
mise exec --cd "$HOME" -- npm install -g firebase-tools
```

Node / npm を明示更新する場合は `mise upgrade --cd "$HOME" --jobs 1 node npm`。
グローバルパッケージは Node のバージョンごとに再導入が必要になる場合がある。
プロジェクトで別のバージョンを指定する例は `mise use node@24`。
設定を確認してから `mise install` し、非対話のスクリプトや CI では `mise exec -- <command>` を使う。
mise 本体の更新は導入元の apt / Homebrew / winget で行う。

[mise の公式手順](https://mise.jdx.dev/installing-mise.html)、[シェルの有効化](https://mise.jdx.dev/cli/activate.html)。

## GitHub CLI の初回認証

`gh` は全対応環境で導入する。Codex がコマンドを実行する環境で初回認証する。
WSL 内と Windows 側の認証は別々に扱い、認証済みなら再ログインしない。

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth status
```

表示された URL とコードで自分の GitHub アカウントへログインする。
共通 Git 設定は HTTPS 認証に `gh auth git-credential` を使う。SSH の接続先には別途 SSH 認証が必要。
PR 作成には push 権限とコミット用の `user.name` / `user.email` も必要。
認証値をリポジトリへ保存したり、接続先 URL や設定全体をそのまま表示したりしない。

## Flutter（任意）

通常のセットアップでは Flutter を導入・更新しない。必要な端末だけ次を実行する。
通常の一括セットアップも併せて行う。既存の Flutter と Bash の PATH は維持する。

```bash
INSTALL_FLUTTER=1 bash ~/git/dotfiles/bin/install.sh
```

## スキル用 Python

スキル付属の Python スクリプトには `~/.local/share/codex-skill-python/bin/python` を使う。
セットアップは独立した仮想環境に `bin/requirements-skill-python.txt` の PyYAML を導入する。
通常の `python3` と各プロジェクトの依存関係は変更しない。導入済みなら再利用する。

個別に準備する場合は、Linux では `python3-venv`、Mac では Homebrew の `python` を用意して次を実行する。

```bash
bash ~/git/dotfiles/bin/setup-skill-python.sh
```

検証スクリプトは、この Python を指定して実行する。Windows ネイティブは対象外。
環境が壊れた場合は自動削除せず、内容を確認・退避してから再構築する。
