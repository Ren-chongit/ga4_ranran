import os
import json
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest
import google.auth
from google.oauth2 import service_account
import google.generativeai as genai

def main():
    # GitHub Secretsから環境変数を取得
    client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
    private_key = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")
    property_id = os.getenv("GA_PROPERTY_ID")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    # サービスアカウント情報を構成
    service_account_info = {
        "type": "service_account",
        "project_id": "dummy-project",
        "private_key_id": "dummy-key-id",
        "private_key": private_key,
        "client_email": client_email,
        "client_id": "dummy-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": ""
    }

    # 認証クレデンシャル作成
    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    client = BetaAnalyticsDataClient(credentials=credentials)

    # GA4データ取得
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date"), Dimension(name="pageTitle")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
    )
    response = client.run_report(request)

    # データ整形
    rows = [
        {
            "date": row.dimension_values[0].value,
            "pageTitle": row.dimension_values[1].value,
            "views": row.metric_values[0].value,
        }
        for row in response.rows
    ]
    report_text = json.dumps(rows, ensure_ascii=False, indent=2)

    # Geminiで要約
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    summary = model.generate_content(f"以下のGA4データを簡潔に要約してください：\n{report_text}")

    print("📊 GA4要約結果:")
    print(summary.text)

if __name__ == "__main__":
    main()
