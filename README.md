# 📊 Google Analytics 自動分析レポート
（GA4 × Gemini × GitHub Actions）

このリポジトリは **Google Analytics 4（GA4）のデータを自動取得し、Gemini API で要約して GitHub Issue にレポートを自動投稿するワークフロー**です。  
毎日 9:15（日本時間）に実行され、アクセスの増減や改善ポイントを要約してレポート化します。

※Teamsでのレポート作成報告は毎週月曜日のみにしてます。毎日通知は面倒なので。

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
name: Gemini GA4 Summary
on:
  workflow_dispatch: {}
  schedule:
    - cron: '0 0 * * *'  # 毎日月曜 日本時間09:00（UTC 00:00）　分・時・日・月・曜日
permissions:
  contents: read
  issues: write
jobs:
  summarize-ga4:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      # MCPサーバーウォームアップ
      - name: Pre-install MCP server
        run: |
          npx -y mcp-server-google-analytics --version || echo "MCP server ready"
        continue-on-error: true
      
      - name: Run Gemini GA4 Summary via MCP (JS server)
        id: ga4
        uses: google-gemini/gemini-cli-action@main
        env:
          GOOGLE_CLIENT_EMAIL: ${{ secrets.GOOGLE_CLIENT_EMAIL }}
          GOOGLE_PRIVATE_KEY: ${{ secrets.GOOGLE_PRIVATE_KEY }}
          GA_PROPERTY_ID: ${{ secrets.GA_PROPERTY_ID }}
          GEMINI_MODEL: gemini-2.0-flash
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
            あなたはプロのGA4データアナリストです。
            
            【重要】必ず mcp__google-analytics__run_report ツールを使用してGA4データを取得し、分析結果のみをまとめてください。
            
            【絶対禁止】
            - 「了解しました」「まず」「次に」などの前置きや進行説明は一切書かない
            - データ取得プロセスの説明は書かない。Issueの開始は”yyyy年mm月dd日からyyyy年mm月dd日アクセス解析”で始まり、続けて”## トラフィック傾向”と続く
            - エラーの説明や試行錯誤の過程は書かない
            - 「改善する」「強化する」などの抽象的な表現は使わず、必ず具体的なアクションを記載
            - 推測で数値を埋めない。データが取得できない場合は正直に「データ取得失敗」と記載
            
            【必須事項】
            - 全体のコンバージョン率（予約フォーム開始→完了の%）を必ず以下の手順で計算：
              1. 予約完了数を確認
              2. 予約フォーム開始数を確認  
              3. CVR = (予約完了数 ÷ 予約フォーム開始数) × 100
              4. 計算式も明記（例：「257件 ÷ 5,628件 = 4.57%」）
            - 前週データも取得し、増減率を記載（基準期間を明示：例「今週10/22-28 vs 前週10/15-21」）
            - 改善提案には必ず具体的なアクション（例：「検索ボタンを緑→オレンジに変更」「入力項目を10個→7個に削減」）を含める
            - 各施策の期待効果を定量的に記載（例：「コンバージョン率+0.5%改善見込み」）
            - 異常値（離脱率95%以上など）を検出した場合、システム障害の可能性を指摘
            
            【データ取得手順】
            1. 今週データ（昨日から過去7日間、タイムゾーン: Asia/Tokyo）
               a. トラフィックソース: dimensions=["sessionSource", "sessionMedium"], metrics=["sessions"], 上位10件降順
               b. 人気ページ: dimensions=["pagePath"], metrics=["screenPageViews"], 上位10件降順
               c. イベント: dimensions=["eventName"], metrics=["eventCount"], 全イベント取得
            
            2. 前週データ（昨日から過去7日間から、さらに7日間のデータを取得）
               - 同様のデータを取得し、前週比を算出
               - 分析期間を明記（例：今週10/22-28 vs 前週10/15-21）
            
            【データ品質チェック（必須）】
            データ取得後、以下を必ず確認：
            - 上位3ソースの合計が全セッション数の30%以上を占めているか
            - 前週比が妥当な範囲か（±100%を超える変動は要確認）
            - 疑わしいデータがある場合、【データ検証必要】マークをつけて報告
            
            【重要な注意事項】
            - dimensionFilterを使用する場合は慎重に。エラーが出たらフィルタなしで全データ取得し、後から絞り込む
            - 予約・購入関連イベントはイベント名から推測して特定
            - データが取得できない、または明らかに異常な場合は推測で埋めず、正直に報告
            
            【出力形式】いきなり「## トラフィック傾向」から始める。前置きは一切不要。
            
            ## トラフィック傾向
            - **分析期間**: 今週YYYY/MM/DD-MM/DD vs 前週YYYY/MM/DD-MM/DD
            - **上位3ソース**:
              * ソース1の名前 XXXセッション [前週比±XX%]
              * ソース2の名前 XXXセッション [前週比±XX%]
              * ソース3の名前 XXXセッション [前週比±XX%]
            - **考察**: 前週比や特徴的な傾向
            - **改善提案**: 
              * 具体的アクション1（期待効果：〇〇）
              * 具体的アクション2（期待効果：〇〇）
            - **取得時のエラー**: なし / あり（内容を簡潔に）
            
            ## 人気ページ
            - **上位5ページ**:
              * ページ1のパス XXX PV [前週比±XX%]
              * ページ2のパス XXX PV [前週比±XX%]
              * ページ3のパス XXX PV [前週比±XX%]
              * ページ4のパス XXX PV [前週比±XX%]
              * ページ5のパス XXX PV [前週比±XX%]
            - ※前週比±50%以上は【重要】、±500%以上は【緊急】マークをつける
            - **考察**: ユーザー行動の特徴
            - **改善提案**: 
              * 具体的アクション1（期待効果：〇〇）
              * 具体的アクション2（期待効果：〇〇）
            - **取得時のエラー**: なし / あり（内容を簡潔に）
            
            ## コンバージョンと考察
            - **全体コンバージョン率**: 計算式を明記（例：257件 ÷ 5,628件 = 4.57% [前週比+1.2%]）
            - **主要イベント件数**: 各ステップの具体的な数値と前週比
            - **ファネル分析**: 各ステップの離脱率（95%以上は「【システム障害の可能性】」と指摘）
            - **改善提案**: 
              * 具体的アクション1（期待効果：CVR+〇%）
              * 具体的アクション2（期待効果：CVR+〇%）
            - **取得時のエラー**: なし / あり（内容を簡潔に）
            
            ## 週次パフォーマンスサマリー
            - **総合評価**: 良好/要注意/危機的（判断基準を明記）
            - **特記事項**: 今週の特徴的な変化トップ3
            - **推定原因**: パフォーマンス変動の考えられる要因
            
            ## 今後の施策（優先度順、インパクト×実行容易性で評価）
            1. 最優先施策（理由：〇〇、期待効果：〇〇）
            2. 重要施策（理由：〇〇、期待効果：〇〇）
            3. 継続施策（理由：〇〇、期待効果：〇〇）
            
            ※【緊急】マークのある項目は必ず優先施策に含めること
            ※全ての数値はデータに基づいて記載。推測する場合は「推定」と明記。
            ※データが明らかに異常な場合は、推測で埋めずに異常を報告すること。

            最後に改めて、【重要】必ず mcp__google-analytics__run_report ツールを使用すること。
            各項目の数値は全て mcp__google-analytics__run_report ツールから取得したデータに基づいて記載してください。
      
      - name: Create GitHub Issue with Summary
        uses: actions/github-script@v7
        with:
          github-token: ${{ github.token }} 
          script: |
            const today = new Date();
            // 日本時間を考慮（UTCから9時間進める）
            const jstOffset = 9 * 60 * 60 * 1000;
            const jstToday = new Date(today.getTime() + jstOffset);
            
            const yesterday = new Date(jstToday);
            yesterday.setDate(yesterday.getDate() - 1);
            
            const sevenDaysAgo = new Date(jstToday);
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            
            // MM-DD形式に整形
            const fmt = (d) => d.toISOString().split('T')[0].slice(5); // "2025-10-22" → "10-22"
            const todayFull = jstToday.toISOString().split('T')[0]; // 実行日は西暦あり
            const title = `(${todayFull}) らんらんアクセス解析｜期間：${fmt(sevenDaysAgo)}〜${fmt(yesterday)}`;
            
            const outs = ${{ toJSON(steps.ga4.outputs) }};
            const pick = (keys) => { 
              for (const k of keys){ 
                const v=(outs?.[k]||'').trim(); 
                if(v) return v; 
              } 
              return ''; 
            };
            const body = pick(['gemini_result','gemini_response','summary','output','text','content'])
              || 'GA4集計結果が取得できませんでした。';
            
            const { data: issue } = await github.rest.issues.create({
              owner: context.repo.owner,
              repo:  context.repo.repo,
              title,
              body
            });
            core.info(`✅ Issue #${issue.number} を作成しました`);
```

さらに詳しい解説は Note(private)に記載してます。
https://www.notion.so/GA4_MCP-GitHub-299001aed37780b3b6c7ef9e6e817e48

