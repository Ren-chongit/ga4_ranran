import os
import json
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest
import google.generativeai as genai

def main():
    # Secretsから取得
    service_account_json = os.getenv("ga4_ranran_secret") or os.getenv("GA4_SERVICE_ACCOUNT_JSON")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    property_id = os.getenv("GA4_PROPERTY_ID", "YOUR_GA4_PROPERTY_ID")  # 必要に応じてSecrets化

    # JSONをロード
    creds = json.loads(service_account_json)
    client = BetaAnalyticsDataClient.from_service_account_info(creds)

    # GA4データ取得
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date"), Dimension(name="pageTitle")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
    )
    response = client.run_report(request)

    # 結果を整形
    rows = []
    for row in response.rows:
        rows.append({
            "date": row.dimension_values[0].value,
            "pageTitle": row.dimension_values[1].value,
            "views": row.metric_values[0].value,
        })
    report_text = json.dumps(rows, ensure_ascii=False, indent=2)

    # Geminiで要約
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    summary = model.generate_content(f"以下のGA4データを簡潔に要約してください：\n{report_text}")

    print("📊 GA4要約結果:")
    print(summary.text)

if __name__ == "__main__":
    main()
