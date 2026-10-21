# Next.js プロジェクトの共通設定

共通の Biome / TypeScript 設定を [`src/project-presets/nextjs/`](../src/project-presets/nextjs/) で管理し、
各プロジェクトの `config/presets/nextjs/` へコピーして Git 管理する。
プロジェクト直下の設定が `extends` で共通プリセットを読み込み、固有の設定を上書きする。
CI と他の端末では、プロジェクトの clone だけで設定を利用できる。
dotfiles の更新や一括セットアップでは、プロジェクトへ自動反映しない。

## 管理方式の選び方

| 方式 | 向く用途・更新の扱い |
| --- | --- |
| 原本からコピーし、`extends` で継承する | 少数の独立したリポジトリ向け。同期コマンドで差分を作り、プロジェクトごとに検証・コミットする。本手順で採用 |
| バージョン付きの共有 npm パッケージ | 利用先が増え、設定を依存更新 PR で配布したい場合。公開・互換性・配布先の管理が必要 |
| リポジトリテンプレート | 新規作成時のディレクトリ構成や初期ファイルを揃える。作成後の設定更新は別途管理する |
| ホームの設定や別リポジトリへのリンク | 利用する端末に依存するため、プロジェクトの共有設定には使わない |
| モノレポのルート設定 | アプリやライブラリを一緒に開発・リリースする場合。設定統一だけを目的に既存リポジトリを統合しない |

Biome は相対パスと npm パッケージの設定を `extends` で読み込める。
将来 npm 配布へ移す場合も、プロジェクト直下の例外設定を保ち、共通プリセットの参照先を変更できる。
パッケージと Biome 本体は互換性のあるバージョンを明示し、lockfile とともに更新する。
[Biome の共有設定](https://biomejs.dev/configuration/big-projects/)。

## ディレクトリとコマンドの規約

同じ役割のファイルは次の場所へ置く。利用しないディレクトリを空で作成する必要はない。

```text
src/
  app/ または pages/    Next.js のルーティング
  components/          複数の画面で使う UI
  lib/                 データ処理・外部サービス等のロジック
tests/                 自動テスト。必要に応じて components/、lib/ 等に分ける
scripts/               ビルド・検証・公開・保守の実行スクリプト
docs/                  開発・操作・公開の詳細手順
config/
  presets/nextjs/      コピーした共通プリセットと管理情報
public/                静的配信するファイル
mise.toml              プロジェクトのランタイム・ツール指定
biome.json             共通設定の継承と対象・例外
tsconfig.json          TypeScript を使う場合の継承とパス設定
```

新規アプリは `src/app/` を基本にする。既存の Pages Router は `src/pages/` を使い、
ルーター移行は機能・URL・公開方式の変更を含む別の対応とする。
共通 UI がまだない場合は `src/components/` を作るためだけにコンポーネントを分割しない。
本文データや過去の資産等は用途に応じて別ディレクトリを利用できる。
[Next.js のディレクトリ規約](https://nextjs.org/docs/app/getting-started/project-structure)。

テストは `tests/` に揃える。`test/` や `__tests__/` から移す場合は、npm scripts、
CI、Biome の対象・例外、TypeScript の include、テストランナーの検出設定、文書の参照を更新する。
Jest は `__tests__/` のディレクトリ名による自動検出もあるため、テスト数とスナップショットの対応を確認する。
`scripts/` には、出力の監査など単独で実行する検証コマンドも置ける。

ローカルの `npm test` は用途に合わせて watch を利用できるが、CI の入口は `npm run test:ci` とし、
watch なしで終了するコマンドを登録する。公開前の型検査・ビルド等は引き続き個別のコマンドで実行する。
mise 設定の名前は `mise.toml` を基本にし、既存の `.mise.toml` は内容を保って移す。
既存のバージョン指定や Java 等の追加ツールは維持する。

## 共通化するもの・各プロジェクトで決めるもの

| 対象 | 共通の既定値・運用 | プロジェクトに残すもの |
| --- | --- | --- |
| Biome | スペース2個、80桁、二重引用符、セミコロン、推奨ルールと React / Next ドメイン | 対象ファイル、生成物の除外、個別のルール例外 |
| TypeScript | `strict`、`noEmit`、bundler 用の解決、JSX、Next プラグイン | `paths`、`include` / `exclude`、`allowJs`、対象環境による `target` の変更 |
| EditorConfig / Git 属性 | [共通の初期テンプレート](repository-maintenance.md)。UTF-8、LF、最終改行、スペース2個と拡張子別の例外 | 導入後の `.editorconfig` / `.gitattributes`。変更は各リポジトリで管理 |
| Node / パッケージ管理 | Node はプロジェクトの mise 設定、開発ツールは `package.json` と lockfile。CI もプロジェクトの指定に合わせる | Node の具体的な版、必要なツール。パッケージ管理ツールの移行は別途判断 |
| npm scripts | `dev` / `build` / `check` / `format` / `typecheck` / `test:ci` などの入口を揃える | ビルド前後の処理、実際のテストコマンド。JS のみなら `typecheck` は不要 |
| テスト | CI は watch なしで終了するコマンドにする | Node test runner / Jest / Vitest、テスト対象、ブラウザ検証の要否 |
| GitHub Actions | [Node CI の雛形](repository-maintenance.md#node--npm-の-ci)。品質チェックの順序とキャッシュ方針 | 公開ジョブ、認証、権限、成果物、プロジェクト固有の検証 |
| 依存更新 | [Dependabot の雛形](repository-maintenance.md#依存更新)。週次更新と minor / patch のグループ化 | 更新時期、互換性の制約、メジャー更新の判断 |
| Next.js / CSS / UI | 採用する構成の方針や新規作成用テンプレート | `output`、画像、ヘッダー、公開先、Tailwind 等の採用、テーマや画面設計 |
| 環境変数・作業規則 | `.env.example` は設定名だけを記載。端末共通の規則は dotfiles | 値、秘密情報、サービス名、プロジェクトの `AGENTS.md` |

Biome を使うプロジェクトには、必要なルールが足りる限り ESLint / Prettier を追加しない。
Biome の lint は TypeScript の型検査の代わりにはならない。
Next.js 16 以降の `next build` は lint を実行しないため、CI で `check` も明示実行する。
[Next.js の lint 設定](https://nextjs.org/docs/app/getting-started/installation#set-up-linting)。

## 初回導入

導入済みの Python 3 を使う。同期コマンドはネットワーク通信、依存導入、Git 操作を行わない。
新規アプリ自体は通常の Next.js の作成手順で用意する。
`create-next-app` の `--biome` も利用できるが、生成された設定と共通プリセットの統合は次の手順で行う。
[create-next-app](https://nextjs.org/docs/app/api-reference/cli/create-next-app)。

対象ディレクトリは実際のプロジェクトへ置き換える。

```bash
python3 ~/git/dotfiles/bin/sync-project-presets.py /path/to/app --init
python3 ~/git/dotfiles/bin/sync-project-presets.py /path/to/app --init --write
```

通常実行は変更予定の表示だけ。`--write` は共通プリセット2個とハッシュを記録する `manifest.json` を更新する。
`--init` は、存在しない `biome.json`、`.editorconfig`、`.gitattributes`、`mise.toml` も作成する。
`package.json` の dependencies / devDependencies に TypeScript があれば、存在しない `tsconfig.json` も作成する。
初期 TypeScript テンプレートは `src/` と `@/*` を想定しているため、構成に合わせて `paths` を調整する。
Windows ネイティブで Python が導入済みの場合は `python3` の代わりに `py -3` を使える。
初期 mise 設定は Node 24 系を指定する。既存の `mise.toml` / `.mise.toml` は維持し、
新しいファイルとの二重配置は行わない。ツールの導入や更新はこのコマンドでは行わない。

既存のルート設定は維持する。`biome.jsonc` がある場合も `biome.json` を新規作成しない。
既存の設定に、次の継承指定を追加する。
既に `extends` がある場合は、既存の継承先との優先順位・互換性を確認して統合する。

`biome.json` / `biome.jsonc`:

```json
{
  "$schema": "./node_modules/@biomejs/biome/configuration_schema.json",
  "extends": ["./config/presets/nextjs/biome-next.json"]
}
```

共通プリセットと同じ `formatter`、`javascript.formatter`、推奨ルール等はルートから取り除き、
`files` と `overrides`、意図した例外だけを残す。ルートに同じ設定を残すと、後の共通設定の更新を上書きしてしまう。
既存のルール無効化をすべて共通プリセットへ移さず、理由と対象範囲を各プロジェクトで確認する。
プリセットは `linter.rules.preset` に対応する Biome 2.5 系を前提とする。
Biome 本体は各プロジェクトの開発依存でバージョンを固定し、更新時にプリセットとの互換性を検証する。

`tsconfig.json`:

```json
{
  "extends": "./config/presets/nextjs/tsconfig-next.json",
  "compilerOptions": {
    "allowJs": false,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts", ".next/dev/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

既存の `paths`、`include`、`exclude`、`allowJs` は維持して統合する。
共有 TypeScript 設定内の相対パスはその設定ファイルがある場所を基準に解釈されるため、
プロジェクトのディレクトリ構成に依存する項目はルートに置く。
[TypeScript の extends](https://www.typescriptlang.org/tsconfig/extends.html)。

`.editorconfig` / `.gitattributes` が既にある場合はテンプレートと比較して必要な内容だけ統合する。
初期テンプレートは導入後の更新対象に含めない。
管理先の途中にリンクがある場合や、コピー済みの共通プリセットが独自に編集されている場合、同期は停止する。
リンクは利用者の手動配置を維持し、別の場所を使う場合は設定の配置を個別に判断する。

## 更新・確認

1. dotfiles の原本を更新し、dotfiles 自身のテストと差分確認を行う。
2. 対象プロジェクトごとに次を実行し、更新されるファイルを確認する。

   ```bash
   python3 ~/git/dotfiles/bin/sync-project-presets.py /path/to/app
   python3 ~/git/dotfiles/bin/sync-project-presets.py /path/to/app --write
   python3 ~/git/dotfiles/bin/sync-project-presets.py /path/to/app --check
   ```

3. プロジェクトで差分を確認し、導入済み依存で `check`、必要な型検査・テスト・ビルドを実行する。
   TypeScript のプロジェクトでは `next typegen && tsc --noEmit` 等、そのプロジェクトに適したコマンドを使う。
   ブラウザ検証は画面・操作・実行時エラーの確認が必要な変更で行う。
4. 共通プリセットのコピー、`manifest.json`、ルート設定の変更を同じプロジェクトのコミットに含める。
   CI の成功を確認し、そのプロジェクトの公開手順に従う。

`--check` は、手元の dotfiles の原本とコピーの一致を確認する。終了コードは一致が `0`、未同期が `1`、
独自変更・不正なファイル等が `2`。共通設定をルートから継承できているかの検査や、最新版の取得は行わない。
プロジェクトの通常 CI では、コミット済みの設定で品質チェックを実行し、dotfiles の取得は不要。
共通設定の変更が必要なら原本を変更し、プロジェクト固有の変更はルート設定へ置く。
取り消しは対象プロジェクトの Git 差分・コミットを使って行う。
複数リポジトリの未同期をまとめて確認する場合は、
[共通プリセットの横断チェック](repository-maintenance.md#共通プリセットの横断チェック)を使う。

## dotfiles の検証

```bash
python3 -B -m unittest discover -s tests -v
git diff --check
```

同期テストは一時ディレクトリだけを使い、プレビュー、更新、独自変更の上書き拒否、
既存 JSONC 設定とリンクの維持を確認する。実際の Next.js アプリの検証は各プロジェクトで行う。
依存関係の再インストールや、一括セットアップによる検証は行わない。
