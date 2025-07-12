#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM inference service for eligibility determination.
Refactored from llm.py.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from jinja2 import Template
from openai import OpenAI

from db.repositories import BiddingCaseRepository

logger = logging.getLogger(__name__)

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


class LLMInferenceService:
    """Service for LLM-based eligibility inference"""

    def __init__(self,
                 case_repository: BiddingCaseRepository,
                 openai_api_key: str,
                 model: str = "gpt-4o-2024-11-20"):  # Same model as llm.py
        self.case_repo = case_repository
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model

    def run_inference_batch(self, limit: int = 100) -> Dict[str, Any]:
        """Run eligibility inference on a batch of cases"""
        start_time = datetime.now()
        processed_count = 0
        eligible_count = 0
        errors = []

        try:
            # Get cases for inference
            cases = self._get_cases_for_inference(limit)
            logger.info(f"Found {len(cases)} cases for inference")

            for case in cases:
                try:
                    # Run inference
                    result = self._run_case_inference(case)

                    if result:
                        # Update case with inference results using same format as llm.py
                        update_data = {
                            'is_eligible': result['is_eligible'],
                            'reason': result['reason'],
                            'details': result['details']
                        }

                        success = self._update_case_inference(case['case_id'], update_data)

                        if success:
                            processed_count += 1
                            if result['is_eligible']:
                                eligible_count += 1
                            logger.info(f"Case ID {case['case_id']}: {'入札可能' if result['is_eligible'] else '入札不可'}")
                            
                            # Commit every 10 cases like original
                            if processed_count % 10 == 0:
                                logger.info(f"進捗: {processed_count}/{len(cases)}")
                        else:
                            errors.append(f"Failed to update case {case['case_id']}")
                    else:
                        errors.append(f"No inference result for case {case['case_id']}")

                except Exception as e:
                    error_msg = f"Error processing case {case['case_id']}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            duration = (datetime.now() - start_time).total_seconds()

            return {
                'success': True,
                'total_cases': len(cases),
                'processed': processed_count,
                'eligible': eligible_count,
                'errors': errors,
                'duration_seconds': duration
            }

        except Exception as e:
            logger.error(f"Inference batch failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_cases_for_inference(self, limit: int) -> List[Dict[str, Any]]:
        """Get cases that need inference"""
        # This would be implemented in the repository
        # For now, using a simple query
        with self.case_repo.get_cursor() as cursor:
            # Get today's cases like original llm.py
            from datetime import date
            today = date.today()
            
            cursor.execute("""
                SELECT
                    case_id, case_name, org_name as organization_name,
                    org_prefecture, announcement_date, bidding_date,
                    bidding_format as procurement_type,
                    qualifications_raw as qualification_info,
                    business_types_raw, overview as details,
                    planned_price_raw, delivery_location, remarks,
                    is_eligible_to_bid
                FROM bidding_cases
                WHERE
                    DATE(created_at) = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (today, limit))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cases = [dict(zip(columns, row)) for row in rows]
            
            # Filter cases like original llm.py
            filtered_cases = []
            skipped_count = 0
            for case in cases:
                # Skip if already marked as ineligible
                if case.get('is_eligible_to_bid') == False:
                    logger.info(f"Case ID {case['case_id']} は既に入札不可と判定されているため、スキップします")
                    skipped_count += 1
                    continue
                filtered_cases.append(case)
            
            logger.info(f"本日の入札データ数: {len(cases)}, スキップ: {skipped_count}")
            return filtered_cases

    def _run_case_inference(self, case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run inference on a single case"""
        try:
            # Build prompt using same format as llm.py
            bid_data = {
                "case_id": case.get('case_id'),
                "case_name": case.get('case_name'),
                "org_name": case.get('organization_name'),
                "org_prefecture": case.get('org_prefecture'),
                "announcement_date": case.get('announcement_date').isoformat() if case.get('announcement_date') else None,
                "bidding_date": case.get('bidding_date').isoformat() if case.get('bidding_date') else None,
                "bidding_format": case.get('procurement_type'),
                "qualifications_raw": case.get('qualification_info'),
                "business_types_raw": case.get('business_types_raw'),
                "overview": case.get('details'),
                "planned_price_raw": case.get('planned_price_raw'),
                "delivery_location": case.get('delivery_location'),
                "remarks": case.get('remarks')
            }

            # Use the same prompt template as llm.py
            prompt = VERIFY_BID_PROMPT_TEMPLATE.render(
                bid_data=json.dumps(bid_data, ensure_ascii=False, indent=2)
            )

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは政府調達の入札判定アナリストです。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            # Parse response
            result_json = response.choices[0].message.content
            result = json.loads(result_json)

            # Ensure we have the required fields
            if "is_eligible_bid" not in result or "reason" not in result:
                raise ValueError("レスポンスに必要なフィールドが含まれていません")

            # reasonが配列の場合は結合して文字列にする
            reason_text = result["reason"]
            if isinstance(reason_text, list):
                reason_text = " / ".join(reason_text)

            return {
                'is_eligible': result["is_eligible_bid"],
                'reason': reason_text,
                'details': result
            }

        except Exception as e:
            logger.error(f"Inference error for case {case['case_id']}: {e}")
            return None

    def _update_case_inference(self, case_id: str, update_data: Dict[str, Any]) -> bool:
        """Update case with inference results"""
        try:
            # Convert case_id to int for database
            case_id_int = int(case_id)
            
            with self.case_repo.get_cursor() as cursor:
                # Update exactly like the original llm.py
                cursor.execute("""
                    UPDATE bidding_cases
                    SET
                        is_eligible_to_bid = %s,
                        eligibility_reason = %s,
                        eligibility_details = %s,
                        updated_at = NOW()
                    WHERE case_id = %s
                """, (
                    update_data['is_eligible'],
                    update_data['reason'],
                    json.dumps(update_data['details'], ensure_ascii=False),
                    case_id_int
                ))

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update case {case_id}: {e}")
            return False
