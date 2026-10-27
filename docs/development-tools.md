# 開発ツール

## 手動配置のリンクとシェル設定

`.bashrc` の `AP1_ROOT`・`AP2_ROOT`・`DOC_MAIN` と関連エイリアス、Vim の配置、
`.screenrc` のタブ番号・起動コマンドは、手動で配置したシンボリックリンクや作業場所を参照する前提で使う。
参照先の取得・作成は利用者が行う。dotfiles の整理・公開情報の見直し・ツール管理の変更だけを理由に、
これらのパスや関連設定を変更・削除・改名しない。変更するのは利用者が明示的に指定した場合に限る。

`r` で設定を再読み込みしても履歴の同期処理は重複登録しない。
既存の `PROMPT_COMMAND` が文字列または配列の場合も、登録済みの処理を保つ。
PATH は先に現れた要素を残して重複を除き、再読み込みで同じパスを増やさない。
設定済みの優先順と、明示された空要素（現在のディレクトリ）は一つずつ保持する。
screen はホームで対話端末を開いた場合に自動起動する。非対話処理や入出力が端末でない場合は起動しない。

`git p` は作業を一時退避し、`master` または `main` を fast-forward 更新して、
マージ済みの作業ブランチを削除する。`master` と `main` は削除しない。
今回退避した作業だけをステージ状態も含めて復元し、以前の stash は維持する。
更新や復元に失敗した場合は退避データを残すため、表示された stash を確認してから復元する。

`git ua` は ignore 対象を除いた未追跡ファイルだけを追加する。
空白・改行・先頭の `--` やパターン記法を含む名前もファイル名として扱い、
追跡済みファイルの変更・削除と、既存のステージ内容は維持する。

`git cl` は現在のブランチを fast-forward 更新した後、マージ済みのローカル作業ブランチを削除する。
`main`・`master`・`origin/HEAD` で分かる既定ブランチと、worktree で使用中のブランチは維持する。
削除対象がなくても正常終了し、取得失敗や履歴の分岐があればブランチ削除へ進まない。

## mise / Python / Node / npm / Firebase CLI

グローバル設定は [`src/.config/mise/config.toml`](../src/.config/mise/config.toml) で管理し、
セットアップで `~/.config/mise/config.toml` へリンクする。
共通の既定値は Python の `3.14`、Node の `lts`、npm と `npm:firebase-tools` の `latest`。
npm と Firebase CLI はそれぞれ独立したツールとして管理する。
バージョン方針を変える場合はこのファイルを編集する。

`bin/install.sh` は設定を書き換えず、ホームを基準に設定済みツールを導入する。
設定だけを反映する `u` ではツールを導入せず、共通ツールの更新は `up` で行う。
実行元プロジェクトの指定や対話シェルの有効化には依存しない。
プロジェクトでは、そのリポジトリの `mise.toml` を優先する。
プロジェクト用の `mise.lock` の要否と CI での固定は、[共通の保守方針](repository-maintenance.md#miselock-の採用)を参照する。
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
mise which python3
mise which node
mise which npm
mise which firebase
python3 --version
node --version
npm --version
firebase --version
```

Zsh では Homebrew の shellenv 設定より後の `.zshrc` に `eval "$(mise activate zsh)"` を追加する。
Bash 設定全体を Zsh から読み込まない。

### ツールの導入と更新

共通設定のリンク後、ツールだけ導入する場合:

```bash
mise install --cd "$HOME" --jobs 1
```

共通ツールだけを明示更新する場合は `mise upgrade --global --jobs 1 --no-prune`。
Firebase CLI だけなら末尾に `npm:firebase-tools` を加える。
ツールは mise の個別ディレクトリへ導入し、Node のグローバルパッケージ領域へ直接追加しない。
既存のグローバル版は自動削除せず、反映後に `command -v firebase` と `mise which firebase` が同じ実体を指すことを確認する。
プロジェクトで別のバージョンを指定する例は `mise use node@24`。
設定を確認してから `mise install` し、非対話のスクリプトや CI では `mise exec -- <command>` を使う。
mise 本体の更新は導入元の apt / Homebrew / winget で行う。

### 共通環境の更新

`u` は `bin/update.sh`、`up` は `bin/upgrade.sh` を呼ぶ。
前者は設定の同期・反映だけ、後者は設定の同期後に導入済みの共通環境を更新する。
Git の更新前に、指定先がチェックアウトのルートで、origin が想定するリポジトリであることを確認する。
origin の URL が想定外・未登録・複数登録の場合や、親ディレクトリの Git 管理が見つかった場合は変更せず停止する。
同じ GitHub リポジトリの HTTPS / SSH 接続と、チェックアウトへの手動リンクは利用できる。
現在のブランチが origin の単一ブランチを追跡することも確認し、その取得先を明示して更新する。
追跡先が未設定・別 remote の場合や detached HEAD では停止し、ブランチや追跡先を自動変更しない。
Git を更新した後、新しく取得した入口スクリプトと共有処理を別の Bash プロセスで読み込んで実行する。
設定反映のために Git の更新を再度実行せず、取得が失敗した場合は設定反映やパッケージ更新へ進まない。

```bash
u
up
```

`up` は Linux / WSL では apt、Mac では Homebrew の formula と導入済みの管理対象 cask、
続いて mise のグローバル設定のツールを1並列で更新する。WSL では Windows 側の管理対象アプリも更新する。
不足する mise や Homebrew は自動導入せず、初期セットアップを案内して停止する。
アプリの不足分、スキル用 Python、Flutter SDK は更新コマンドで新規導入・再作成しない。

mise は `--global` でプロジェクトの設定・環境変数・lockfile を読み込まず、`--bump` も指定しない。
旧バージョンは `--no-prune` で保持する。Python の `3.14` はその系列内、Node の `lts` と
npm / Firebase CLI の `latest` はメジャー更新も含む指定なので、追従範囲は共通設定で決める。
プロジェクトのランタイム指定、npm 依存、Flutter の依存更新は各プロジェクトで実施する。
通信・権限・更新処理が失敗した場合は停止し、自動で巻き戻さない。
[mise upgrade](https://mise.jdx.dev/cli/upgrade.html)。

初期セットアップと更新の入口は `bin/`、共有する処理は `lib/install/` の
`common.sh` / `macos.sh` / `linux.sh` / `wsl.sh` に置く。`src/` はホームに配置する設定を管理する。

[mise の公式手順](https://mise.jdx.dev/installing-mise.html)、[シェルの有効化](https://mise.jdx.dev/cli/activate.html)。

### CLI とプロジェクト依存の分担

端末共通の CLI は mise のグローバル設定で管理し、プロジェクト固有のバージョンはその `mise.toml` で指定する。
npm 配布の CLI は `npm:<パッケージ名>` を使う。[npm backend](https://mise.jdx.dev/dev-tools/backends/npm.html)を参照。
プロジェクトの `package.json` にある開発ツールとライブラリは、その依存定義と npm スクリプトで管理する。

## Python（ユーザー共通）

通常使う `python` / `python3` は、mise のグローバル設定で `3.14` 系を選ぶ。
同じ系列のパッチ更新を取り込み、別のマイナーバージョンへ移す場合は共通設定を明示的に変更する。
Python だけを導入・確認する場合:

```bash
mise install --cd "$HOME" --jobs 1 python
mise exec --cd "$HOME" -- python3 --version
```

プロジェクトで別の系列が必要な場合だけ、そのルートで `mise use python@3.13` などを指定する。
ライブラリは各プロジェクトの仮想環境で管理し、共通 Python へ一括導入しない。
既存の仮想環境はそのまま利用する。Python の系列を切り替える必要がある場合は、
そのプロジェクトの手順で仮想環境を作り直す。

初回セットアップ用の Python は引き続き apt / Homebrew で準備する。
OS の Python とスキル用の既存仮想環境は、mise の共通 Python を追加しても置き換えない。
[mise の Python 管理](https://mise.jdx.dev/lang/python.html)を参照。

## FFmpeg（プロジェクトごと）

動画・音声処理に必要なリポジトリの `mise.toml` で `conda:ffmpeg` のバージョンを指定する。
導入方法・必要なコーデック・対応プラットフォームと lockfile は、そのプロジェクトで管理する。
Conda 自体の別途導入は不要。FFmpeg を共通ツールや OS の一括インストール対象へ追加しない。

対象プロジェクトの設定を確認してから、そのルートで導入・確認する。
lockfile がある場合は、そのプロジェクトの `--locked` を使う手順に従う。

```bash
mise trust
mise install --jobs 1 conda:ffmpeg
mise exec -- ffmpeg -version
mise exec -- ffprobe -version
```

非対話のスクリプトや systemd でも `mise exec --cd <プロジェクトのルート> -- <コマンド>` を使い、
必要なコーデック・フィルターと実処理をプロジェクト側で検証する。
[mise の conda backend](https://mise.jdx.dev/dev-tools/backends/conda.html)を参照。

## ZIP の展開・検証（unzip）

Linux / Chromebook / WSL では `bin/install.sh` が apt の共通パッケージとして `unzip` を導入する。
apt は導入済みのパッケージを再利用する。macOS は OS 付属の `unzip` を使う。

Linux / Chromebook / WSL で `unzip` だけを追加する場合:

```bash
command -v unzip >/dev/null 2>&1 || sudo apt install --no-install-recommends unzip
```

導入後はターミナルを開き直さず、次で確認できる。

```bash
command -v unzip
unzip -v
```

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

`gh auth status` がトークン無効と表示しても、通信できない場合に同じ表示になることがある。
すぐに再ログインせず、`gh api user --jq .login` で認証済みのアカウントを再確認する。
失敗した場合は接続・認証・対象リポジトリの権限を切り分け、認証情報の値は出力しない。

## Flutter（任意）

通常のセットアップでは Flutter を導入・更新しない。必要な端末だけ次を実行する。
通常の一括セットアップも併せて行う。既存の Flutter と Bash の PATH は維持する。

```bash
INSTALL_FLUTTER=1 bash ~/git/dotfiles/bin/install.sh
```

Flutter SDK の使用バージョンはプロジェクトの `mise.toml` で指定できる。
依存パッケージの更新は SDK の選択とは別の操作で、対象プロジェクトの mise タスクにまとめる。
共通の `updateFlutter` / `updateFirebaseFunctions` 関数と、それらを呼ぶ `n` エイリアスは定義しない。

プロジェクトの `mise.toml` に記載する例:

```toml
[tasks."deps:update"]
description = "pubspec.yaml の制約内で依存パッケージを更新"
run = "flutter pub upgrade"
```

プロジェクト内で `mise run deps:update` を実行し、そのプロジェクトの解析・テストで検証する。
メジャー更新は必要なときに `flutter pub outdated` で確認し、`flutter pub upgrade --major-versions` を明示実行する。
[mise タスク](https://mise.jdx.dev/tasks/)、[Flutter の SDK と依存更新](https://docs.flutter.dev/install/upgrade)。

## スキル用 Python

スキル付属の Python スクリプトには `~/.local/share/codex-skill-python/bin/python` を使う。
セットアップは独立した仮想環境に `bin/requirements-skill-python.txt` の PyYAML を導入する。
通常の `python3` と各プロジェクトの依存関係は変更しない。導入済みなら再利用する。
セットアップ中の Python は隔離モードで呼び出し、作業フォルダーや `PYTHONPATH` のモジュールと、
`PYTHONOPTIMIZE` による最適化の影響を受けずに依存関係を確認する。

個別に準備する場合は、Linux では `python3-venv`、Mac では Homebrew の `python` を用意して次を実行する。

```bash
bash ~/git/dotfiles/bin/setup-skill-python.sh
```

検証スクリプトは、この Python を指定して実行する。Windows ネイティブは対象外。
環境が壊れた場合は自動削除せず、内容を確認・退避してから再構築する。
