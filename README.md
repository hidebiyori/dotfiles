# dotfiles

hidebiyori の複数端末で、シェル等の共通設定と開発ツールを一括セットアップ・更新するためのリポジトリ。

- `src/`: Bash・Vim・Git・Codex 等の設定ファイル。ホームディレクトリへシンボリックリンクで配置する。
- `bin/install.sh`: このリポジトリの取得・更新、設定のリンク、OS 別のセットアップ、
  mise・Node（mise）・Flutter・Firebase 等の導入をまとめて行う。
- 主な一括セットアップ対象は Mac と Chromebook の Linux 開発環境。
  Linux 分岐は apt と ChromeOS の共有フォルダを前提としている。
  Windows では WSL の環境に応じて内容を確認し、Git Bash では必要な設定・手順を個別に利用する。
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

## Codex

- ユーザー共通の指示は `src/.codex/AGENTS.md` で管理する。
- 既存の `bin/install.sh` が `~/.codex/AGENTS.md` へのシンボリックリンクを作成する。
- Codex の設定だけを適用する場合（既存ファイルがある場合は先に退避する）:

  ```bash
  mkdir -p "${HOME}/.codex"
  ln -s "${HOME}/git/dotfiles/src/.codex/AGENTS.md" "${HOME}/.codex/AGENTS.md"
  ```

- `CODEX_HOME` を設定している環境では、リンク先をそのディレクトリに変更する。
- 反映には Codex の新しいセッションを開始する。`AGENTS.override.md` がある場合はそちらが優先される。
- 方針: 作業完了・検証後に今回の変更だけをコミットし、push は明示的な依頼時に行う。

## 個人共通のスキル

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
既存どおり OS のパッケージ更新や Node・Flutter・Firebase の導入も行う。
Linux 分岐には Chromebook 固有のリンク作成等もあるため、WSL ではその内容を確認する。
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

### Node を nvm から mise に移行する

一括スクリプトは nvm を取得せず、次で Node の LTS を共通の既定値として設定する。
Firebase CLI は mise の Node を明示してインストールするので、
非対話シェルや実行元プロジェクトの Node 設定に依存しない。

```bash
mise use --global node@lts
mise exec node@lts -- npm install -g firebase-tools
```

この部分だけを実行すれば、OS 全体や Flutter を更新せずに Node を移行できる。
LTS は固定バージョンではなく、一括スクリプトの再実行時には新しい LTS に更新され得る。

`.bash_profile` の nvm 初期化は削除済み。既に開いているシェルには nvm の関数や
PATH が残るため、端末アプリを終了して開き直す（`r` だけでは残る）。
別のシェル設定に nvm の初期化や PATH がある場合も取り除く。
その後、次の結果が nvm 配下ではなく mise 管理の Node を指すことを確認する。

```bash
command -v node
node --version
npm --version
mise which node
firebase --version
```

以前の `~/.config/nvm`（別方式では `~/.nvm`）やグローバルパッケージは
自動削除・移行しない。必要なら切替前に `npm ls -g --depth=0` で一覧を控え、
必要なものだけ mise 側で再導入する。グローバルパッケージは Node のバージョンごとに
再導入が必要になる場合がある。プロジェクトの動作確認後、不要になった
nvm ディレクトリを手動で削除する。Flutter の管理方法は変更しない。
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
[シェルの有効化](https://mise.jdx.dev/cli/activate.html)。
