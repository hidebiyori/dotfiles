# dotfiles

Mac、Chromebook の Linux 開発環境、Windows 11 / WSL2 で使う共通設定とセットアップ。
`src/` の設定をホームへリンクし、開発ツールとデスクトップアプリを導入する。

## Windows Codex でプロジェクトを追加するとき

**フォルダー選択に入力する場所は `\\wsl$\Ubuntu\home\<Linuxユーザー名>\git\<リポジトリ名>`。**

| 使う場所 | 同じプロジェクトを指すパスの例 |
| --- | --- |
| Windows の Codex / フォルダー選択 | `\\wsl$\Ubuntu\home\hidebiyori\git\dotfiles` |
| WSL のターミナル / Codex の作業ディレクトリ | `/home/hidebiyori/git/dotfiles`（`~/git/dotfiles`） |

**Add new project / `Ctrl+O` → `\\wsl$\` → ディストリビューション → `home` → Linux ユーザー → `git` → 対象フォルダー**。
`Ubuntu` は `wsl --list --quiet` の登録名、ユーザー名は WSL 内の `whoami` に合わせる。
新規リポジトリも WSL の `~/git/<名前>` に作成してから、同じ方法で追加する。
エージェントと統合ターミナルは WSL に設定する。[初回設定と確認](docs/windows-setup.md#codex-を-wsl-で使う設定)。

## セットアップ

既存の Bash・Git・SSH・Codex・mise・VS Code 設定は管理対象の内容で置き換える。
残したい設定を退避し、スクリプトを確認してから実行する。パッケージの導入・ダウンロードを伴う。

### Windows 11

通常の PowerShell から [Windows セットアップ手順](docs/windows-setup.md#初回に実行すること)を使う。
Windows アプリ、WSL2、WSL 内の clone とセットアップを順に準備する。
Git for Windows や Windows 側での手動 clone は事前準備に不要。
Steam は [`-IncludeSteam` を指定した場合だけ](docs/desktop-apps.md#steam任意)追加できる。
左 Win → Alt の設定は、[キー設定の専用コマンド](docs/windows-keyboard.md)で任意に適用できる。

### Mac / Chromebook / 準備済みの WSL2

Git を導入済みのターミナルで実行する。既存の clone があれば取得を省く。

```bash
mkdir -p "$HOME/git"
git clone https://github.com/hidebiyori/dotfiles.git "$HOME/git/dotfiles"
cd "$HOME/git/dotfiles"
less bin/install.sh
```

確認後、別の操作として実行する。

```bash
bash bin/install.sh
```

ターミナルを開き直すと設定が有効になる。設定の更新・再適用は `u`、共通環境の更新は `up`。
Linux のパッケージ管理は apt を使い、WSL では Windows 側の GUI アプリを利用する。

## 更新と再実行

| 操作 | 内容 |
| --- | --- |
| `u` | リポジトリの fast-forward 更新と設定の再適用。ツールの導入・更新は行わない |
| `up` | 設定を同期してから OS パッケージ・共通開発ツール・導入済みの管理対象アプリを更新 |
| `bash bin/install.sh` | 初期セットアップ。不足するツールとアプリを導入 |

- alias を使わない場合は `bash ~/git/dotfiles/bin/update.sh` / `bash ~/git/dotfiles/bin/upgrade.sh`。
  alias の変更はターミナルを開き直すか `r` で反映する。
- Python / Node / npm / Firebase CLI は [mise の共通設定](src/.config/mise/config.toml)で管理する。
  `up` はプロジェクトの依存関係を更新しない。詳細は[共通環境の更新](docs/development-tools.md#共通環境の更新)。
- 同じ設定リンク・コピー・導入済みアプリを再利用する。Downloads / MyDrive の実ディレクトリは維持する。
  Windows / Mac の対象アプリを明示更新する方法は[アプリ管理](docs/desktop-apps.md)を参照する。
- 通信・権限・検証の失敗時は停止する。原因を解消して再実行する。途中の反映は自動で巻き戻さない。
  Git の分岐や更新を妨げるローカル変更は自動で解消しない。
- 実行前にリポジトリの変更を確認する場合は `git fetch` と `git diff HEAD..origin/main` を使う。
  Flutter は[明示指定した場合](docs/development-tools.md#flutter任意)だけ導入・更新する。

## 目的別の手順

| 文書 | 内容 |
| --- | --- |
| [Windows / WSL2](docs/windows-setup.md) | 初回導入、オプション、Codex の WSL 設定、エラー時の扱い |
| [Windows のキー設定](docs/windows-keyboard.md) | 常駐なしの左 Win → Alt、元に戻す方法、Copilot / Fn の制約 |
| [開発ツール](docs/development-tools.md) | 手動リンクを使う設定、mise / CLI、FFmpeg、unzip、GitHub 初回認証、Flutter、スキル用 Python |
| [リポジトリ共通の保守](docs/repository-maintenance.md) | 新規リポジトリの確認項目、Dependabot の設定、CI の雛形、プリセット・文書リンク検証 |
| [文書の管理方針と雛形](docs/documentation.md) | 現在の仕様・手順を正本にする規約、README・構成・開発・運用の雛形 |
| [Next.js の共通設定](docs/project-presets.md) | Biome / TypeScript の原本・同期、初期テンプレート、プロジェクト固有設定との分担 |
| [Webアプリの共通対応候補](docs/web-app-candidates.md) | favicon、ダークモード、キャッシュ優先表示、通信失敗・更新からの復帰、スマートフォン・アクセシビリティの確認項目 |
| [デスクトップアプリ](docs/desktop-apps.md) | OS 別の導入・更新、手動の表示・入力設定、Chromebook の最大化起動 |
| [Codex の共通指示とスキル](docs/codex.md) | AGENTS.md の管理場所・同期、共通とプロジェクト固有の分担 |
| [会話から得た共通知見](docs/learnings.md) | 知見の採用・公開前確認、再利用する判断基準と手順へのリンク |
| [Firebase 公開認証](docs/firebase-deploy-auth.md) | 既存認証の確認、ADC、GitHub OIDC / WIF |
| [Chrome / Playwright](docs/playwright-extension.md) | Chromebook で必要時だけ接続する手順 |

共通の行動規則は [`src/.codex/AGENTS.md`](src/.codex/AGENTS.md)、
このリポジトリの変更・検証規則は [`AGENTS.md`](AGENTS.md) で管理する。
公開ファイルには汎用手順を置き、プロジェクト固有の情報は各プロジェクト内で管理する。
