# リポジトリ共通の設定と保守

言語やフレームワークに依存しない初期設定は、
[`src/project-presets/common/templates/`](../src/project-presets/common/templates/) で管理する。
各リポジトリへコピーして Git 管理し、CI と別の端末でも clone だけで使える状態にする。
セットアップや dotfiles の更新から、各プロジェクトへ自動反映しない。

## 実行ファイルの配置

ディレクトリ名は実装言語ではなく、コマンドの使い方で決める。
`bin/` にシェルや Python のスクリプトを置いてよく、コンパイル済みである必要はない。

| 場所 | 用途 |
| --- | --- |
| `bin/` | 利用者が直接呼ぶ CLI、セットアップ・更新・共通保守の入口 |
| `scripts/` | アプリ内のビルド・検証・公開など、そのプロジェクトの開発作業 |
| `lib/` | 入口から読み込む共有処理 |

両方の用途がある場合に分ける。既存の構成を名前の統一だけのために移動しない。
dotfiles は `bin/` を入口、`lib/install/` を共有処理とし、
`src/bin/` はホームへ配置するコマンドの原本として使う。
アプリでは [共通プリセットの規約](project-presets.md#ディレクトリとコマンドの規約)に従い `scripts/` を基本にする。

## mise.lock の採用

`mise.toml` はツールの要求バージョンを指定し、`mise.lock` は解決した正確なバージョンと、
対応する backend が提供する取得 URL・チェックサムを記録する。
たとえば `node = "24"` だけでは、導入時期によってパッチバージョンが変わり得る。

| 対象 | 方針 |
| --- | --- |
| mise でビルド・テスト・公開用のツールを管理するプロジェクト | `mise.toml` と `mise.lock` を Git 管理することを基本にする |
| プロジェクト固有の mise ツールがない文書・ノート集 | `mise.toml` や `mise.lock` を形式だけのために追加しない |
| dotfiles のユーザー共通ツール | グローバル設定の指定範囲で更新する。プロジェクト用のルート `mise.lock` は不要 |
| `mise.local.toml` 等の端末固有設定 | 対応する local lockfile も含めて Git 管理しない |

完全なバージョンを `mise.toml` に書けばバージョン自体は固定できるが、
取得情報も記録する lockfile は再現性の確認に役立つ。
`mise.lock` は npm 等の依存関係を固定しないため、`package-lock.json` や `uv.lock` も維持する。

プロジェクトへ導入する場合は、次の順で差分を確認する。

```bash
mise lock
mise install --locked --jobs 1
```

`mise lock` はツールをインストールせずに lockfile を生成するが、解決のための通信は発生し得る。
lockfile をコミットし、CI も `--locked` で導入する。
CI と利用端末の各プラットフォームに必要な取得情報が含まれることを確認する。
`.mise/locks/` に依存グラフの付随ファイルが生成された場合は、それも対応する lockfile と管理する。
端末固有の lockfile に対応する付随ファイルは除外する。
URL に認証情報が含まれないことも、コミット前に確認する。
`--locked` でも未取得のツール等には通信が必要で、オフライン導入を保証するものではない。

更新時は `mise lock --bump node` のように対象を絞り、必要な導入・検証後にコミットする。
既存プロジェクトへは、CI と対応環境を確認しながら個別に導入する。
[mise の lockfile](https://mise.jdx.dev/dev-tools/mise-lock.html)。

## 既定ブランチの保護

`Your main branch isn't protected` は、既定ブランチに保護が設定されていないことを示す。
この警告や設定への案内が表示されることだけで、現在のプランで保護を利用できるとは判断しない。
先に対象の公開範囲・所有者のプランと、公式の利用条件・設定やAPIの応答を確認する。
従来のbranch protectionとブランチのrulesetはいずれも、GitHub Freeでは公開リポジトリが対象で、
非公開リポジトリにはPro / Team / Enterprise等の対応プランが必要。
[branch protectionの利用条件](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)、
[rulesetの利用条件](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)。
HTTP 403だけでプラン制約と断定せず、プラン変更を求める応答か、権限不足など別の理由かを確認する。

プラン非対応を確認した場合は保護設定を中止し、同じ設定要求を繰り返さない。
アプリ・ツール・dotfilesは、PRと対象コミットのCI成功を作業手順で確認し、既定ブランチのforce pushと削除を行わない。
文書・ノート集の手動編集を許す例外は維持する。個別の `AGENTS.md` に、GitHub上では強制できない制約と運用を記録し、
プランや公開範囲が変わった場合に利用可否を再確認する。

保護設定を利用できる場合は、日常の編集方法に応じて次のいずれかを選び、個別の `AGENTS.md` に用途と例外を記載する。

| 項目 | アプリ・ツール・dotfiles | 手動で直接編集する文書・ノート集 |
| --- | --- | --- |
| 利用者の main への通常 push | PR を経由する | 許可する |
| PR | 必須 | 利用者の手動編集には必須にしない |
| 必須 CI | PR で実行される検証ジョブを登録する | 直接 push を許すため必須チェックは設定しない。push 後の CI は実行できる |
| 承認レビュー | 個人運用では必須人数を 0 にする | 必須にしない |
| force push・ブランチ削除 | 禁止 | 禁止 |

文書・ノート集では、Obsidian 等で手動で読み書きし、AI で分類・整理する運用を併用できる。
利用者の直接編集を許すことと、エージェントの通常作業を PR 経由にすることは両立する。
エージェントの直接 push も認める場合は、個別の指示で対象と条件を明記する。
直接 push 後の CI は事後検証なので、push 前の差分・リンク等の確認も行う。

新規の保護設定は Settings → Rules → Rulesets の branch ruleset を基本にし、
既定ブランチを対象に `Active` で適用する。
両方の運用で `Restrict deletions` と `Block force pushes` を有効にし、
管理者を含めて通常の bypass は設定しない。
直接編集する対象では `Restrict updates`、PR 必須、必須ステータスチェックを設定しない。

アプリ等では `Require a pull request before merging` と `Require status checks to pass before merging` を追加し、
対象ブランチを最新にする設定も有効にする。
必須チェックは、実際に PR で成功したジョブ名と提供元を確認して登録する。
文書だけの変更でも必須チェックが実行されるよう、workflow のパス条件等を確認する。
main へのマージ後にだけ実行する公開ジョブを、PR の必須チェックへ登録しない。
個人運用で承認者を確保できない場合も、承認人数 0 の PR と CI で運用できる。

ruleset と既存の branch protection は併せて適用され、厳しい方の条件が残る。
設定前に両方を確認し、既存の保護を不用意に置き換えない。
[設定できる保護ルール](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)。

共通方針の文書化だけでは GitHub 側の設定は変わらない。
適用対象、既存ルール、プラン、PR の検証ジョブを確認してからリポジトリごとに設定し、
設定の保存後は実際に有効なルールを再確認する。

## 改行・編集設定

導入済みの Python 3 で、変更予定を確認してから反映する。

```bash
python3 ~/git/dotfiles/bin/init-project-config.py /path/to/repository
python3 ~/git/dotfiles/bin/init-project-config.py /path/to/repository --write
```

通常実行はプレビューのみ。`--write` は存在しない `.editorconfig` と `.gitattributes` だけを作成する。
既存ファイルと手動配置のリンクは維持し、内容の統合は差分を見て個別に行う。
親ディレクトリがリンクの場合や、設定ファイルの場所にディレクトリがある場合は停止する。
コマンドはネットワーク通信、依存導入、Git 操作を行わない。
Windows ネイティブで Python が導入済みなら `python3` の代わりに `py -3` を使える。

- `.editorconfig`: UTF-8、LF、最終改行、スペース2個。Python は4個、Makefile はタブ、
  Markdown は末尾スペースを維持する。
- `.gitattributes`: テキストは LF、`.bat` / `.cmd` は作業ツリーで CRLF とする。
  EditorConfig も同じ拡張子の例外を指定する。バイナリは Git の自動判定で変換を避ける。

既存のファイルを一括整形・再正規化する処理は含めない。
既存リポジトリへの導入では `git diff` と `git ls-files --eol` で影響を確認し、
意図した改行変更だけをコミットする。文字コード変換は別途判断する。
[Git のファイル属性](https://git-scm.com/docs/gitattributes)。

これらは初期テンプレートで、作成後は各リポジトリの設定として管理する。
原本の更新時は必要な差分を比較して取り込み、プロジェクト固有の例外を維持する。
Next.js の初期化でも同じ原本を使う。
[Next.js の共通設定](project-presets.md)を参照する。

## 依存更新

GitHub Actions だけを使うリポジトリ:

```bash
python3 ~/git/dotfiles/bin/init-project-config.py /path/to/repository --github-actions
python3 ~/git/dotfiles/bin/init-project-config.py /path/to/repository --github-actions --write
```

Node / npm のアプリでは次の `--node` を使う。npm と GitHub Actions の設定を用意する。
どちらの雛形も `open-pull-requests-limit: 0` とし、通常更新 PR は作らない。
脆弱性はアラートで確認し、修正を手動で行う。
セキュリティ更新 PR も停止するには、次の GitHub 側の設定を別途実施する。
将来バージョン更新 PR を使う場合は、各リポジトリで上限を変更する。
雛形のスケジュールは月曜の週次、minor / patch はグループ化、major は別 PR としてある。
[Dependabot の設定](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)。

`.github/dependabot.yml` / `.github/dependabot.yaml` が既にあれば維持する。
対象ディレクトリがルート以外の場合や、他のパッケージ管理方式を使う場合は、
既存設定と雛形を比較して対象・更新頻度・例外を各リポジトリで調整する。
dotfiles 自身には GitHub Actions 用の設定を導入している。

## GitHub 側の Dependabot 設定

通常のバージョン更新 PR は `.github/dependabot.yml` の
`open-pull-requests-limit: 0` で停止できる。
セキュリティ更新 PR はこの上限に含まれず、GitHub 側の設定で停止する。
脆弱性の通知を受ける Dependabot alerts は有効に保ち、修正は手動で確認する。

GitHub CLI (`gh`) で認証済みの環境から、対象を明示して実行する。

```bash
python3 ~/git/dotfiles/bin/configure-dependabot.py OWNER/REPO
python3 ~/git/dotfiles/bin/configure-dependabot.py OWNER/REPO --write
```

通常実行でも API で現在の状態を読み取るが、設定は変更しない。
`--write` は管理権限を確認した対象1件の Dependabot security updates を無効にし、
Dependabot alerts を有効にして、反映後の両方の状態を再確認する。
設定済みなら変更リクエストは送らない。対象は github.com の `OWNER/REPO` に限定し、
URL・Git remote・全リポジトリ一覧から対象を推測しない。
fine-grained token を使う場合はリポジトリの Administration の書き込み権限が必要。
通信は1件ずつ、応答後に最低1秒空け、権限不足・アクセス制限時は再試行せず停止する。
変更直後に旧状態が返る場合だけ、読み取りを最大3回まで行って反映を待つ。
変更リクエスト自体は繰り返さない。
途中で失敗した場合、設定を自動で巻き戻さず、原因を確認して同じコマンドを再実行する。

使用する公式 API は
[security updates の確認・停止](https://docs.github.com/en/rest/repos/repos#disable-dependabot-security-updates)と
[alerts の確認・有効化](https://docs.github.com/en/rest/repos/repos#enable-vulnerability-alerts)。
依存ファイル・workflow・既存 PR のクローズ・Watch・メール通知設定は変更しない。
PR を作る auto-triage rules も変更しないので、存在する場合は次の項目で確認する。

## 新規リポジトリ作成時のチェックリスト

- [ ] [初期設定](#改行編集設定)を導入し、用途に応じて Node CI などを選ぶ。
- [ ] [ツールの固定方針](#miselock-の採用)を選び、採用時は lockfile と CI の `--locked` を揃える。
- [ ] [既定ブランチの保護](#既定ブランチの保護)の利用可否を先に確認し、利用できる場合は保護を設定する。利用できない制約と代わりの運用、直接編集の要件は個別の `AGENTS.md` に明記する。
- [ ] 自動 PR を停止するリポジトリでは、Dependabot の全エコシステムの
  `open-pull-requests-limit` を `0` にする。既存設定は初期化コマンドで上書きされないため個別に確認する。
- [ ] `configure-dependabot.py OWNER/REPO --write` を実行し、
  `security updates=disabled, alerts=enabled` の確認結果を得る。
- [ ] Settings → Advanced Security → Dependabot rules に、
  PR を作成する auto-triage rule があれば無効にする。
  組織が強制するルールは組織管理者へ確認する。
- [ ] Dependency graph が有効であることを確認する。
  API を利用できない場合は同じ画面で Dependabot alerts を有効、security updates を無効にする。
- [ ] メールで受ける場合は Watch → Custom → Security alerts を購読し、
  個人の通知設定で Dependabot alerts の Email を有効にする。
- [ ] 差分・必要な検証・CI を確認して、設定をコミットする。

auto-triage rules と通知設定は、このコマンドでは確認・変更できない項目として画面で確認する。
[PR 作成ルールと security updates の関係](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/auto-triage-dependabot-alerts)。

個人アカウントの Settings → Code security では、新規リポジトリ向けの既定値も設定できる。
Dependabot security updates の自動有効化を不要なら一度見直し、alerts は有効に保つ。
このアカウント全体の設定はコマンドの対象外とし、作成後は上のコマンドで実際の状態を確認する。
[アカウント単位の新規リポジトリ設定](https://docs.github.com/en/account-and-profile/how-tos/account-settings/managing-security-and-analysis-features#enabling-or-disabling-features-for-new-repositories)。

## Node / npm の CI

```bash
python3 ~/git/dotfiles/bin/init-project-config.py /path/to/app --node
python3 ~/git/dotfiles/bin/init-project-config.py /path/to/app --node --write
```

`--node` は、基本設定と Dependabot に加え、存在しない `mise.toml` と CI の雛形を追加する。
読み取り可能な `package.json` と `package-lock.json` が必要。
新しく CI を作る場合は `check` / `test:ci` / `build` の npm scripts と、
TypeScript を依存に持つ場合は `typecheck` も先に用意する。
必要な設定が足りなければ、基本設定も書き込まずに停止する。

既存の `mise.toml` / `.mise.toml` は維持する。Node の指定が含まれることを確認する。
新規テンプレートは Node 24 系を指定し、
[mise の公式 Action](https://github.com/jdx/mise-action)でプロジェクトの設定から導入する。
CI の共通雛形は `actions/checkout@v7`、`jdx/mise-action@v5`、`actions/cache@v6` を使う。
mise 本体は公開後24時間以上経過した安定リリースから選び、
`minimum_release_age: 24h` でこの待機時間を明示する。Node 等のツールの更新時期は別に管理する。
ツールの導入は1並列、npm はダウンロードキャッシュを利用する。
初期化コマンドは `mise.lock` を生成しない。lockfile を採用するときは
[導入手順](#miselock-の採用)に従い、mise Action の `install_args` を `--locked --jobs 1` に変更する。
依存導入後に lockfile が変わっていないことを確認してから、
`check` → 任意の `typecheck` → `test:ci` → `build` を順番に実行する。
CI の権限は `contents: read`、実行時間は20分までとし、同じ ref の古い検証は取り消す。

`.github/workflows/` に既存の YAML があれば、追加の検証 workflow は作成しない。
[`node-check.yml`](../src/project-presets/common/templates/node-check.yml)と比較し、既存 CI に必要な部分を統合する。
既定ブランチが `main` 以外の場合や、ビルド用の環境変数・生成処理が必要な場合も個別に調整する。
npm の lifecycle scripts は既定で無効にする。依存パッケージのビルドが必要なら、
対象を確認して `npm rebuild <package>` 等をプロジェクトの手順へ追加する。

このコマンド自体は依存導入や CI の実行を行わない。
各リポジトリで差分と検証結果を確認し、コミット・PR に含める。
公開ジョブと認証は各プロジェクトで管理する。
同じ検証処理を複数リポジトリで維持する負担が増えた段階で、再利用可能な workflow への切り出しを判断する。

## テンプレートの手動更新

自動更新 PR を使わず、公式の安定リリースと移行手順を確認して更新する。

1. Action の実行ランタイム・Runner の要件・入力や既定値の変更を確認する。
   アプリ用 Node のバージョンと、Action 自身の実行ランタイムは分けて確認する。
2. 共通雛形を更新し、YAML と入力の互換性、初期設定コマンドの既存テストを検証する。
   Node の系統を変更する場合は LTS とアプリの対応状況も確認する。
3. 導入済みリポジトリの workflow に必要な差分を取り込む。
   既存のキャッシュ設定、公開条件、認証、プロジェクト固有の処理を維持する。
4. リポジトリごとに検証してコミットし、PR の CI を確認してマージする。
   公開が起動する場合は本番確認まで追う。

初期化コマンドは既存ファイルを上書きせず、プリセットの横断チェックも CI 雛形を検査しない。
原本の更新だけでは導入済み workflow に反映されないため、コピー先を別途確認する。

## 共通プリセットの横断チェック

Next.js の共通プリセットを導入したリポジトリを、指定した順に確認する。

```bash
python3 ~/git/dotfiles/bin/check-project-presets.py /path/to/app-one /path/to/app-two
```

対象一覧を繰り返し使う場合は、端末ローカルの
`~/.config/dotfiles/projects.json` 等にパス文字列の JSON 配列を置く。
実際のプロジェクト名やパスを dotfiles の公開ファイルへ追加しない。

```json
[
  "~/git/app-one",
  "~/git/app-two"
]
```

```bash
python3 ~/git/dotfiles/bin/check-project-presets.py --projects-file ~/.config/dotfiles/projects.json
```

一覧内の相対パスは一覧ファイルのディレクトリが基準となる。
引数のパスと一覧ファイルは併用でき、同じディレクトリは1回だけ確認する。
自動探索、ネットワーク通信、同期、依存導入、Git 操作は行わない。
出力は対象の末尾のディレクトリ名と状態に限定し、絶対パスや設定内容は転送しない。

終了コードは全件同期済みが `0`、未同期ありが `1`、確認できない対象ありが `2`。
エラーがあっても残りの対象を確認し、エラーは未同期より優先して終了コードに反映する。
対象ごとに既存の `sync-project-presets.py --check` を呼び出すため、
検査範囲は共通プリセット2個と管理情報の一致まで。
初期テンプレートやルート設定の継承、npm scripts、アプリの動作は別途確認する。
個別のエラー詳細は対象に対して単体の `--check` を実行して確認する。

## Markdown の相対リンク検証

```bash
python3 ~/git/dotfiles/bin/check-markdown-links.py /path/to/repository
```

Git 管理されている `*.md` / `*.markdown` を作業ツリーの内容で確認する。
通常のインラインリンク、画像、1行の参照定義を使うリンクに対応し、
相対参照先のファイル・ディレクトリの存在を検査する。
日本語、URL エンコード、括弧を含む参照先も扱う。
参照先の欠落とリポジトリ外への相対リンクは問題として報告する。
対応する参照定義がない括弧の並びは、Markdown と同じく通常の文章として扱う。

fenced code、インラインコード、HTML コメント内の例は除外する。
外部 URL、絶対パス、見出しアンカーの存在、HTML / Wiki 独自のリンク構文は検証しない。
Markdown 全体の構文検証ではないため、インデントによるコードブロックや複数行の参照定義等を使う場合は、
その形式に対応する検証をプロジェクト側で選ぶ。
Markdown 自体がシンボリックリンクのものは読み込まず、除外件数を表示する。

通信や書き換えは行わない。問題は参照元の相対パスと行番号で報告し、
リンク先の値やクエリは出力しない。
終了コードは問題なしが `0`、リンクの問題ありが `1`、読み取り等の確認エラーありが `2`。
新しい文書は `git add` 後に対象へ含まれる。
dotfiles の Linux CI でもこのコマンドを実行する。
