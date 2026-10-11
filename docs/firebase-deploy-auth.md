# Firebase 公開認証を既存の設定から調べる

GitHub Actions の Firebase Hosting 公開を設定する際の共通手順。
Secret が見つからない場合も、認証に使える設定と権限を確認してから、
不足している操作を判断する。認証情報の値は文書・チャット・ログへ残さない。

## 既存設定を確認する

1. 対象と別プロジェクトの `.github/workflows/`、`firebase.json`、
   `.firebaserc`、デプロイスクリプトを読む。対象の Firebase プロジェクトと
   Hosting target を確認し、別サイトの認証をそのまま流用しない。
2. 過去チャットや記録から、サービスアカウント鍵、GitHub Secret、
   Workload Identity Federation (WIF) のどれを設定したかを調べる。
   Secret の値を取得・表示する必要はない。
3. 導入済み CLI と認証設定の有無を調べる。設定全体や環境変数の一括表示はしない。

```bash
command -v gcloud
command -v gh
gh secret list --repo OWNER/REPO
test -f "$HOME/.config/gcloud/application_default_credentials.json"
```

既存 workflow が Secret を使っていることと、現在のアカウントがその Secret を
新しいリポジトリへ設定できることは別に確認する。GitHub は既存 Secret の本文を
読み戻せない。ローカル認証がある場合は、新しい鍵を探したり作ったりする前に使える権限を調べる。

## gcloud の通常アカウントがない場合の ADC

gcloud CLI のログインと Application Default Credentials (ADC) は別の設定。
通常の gcloud コマンドにアクティブアカウントがなくても、既存 ADC を
コマンド単位で指定すると利用できる場合がある。`HOME` 等のシステム変数は書き換えない。

```bash
CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE="$HOME/.config/gcloud/application_default_credentials.json" \
  gcloud projects describe PROJECT_ID --format='value(projectId)'
```

これが通れば、同じ指定で必要な管理権限を読み取り確認する。
プロジェクトの読み取り成功だけでは、API 有効化・IAM 変更・公開権限までは証明できない。
失敗時は認証失敗と権限不足を区別し、実行結果に応じて必要なログインや権限を伝える。
ADC の JSON、refresh token、access token、秘密鍵は表示しない。

2026-10-12 の調査では、通常の gcloud アクティブアカウントがない環境で、
既存 ADC の override によるプロジェクト読み取りと IAM・Service Account Credentials・
Security Token Service API の有効化を確認した。この観測は、別端末や別プロジェクトの
権限を保証するものではない。

## GitHub Actions からの公開

新しい設定は Google WIF と GitHub OIDC を優先し、長期サービスアカウント鍵を作らない。
既存の設定がある場合は、pool・provider・サービスアカウントのメタデータと IAM を確認し、
同じ用途の設定を重複作成しない。

- GitHub OIDC issuer は `https://token.actions.githubusercontent.com/`。
- provider の mapping は `google.subject=assertion.sub` に加え、制限に使う
  `repository_id`、`repository_owner_id`、`ref`、`event_name` を対応させる。
- provider の condition をリポジトリと所有者の数値 ID、
  `refs/heads/main`、`push` に限定する。数値 ID は GitHub API のメタデータで確認する。
  リポジトリ名だけを制限に使うと、削除後に名前を再利用される可能性がある。
- 公開専用サービスアカウントを使い、該当リポジトリの federated principal にだけ
  `roles/iam.workloadIdentityUser` を付与する。principalSet は
  `attribute.repository_id/REPOSITORY_NUMERIC_ID` に限定する。
  Firebase Hosting の公開用ロールは `roles/firebasehosting.admin`。
  Firebase CLI には追加で `roles/serviceusage.apiKeysViewer` が必要。
  対象 CLI・サイト・Firebase プロジェクトの既存 IAM を確認し、Owner 権限で代用しない。
- workflow は検証が成功した後、`main` の `push` だけで公開する。
  PR の検証 job に公開認証は与えない。認証 job の `permissions` には
  `contents: read` と `id-token: write` を設定する。
- `actions/checkout` の後に `google-github-actions/auth` を実行し、
  `workload_identity_provider` と `service_account` を指定して ADC を作る。
  action の現行仕様と参照するコミットは公式リポジトリで確認する。
- provider resource name とサービスアカウント email は秘密鍵ではないため、
  対象リポジトリの設定として管理できる。生成された一時 ADC ファイルは Git 管理に含めず、
  artifact にも保存しない。

provider condition のテンプレート（数値 ID を確認して置き換える）:

```text
assertion.repository_id=='REPOSITORY_NUMERIC_ID' && assertion.repository_owner_id=='OWNER_NUMERIC_ID' && assertion.ref=='refs/heads/main' && assertion.event_name=='push'
```

2026-10-12 の調査では、既存 ADC で専用サービスアカウントと WIF pool/provider を作成し、
上記の制限・ロールを設定できた。サービスアカウント鍵は作成せず、GitHub Secret も不要だった。
これは設定作成の確認であり、Actions での認証とデプロイは実際の実行結果で別に検証する。

共有 Firebase プロジェクトでは、例えば `firebase deploy --only hosting:TARGET --project PROJECT_ID`
のように Hosting target を絞る。リポジトリに公開用スクリプトがあれば、その検証済みコマンドを使う。
別サイトの公開や新しい認証設定の作成は、依頼の範囲と現在の権限を確認してから行う。

設定完了後は、GitHub Actions での OIDC 認証・公開結果と、代表 URL の HTTP 応答、
公開したファイルの内容またはハッシュを確認する。ローカルの手動公開成功だけで
GitHub Actions の公開成功と扱わない。

参考: [Google のデプロイパイプライン向け WIF 手順](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)、
[Google GitHub Actions auth](https://github.com/google-github-actions/auth)、
[Firebase Hosting の IAM ロール](https://firebase.google.com/docs/projects/iam/roles-predefined-product#hosting)。
