from jinja2 import Template

VERIFY_BID_PROMPT_TEMPLATE = Template("""
あなたは政府調達の入札判定アナリストです。次の会社プロファイルと案件要件を比較し、入札可能性を評価してください。

## 会社プロファイル
{
  "company_name_ja": "株式会社Solafune",
  "company_name_en": "Solafune, Inc.",
  "corporate_number": "5360001027200",
  "established": "2020-03-20",
  "capital_jpy": 7300000,
  "hq_address": "東京都千代田区丸の内2-4-1 丸ビル28F 100-6390",
  "representative": "上地 練（Ren Uechi）",
  "employees": 11,
  "industry_codes": {
    "JSIC": "3910 情報サービス業",
    "NAICS": "541360 Geospatial Mapping Services"
  },
  "business_summary": "衛星・地理空間データ解析技術を開発し、農業・防災・天然資源・金融・防衛・保険など多分野向けにデータサイエンス競技やAPIサービスを提供。",
  "core_technologies": [
    "SAR・光学衛星画像AI解析",
    "Super-Resolution & Generative AI",
    "全球規模データ基盤"
  ],
  "government_bid_history": [
    { "date": "2025-06-04", "agency": "防衛省", "title": "AI用教師データの作成(その5)" },
    { "date": "2025-03-24", "agency": "不明", "title": "実用性データ取得装置" }
  ],
  "financials": null,
  "risk_compliance": "公開情報ベースで特記事項なし",
  "contact": {
    "email": "info@solafune.com",
    "phone": "+81-50-3161-9015"
  }
}

## 案件要件

{{ bid_data }}

## 判定指示

上記の会社プロファイルと案件データを比較し、入札可能性を判定してください。
必ず以下のJSON形式で回答してください：

{
  "is_eligible_bid": true または false,
  "reason": [
    "理由1（必須）",
    "理由2（任意）",
    "理由3（任意）"
  ]
}

注意事項：
- "is_eligible_bid"フィールドは必ずtrue（入札可能）またはfalse（入札不可）のいずれかの値にしてください
- "reason"フィールドは配列形式で、最低1つ、最大3つの理由を日本語で記載してください
- 理由は具体的かつ簡潔に記載してください
""")
