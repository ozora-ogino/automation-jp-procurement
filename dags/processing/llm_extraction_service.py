#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM-based extraction service for processing bidding documents.
Refactored from preprocessor.py LLM extraction functionality.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from openai import OpenAI

from data.models import BiddingCase
from db.repositories import BiddingCaseRepository
from processing.text_processor import TextProcessor
from utils.file_service import FileService

logger = logging.getLogger(__name__)


class LLMExtractionService:
    """Service for extracting structured data from documents using LLM"""

    # Copy exact prompt from preprocessor.py EXTRACT_BID_INFO_PROMPT_TEMPLATE
    EXTRACTION_PROMPT_TEMPLATE = """
あなたは政府調達・公共入札の専門アナリストです。長年の経験を持ち、入札文書から重要情報を正確に抽出し、リスクを見極める能力があります。
以下の入札案件文書を詳細に分析し、入札参加判断に必要な全ての重要情報を抽出してください。

## 分析対象文書
{document_content}

## 抽出タスク

### 1. 基本的な抽出指示
上記文書から入札参加の可否判断に必要な情報を網羅的に抽出し、以下のJSON形式で出力してください。
情報の見落としがないよう、文書全体を注意深く読み、暗黙的な要件や条件も含めて抽出してください。

### 2. 出力形式

```json
{{
  "important_dates": {{
    "announcement_date": "公告日（YYYY-MM-DD）",
    "briefing_session": {{
      "date": "説明会日時（YYYY-MM-DD HH:MM）",
      "is_mandatory": "参加必須かどうか（true/false）",
      "location": "開催場所"
    }},
    "question_deadline": "質問受付締切（YYYY-MM-DD HH:MM）",
    "submission_deadline": "入札書提出締切（YYYY-MM-DD HH:MM）",
    "opening_date": "開札日時（YYYY-MM-DD HH:MM）",
    "contract_date": "契約締結予定日（YYYY-MM-DD）",
    "performance_period": {{
      "start": "履行開始日（YYYY-MM-DD）",
      "end": "履行終了日（YYYY-MM-DD）",
      "description": "履行期間の詳細説明"
    }}
  }},

  "qualification_requirements": {{
    "unified_qualification": {{
      "required": "全省庁統一資格の要否（true/false）",
      "category": "必要な業種区分（物品製造/役務提供等）",
      "rank": "必要な等級（A/B/C/D）",
      "valid_regions": ["有効な地域（関東・甲信越等）"]
    }},
    "specific_qualifications": [
      {{
        "name": "資格・認証名",
        "details": "詳細要件",
        "is_mandatory": "必須かどうか（true/false）"
      }}
    ],
    "experience_requirements": [
      {{
        "type": "実績の種類",
        "details": "具体的な要件",
        "period": "対象期間",
        "scale": "規模要件"
      }}
    ],
    "financial_requirements": {{
      "capital": "資本金要件",
      "annual_revenue": "年間売上高要件",
      "financial_soundness": "財務健全性要件"
    }},
    "personnel_requirements": [
      {{
        "role": "役割・職種",
        "qualification": "必要資格",
        "experience": "必要経験",
        "number": "必要人数"
      }}
    ],
    "other_requirements": ["その他の参加資格要件"]
  }},

  "business_content": {{
    "overview": "業務概要（100文字程度）",
    "detailed_content": "詳細な業務内容",
    "scope_of_work": ["作業範囲1", "作業範囲2"],
    "deliverables": [
      {{
        "item": "成果物名",
        "deadline": "納期",
        "format": "形式・仕様",
        "quantity": "数量"
      }}
    ],
    "technical_requirements": [
      {{
        "category": "技術要件カテゴリ",
        "requirement": "具体的要件",
        "priority": "重要度（必須/推奨/任意）"
      }}
    ],
    "performance_location": "履行場所",
    "work_conditions": "作業条件・制約事項"
  }},

  "financial_info": {{
    "budget_amount": "予定価格（数値のみ、円単位）",
    "budget_disclosure": "予定価格の公表有無（事前公表/事後公表/非公表）",
    "minimum_price": {{
      "exists": "最低制限価格の設定有無（true/false）",
      "calculation_method": "算出方法"
    }},
    "payment_terms": {{
      "method": "支払方法",
      "timing": "支払時期",
      "conditions": "支払条件"
    }},
    "advance_payment": {{
      "available": "前払金の有無（true/false）",
      "percentage": "前払金の割合",
      "conditions": "前払金の条件"
    }},
    "bid_bond": {{
      "required": "入札保証金の要否（true/false）",
      "amount": "金額または率",
      "exemption_conditions": "免除条件"
    }},
    "performance_bond": {{
      "required": "契約保証金の要否（true/false）",
      "amount": "金額または率",
      "exemption_conditions": "免除条件"
    }}
  }},

  "submission_requirements": {{
    "bid_documents": [
      {{
        "document_name": "書類名",
        "format": "形式",
        "copies": "必要部数",
        "notes": "注意事項"
      }}
    ],
    "technical_proposal": {{
      "required": "技術提案書の要否（true/false）",
      "page_limit": "ページ数制限",
      "evaluation_items": ["評価項目1", "評価項目2"]
    }},
    "submission_method": {{
      "options": ["提出方法（持参/郵送/電子入札）"],
      "electronic_system": "電子入札システム名",
      "notes": "提出時の注意事項"
    }},
    "submission_location": {{
      "address": "提出場所住所",
      "department": "担当部署",
      "reception_hours": "受付時間"
    }}
  }},

  "evaluation_criteria": {{
    "evaluation_method": "落札者決定方式",
    "price_weight": "価格点の配分（%）",
    "technical_weight": "技術点の配分（%）",
    "evaluation_items": [
      {{
        "category": "評価項目カテゴリ",
        "item": "評価項目",
        "points": "配点",
        "criteria": "評価基準"
      }}
    ],
    "minimum_technical_score": "技術点の最低基準点"
  }},

  "contact_info": {{
    "contract_department": {{
      "name": "契約担当部署",
      "person": "担当者名",
      "phone": "電話番号",
      "fax": "FAX番号",
      "email": "メールアドレス",
      "hours": "問い合わせ可能時間"
    }},
    "technical_department": {{
      "name": "技術担当部署",
      "person": "担当者名",
      "phone": "電話番号",
      "email": "メールアドレス"
    }}
  }},

  "special_conditions": {{
    "joint_venture": {{
      "allowed": "JV参加の可否（true/false）",
      "conditions": "JV参加の条件"
    }},
    "subcontracting": {{
      "allowed": "再委託の可否（true/false）",
      "restrictions": "再委託の制限事項"
    }},
    "confidentiality": "機密保持に関する要件",
    "intellectual_property": "知的財産権の取扱い",
    "penalty_clauses": "違約金・損害賠償条項"
  }},

  "risk_analysis": {{
    "key_points": [
      {{
        "point": "重要ポイント",
        "importance": "重要度（高/中/低）",
        "reason": "重要な理由"
      }}
    ],
    "red_flags": [
      {{
        "issue": "リスク・懸念事項",
        "severity": "深刻度（高/中/低）",
        "description": "詳細説明",
        "mitigation": "対策案"
      }}
    ],
    "unclear_points": [
      {{
        "item": "不明確な点",
        "impact": "影響範囲",
        "action_required": "必要なアクション"
      }}
    ]
  }},

  "bid_feasibility": {{
    "strengths": ["自社の強み・有利な点"],
    "weaknesses": ["自社の弱み・不利な点"],
    "preparation_time": "準備に必要な期間の評価",
    "resource_requirements": "必要なリソースの評価",
    "competition_level": "想定される競争の激しさ（高/中/低）",
    "recommendation": {{
      "participate": "参加推奨度（推奨/条件付き推奨/非推奨）",
      "reasoning": "判断理由",
      "conditions": ["参加する場合の前提条件"]
    }}
  }}
}}

3. 抽出時の注意事項
完全性の確保
文書内の全ての要件を漏れなく抽出すること
本文だけでなく、添付資料への参照や注記も確認すること
正確性の確保
日付は必ずYYYY-MM-DD形式で統一
時刻はHH:MM形式（24時間表記）で統一
金額は数値のみ（カンマなし、円単位）で記載
ドキュメントに記載されていない場合、その内容はnullとし、間違えた値を代入しないこと。間違った値を出力した場合はペナルティが課せられます。

解釈の明確化
曖昧な表現は「unclear_points」に記録
暗黙的な要件も明示的に抽出
文書に明記されていない標準的な要件も推測して記載
リスク分析の徹底
通常と異なる条件は全て「red_flags」に記録
短い準備期間、厳しい要件、不明確な仕様は特に注意
財務的リスク、技術的リスク、スケジュールリスクを総合的に評価
NULL値の扱い
該当情報が文書に存在しない場合：null
該当しない項目の場合：null
空配列が適切な場合：[]
不明確で推測が必要な場合：unclear_pointsに記載
実用性の重視
入札参加の意思決定に直接影響する情報を優先
形式的な情報より実質的なリスクと機会を重視
具体的なアクションにつながる情報を抽出
文書を分析し、企業が入札参加を判断するために必要な全ての情報を抽出してください。
"""

    def __init__(self,
                 case_repository: BiddingCaseRepository,
                 text_processor: TextProcessor,
                 file_service: FileService,
                 openai_api_key: str,
                 model: str = "gpt-4o-2024-11-20"):  # Same model as preprocessor.py
        self.case_repo = case_repository
        self.text_processor = text_processor
        self.file_service = file_service
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model

    def process_cases_with_llm(self, limit: int = 50) -> Dict[str, Any]:
        """Process unprocessed cases with LLM extraction"""
        start_time = datetime.now()
        processed_count = 0
        success_count = 0
        errors = []

        try:
            # Find cases that need processing
            cases = self.case_repo.find_unprocessed_cases(limit)
            logger.info(f"Found {len(cases)} cases to process with LLM")

            for case_info in cases:
                case_id = str(case_info['case_id'])  # Convert to string
                doc_dir = case_info['document_directory']

                try:
                    # Process documents and extract with LLM
                    extracted_data = self._process_case_documents(case_id, doc_dir)

                    if extracted_data:
                        # Update database with extracted data
                        success = self.case_repo.update_llm_extraction(case_id, extracted_data)
                        if success:
                            success_count += 1
                            logger.info(f"Successfully processed case {case_id}")
                        else:
                            errors.append(f"Failed to update case {case_id}")
                    else:
                        errors.append(f"No data extracted for case {case_id}")

                    processed_count += 1

                except Exception as e:
                    error_msg = f"Error processing case {case_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    processed_count += 1

            duration = (datetime.now() - start_time).total_seconds()

            return {
                'success': True,
                'total_cases': len(cases),
                'processed': processed_count,
                'successful': success_count,
                'errors': errors,
                'duration_seconds': duration
            }

        except Exception as e:
            logger.error(f"LLM extraction process failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _process_case_documents(self, case_id: str, doc_directory: str) -> Optional[Dict[str, Any]]:
        """Process all documents for a case and extract data with LLM"""
        try:
            doc_path = Path(doc_directory)
            if not doc_path.exists():
                logger.warning(f"Document directory not found: {doc_directory}")
                return None

            # Find all documents in the directory
            all_files = list(doc_path.rglob('*'))
            document_files = [f for f in all_files if f.is_file() and f.suffix.lower() in
                            ['.pdf', '.html', '.htm', '.txt', '.md']]

            if not document_files:
                logger.warning(f"No processable documents found in {doc_directory}")
                return None

            # Check if concatenated file already exists
            concat_path = self.file_service.get_concat_file_path(case_id)

            if not concat_path.exists():
                # Concatenate all documents
                concat_path = self.text_processor.concatenate_documents(
                    document_files, concat_path
                )

                if not concat_path:
                    logger.error(f"Failed to concatenate documents for case {case_id}")
                    return None

            # Read concatenated content
            content = self.file_service.read_text(concat_path)

            # Truncate if too long (LLM token limits)
            max_chars = 30000  # Adjust based on model limits
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[... 以降省略 ...]"

            # Extract data using LLM
            extracted_data = self._extract_with_llm(content)

            # Add metadata
            if extracted_data:
                extracted_data['extraction_metadata'] = {
                    'processed_files': len(document_files),
                    'model': self.model,
                    'timestamp': datetime.now().isoformat()
                }

            return extracted_data

        except Exception as e:
            logger.error(f"Error processing documents for case {case_id}: {e}")
            return None

    def _extract_with_llm(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract structured data from content using LLM"""
        try:
            prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(document_content=content)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは政府調達・公共入札の専門アナリストです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=4000
            )

            # Parse the response
            extracted_json = response.choices[0].message.content
            extracted_data = json.loads(extracted_json)

            return extracted_data

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return None
