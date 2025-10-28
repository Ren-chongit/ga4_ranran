# 📊 Google Analytics 自動分析レポート（GA4 × Gemini × GitHub Actions）

このリポジトリは **Google Analytics 4（GA4）のデータを自動取得し、Gemini API で要約して GitHub Issue にレポートを自動投稿するワークフロー**です。  
毎週月曜日 9:15（日本時間）に実行され、アクセスの増減や改善ポイントを要約してレポート化します。
※現在は検証中のため、不定期実行

---

## 🚀 機能概要
- GA4 Data API からアクセスデータを自動取得  
- Gemini API により自然言語で要約  
- 結果を GitHub Issue に自動投稿  
- 毎日自動実行（cron スケジュール）  
- 手動実行（「Run workflow」）も可能  

---

## 🧩 必要なアカウント・設定
### 1️⃣ Google Cloud Console 側設定
1. Google Cloud Console にアクセス  
   https://console.cloud.google.com/
2. 「Analytics Data API」を有効化  
3. サービスアカウントを作成  
4. JSON キーを発行（`client_email` と `private_key` を利用）
5. GA4 の「プロパティ設定 → アクセス管理」で  
   サービスアカウントの `client_email` に「分析者（Analyst）」権限を付与  

---

### 2️⃣ Gemini API キーの取得
1. [Google AI Studio](https://ai.google.dev/) にアクセス  
2. 「API キー」メニュー → 「新しいキーを作成」  
3. 作成時に Cloud Project を選択（または作成）  
4. 発行されたキーをコピー  

---

### 3️⃣ GitHub Secrets 登録
リポジトリの  
**Settings → Secrets and variables → Actions → New repository secret**  
から以下を登録します。

| Name | Value（内容） |
|------|----------------|
| `GOOGLE_CLIENT_EMAIL` | サービスアカウントの client_email |
| `GOOGLE_PRIVATE_KEY`  | JSON からコピーした private_key（改行付き PEM 形式） |
| `GA_PROPERTY_ID`      | GA4 プロパティID（数字のみ） |
| `GEMINI_API_KEY`      | Google AI Studio で発行した APIキー |

> ⚠️ `GOOGLE_PRIVATE_KEY` は `\n` を削除し、実際の改行で貼り付けてください。  
> 「-----BEGIN PRIVATE KEY-----」〜「-----END PRIVATE KEY-----」の間は複数行で保存。

---

## ⚙️ ワークフローの構成
`.github/workflows/ga4_report.yml`

```yaml
name: Google Analytics 自動分析

on:
  schedule:
    - cron: '0 0 * * *'  # 毎日 日本時間9:00
  workflow_dispatch:

permissions:
  contents: read
  issues: write

jobs:
  summarize-ga4:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Run Gemini GA4 Summary via MCP (JS server)
        id: ga4
        uses: google-gemini/gemini-cli-action@main
        env:
          GOOGLE_CLIENT_EMAIL: ${{ secrets.GOOGLE_CLIENT_EMAIL }}
          GOOGLE_PRIVATE_KEY: ${{ secrets.GOOGLE_PRIVATE_KEY }}
          GA_PROPERTY_ID:     ${{ secrets.GA_PROPERTY_ID }}
        with:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          settings_json: |
            {
              "mcpServers": {
                "google-analytics": {
                  "command": "npx",
                  "args": ["-y", "mcp-server-google-analytics"],
                  "env": {
                    "GOOGLE_CLIENT_EMAIL": "$GOOGLE_CLIENT_EMAIL",
                    "GOOGLE_PRIVATE_KEY": "$GOOGLE_PRIVATE_KEY",
                    "GA_PROPERTY_ID": "$GA_PROPERTY_ID"
                  }
                }
              },
              "coreTools": ["mcp__google-analytics__run_report"]
            }
          prompt: |
            あなたはWebサイトのアクセス解析アシスタントです。
            昨日（プロパティのタイムゾーン）のアクセスデータを分析し、
            主要なトラフィックソース、人気ページ、コンバージョンの変化に注目して、
            改善提案を3点以内で出してください。
            出力は日本語の箇条書きでお願いします。

      - name: Create GitHub Issue with Summary
        uses: actions/github-script@v7
        with:
          github-token: ${{ github.token }}
          script: |
            const today = new Date().toISOString().split('T')[0];
            const outs = ${{ toJSON(steps.ga4.outputs) }};
            const pick = (keys) => { for (const k of keys){ const v=(outs?.[k]||'').trim(); if(v) return v; } return ''; };
            const body = pick(['gemini_result','gemini_response','summary','output','text','content'])
              || 'GA4集計結果が取得できませんでした。';
            const { data: issue } = await github.rest.issues.create({
              owner: context.repo.owner,
              repo:  context.repo.repo,
              title: `GA4サマリー (${today})`,
              body
            });
            core.info(`✅ Issue #${issue.number} を作成しました`);
```
---

## 🧠 実行と確認
GitHub 上部メニュー → 「Actions」

ワークフロー Google Analytics 自動分析 を選択

「Run workflow」ボタンを押して手動実行

成功すると「Issues」に自動レポートが生成されます ✅

---

## 💡 出力イメージ
昨日の主要流入経路と増減傾向

滞在時間・直帰率の改善ポイント

コンバージョン増加につながる提案（例：特定ページの導線改善 など）

🔧 トラブルシューティング
エラー内容	原因・対処
DECODER routines::unsupported	秘密鍵の改行が正しくない。PEM形式で再登録。
PERMISSION_DENIED	GA4側のサービスアカウント権限が不足。分析者(Analyst)を付与。
レポート途中で停止	プロンプトが長すぎる。3～5行出力に変更。
何も出力されない	Secrets名の誤字、またはプロパティID不一致。

---

## 参考情報

- 一度のインプット・アウトプット（TPM）で、500,000～600,000TPMぐらい使う
- Gemini 2.5 Proのリミットは125,000TPM
- Gemini 2.5 Flashのリミットは250,000TPM
- Gemini 2.0 Flashのリミットは1,000,000TPM
そんな訳で、Gemini 2.0 Flashを使ってます。上記は全て無料枠の話。
公式 https://ai.google.dev/gemini-api/docs/rate-limits?hl=ja に記載あり

## 関連app
- https://github.com/Ren-chongit/issue_info
- 上記にて新規Issue検知後Teams通知app作成済み（private repo / 運用はローカルPCにて）
