# リポジトリ共通の設定と保守

言語やフレームワークに依存しない初期設定は、
[`src/project-presets/common/templates/`](../src/project-presets/common/templates/) で管理する。
各リポジトリへコピーして Git 管理し、CI と別の端末でも clone だけで使える状態にする。
セットアップや dotfiles の更新から、各プロジェクトへ自動反映しない。

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

Node / npm のアプリでは次の `--node` を使う。npm と GitHub Actions の両方を更新対象にする。
Dependabot は月曜に週次でバージョン更新を確認し、minor / patch をまとめる。
major は別 PR とし、同時に開く更新 PR は各エコシステムで3件までにする。
セキュリティ更新の動作は週次のバージョン更新とは別に扱う。
[Dependabot の設定](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)。

`.github/dependabot.yml` / `.github/dependabot.yaml` が既にあれば維持する。
対象ディレクトリがルート以外の場合や、他のパッケージ管理方式を使う場合は、
既存設定と雛形を比較して対象・更新頻度・例外を各リポジトリで調整する。
dotfiles 自身には GitHub Actions 用の設定を導入している。

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
ツールの導入は1並列、npm はダウンロードキャッシュを利用する。
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
参照先の欠落、未定義の参照ラベル、リポジトリ外への相対リンクは問題として報告する。

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
