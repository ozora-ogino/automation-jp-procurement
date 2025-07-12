from jinja2 import Template
import json

VERIFY_BID_PROMPT_TEMPLATE = Template("""
あなたは政府調達の入札判定アナリストです。次の会社プロファイルと案件要件を比較し、入札可能性を評価してください。

## 重要な判定基準

### 資格要件に関する判定ルール
1. **ランクD、ランク無し、ランク不明の案件**: 中小企業でも参加可能
2. **資格不要の案件**: 全ての企業が参加可能
3. **ランクA、B、C指定の案件**: 該当ランクの資格が必要
4. **地域別資格要件**: 指定地域の資格が必要
5. **業種別資格要件**: 指定業種の資格が必要

### 判定ポイント
- 資格要件が明記されていない場合は、中小企業に有利に解釈
- 複数の資格要件がある場合、全てを満たす必要があるかを確認
- 特定の業種分野での実績要件があるかを確認

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

上記の会社プロファイルと案件データを比較し、特に資格要件に着目して入札可能性を判定してください。

判定ステップ:
1. まず案件のqualifications_rawフィールドを確認
2. 資格要件のランク（A/B/C/D/ランク無し/不明）を判別
3. 会社プロファイルと比較して入札可否を判定

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
- 資格要件に関する判定は特に明確に記載してください
""")


def build_prompt(case_name: str, organization_name: str, details: str = "", 
                qualification_info: str = "", extracted_data: dict = None) -> str:
    """
    Build a prompt for LLM inference based on case information.
    
    Args:
        case_name: Name of the bidding case
        organization_name: Organization offering the bid
        details: Case details
        qualification_info: Qualification requirements
        extracted_data: LLM extracted data (if available)
    
    Returns:
        Formatted prompt string
    """
    # Prepare bid data for the template
    bid_data = {
        "case_name": case_name,
        "organization_name": organization_name,
        "details": details or "詳細情報なし",
        "qualification_info": qualification_info or "資格要件情報なし"
    }
    
    # Add extracted data if available
    if extracted_data:
        bid_data["extracted_info"] = extracted_data
    
    # Render the prompt using the template
    prompt = VERIFY_BID_PROMPT_TEMPLATE.render(
        bid_data=json.dumps(bid_data, ensure_ascii=False, indent=2)
    )
    
    return prompt
