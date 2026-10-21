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
