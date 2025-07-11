import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
from bs4 import BeautifulSoup
import pandas as pd
from openai import OpenAI
from jinja2 import Template
from sql_connection import PostgreSQLConnection

# OpenAI client initialization
client = OpenAI()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Document summarization prompt template
DOCUMENT_SUMMARY_PROMPT_TEMPLATE = Template("""
あなたは政府調達・公共入札の専門アナリストです。長年の経験を持ち、入札文書から重要情報を正確に抽出し、リスクを見極める能力があります。
以下の入札案件文書を詳細に分析し、入札参加判断に必要な全ての重要情報を抽出してください。

## 分析対象文書
{{document_content}}

## 抽出タスク

### 1. 基本的な抽出指示
上記文書から入札参加の可否判断に必要な情報を網羅的に抽出し、以下のJSON形式で出力してください。
情報の見落としがないよう、文書全体を注意深く読み、暗黙的な要件や条件も含めて抽出してください。

### 2. 出力形式

```json
{
  "important_dates": {
    "announcement_date": "公告日（YYYY-MM-DD）",
    "briefing_session": {
      "date": "説明会日時（YYYY-MM-DD HH:MM）",
      "is_mandatory": "参加必須かどうか（true/false）",
      "location": "開催場所"
    },
    "question_deadline": "質問受付締切（YYYY-MM-DD HH:MM）",
    "submission_deadline": "入札書提出締切（YYYY-MM-DD HH:MM）",
    "opening_date": "開札日時（YYYY-MM-DD HH:MM）",
    "contract_date": "契約締結予定日（YYYY-MM-DD）",
    "performance_period": {
      "start": "履行開始日（YYYY-MM-DD）",
      "end": "履行終了日（YYYY-MM-DD）",
      "description": "履行期間の詳細説明"
    }
  },

  "qualification_requirements": {
    "unified_qualification": {
      "required": "全省庁統一資格の要否（true/false）",
      "category": "必要な業種区分（物品製造/役務提供等）",
      "rank": "必要な等級（A/B/C/D）",
      "valid_regions": ["有効な地域（関東・甲信越等）"]
    },
    "specific_qualifications": [
      {
        "name": "資格・認証名",
        "details": "詳細要件",
        "is_mandatory": "必須かどうか（true/false）"
      }
    ],
    "experience_requirements": [
      {
        "type": "実績の種類",
        "details": "具体的な要件",
        "period": "対象期間",
        "scale": "規模要件"
      }
    ],
    "financial_requirements": {
      "capital": "資本金要件",
      "annual_revenue": "年間売上高要件",
      "financial_soundness": "財務健全性要件"
    },
    "personnel_requirements": [
      {
        "role": "役割・職種",
        "qualification": "必要資格",
        "experience": "必要経験",
        "number": "必要人数"
      }
    ],
    "other_requirements": ["その他の参加資格要件"]
  },

  "business_content": {
    "overview": "業務概要（100文字程度）",
    "detailed_content": "詳細な業務内容",
    "scope_of_work": ["作業範囲1", "作業範囲2"],
    "deliverables": [
      {
        "item": "成果物名",
        "deadline": "納期",
        "format": "形式・仕様",
        "quantity": "数量"
      }
    ],
    "technical_requirements": [
      {
        "category": "技術要件カテゴリ",
        "requirement": "具体的要件",
        "priority": "重要度（必須/推奨/任意）"
      }
    ],
    "performance_location": "履行場所",
    "work_conditions": "作業条件・制約事項"
  },

  "financial_info": {
    "budget_amount": "予定価格（数値のみ、円単位）",
    "budget_disclosure": "予定価格の公表有無（事前公表/事後公表/非公表）",
    "minimum_price": {
      "exists": "最低制限価格の設定有無（true/false）",
      "calculation_method": "算出方法"
    },
    "payment_terms": {
      "method": "支払方法",
      "timing": "支払時期",
      "conditions": "支払条件"
    },
    "advance_payment": {
      "available": "前払金の有無（true/false）",
      "percentage": "前払金の割合",
      "conditions": "前払金の条件"
    },
    "bid_bond": {
      "required": "入札保証金の要否（true/false）",
      "amount": "金額または率",
      "exemption_conditions": "免除条件"
    },
    "performance_bond": {
      "required": "契約保証金の要否（true/false）",
      "amount": "金額または率",
      "exemption_conditions": "免除条件"
    }
  },

  "submission_requirements": {
    "bid_documents": [
      {
        "document_name": "書類名",
        "format": "形式",
        "copies": "必要部数",
        "notes": "注意事項"
      }
    ],
    "technical_proposal": {
      "required": "技術提案書の要否（true/false）",
      "page_limit": "ページ数制限",
      "evaluation_items": ["評価項目1", "評価項目2"]
    },
    "submission_method": {
      "options": ["提出方法（持参/郵送/電子入札）"],
      "electronic_system": "電子入札システム名",
      "notes": "提出時の注意事項"
    },
    "submission_location": {
      "address": "提出場所住所",
      "department": "担当部署",
      "reception_hours": "受付時間"
    }
  },

  "evaluation_criteria": {
    "evaluation_method": "落札者決定方式",
    "price_weight": "価格点の配分（%）",
    "technical_weight": "技術点の配分（%）",
    "evaluation_items": [
      {
        "category": "評価項目カテゴリ",
        "item": "評価項目",
        "points": "配点",
        "criteria": "評価基準"
      }
    ],
    "minimum_technical_score": "技術点の最低基準点"
  },

  "contact_info": {
    "contract_department": {
      "name": "契約担当部署",
      "person": "担当者名",
      "phone": "電話番号",
      "fax": "FAX番号",
      "email": "メールアドレス",
      "hours": "問い合わせ可能時間"
    },
    "technical_department": {
      "name": "技術担当部署",
      "person": "担当者名",
      "phone": "電話番号",
      "email": "メールアドレス"
    }
  },

  "special_conditions": {
    "joint_venture": {
      "allowed": "JV参加の可否（true/false）",
      "conditions": "JV参加の条件"
    },
    "subcontracting": {
      "allowed": "再委託の可否（true/false）",
      "restrictions": "再委託の制限事項"
    },
    "confidentiality": "機密保持に関する要件",
    "intellectual_property": "知的財産権の取扱い",
    "penalty_clauses": "違約金・損害賠償条項"
  },

  "risk_analysis": {
    "key_points": [
      {
        "point": "重要ポイント",
        "importance": "重要度（高/中/低）",
        "reason": "重要な理由"
      }
    ],
    "red_flags": [
      {
        "issue": "リスク・懸念事項",
        "severity": "深刻度（高/中/低）",
        "description": "詳細説明",
        "mitigation": "対策案"
      }
    ],
    "unclear_points": [
      {
        "item": "不明確な点",
        "impact": "影響範囲",
        "action_required": "必要なアクション"
      }
    ]
  },

  "bid_feasibility": {
    "strengths": ["自社の強み・有利な点"],
    "weaknesses": ["自社の弱み・不利な点"],
    "preparation_time": "準備に必要な期間の評価",
    "resource_requirements": "必要なリソースの評価",
    "competition_level": "想定される競争の激しさ（高/中/低）",
    "recommendation": {
      "participate": "参加推奨度（推奨/条件付き推奨/非推奨）",
      "reasoning": "判断理由",
      "conditions": ["参加する場合の前提条件"]
    }
  }
}

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
""")


class DocumentSummarizer:
    """案件文書を要約し、重要情報を抽出するクラス"""

    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        self.temperature = 0.1
        self.max_content_length = 10000  # 文書内容の最大文字数

    def read_document_content(self, file_path: str) -> Optional[str]:
        """文書ファイルの内容を読み取る"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None

            # PDFファイルの処理
            if file_path.suffix.lower() == '.pdf':
                return self._read_pdf(file_path)

            # HTMLファイルの処理
            elif file_path.suffix.lower() in ['.html', '.htm']:
                return self._read_html(file_path)

            # Excel/CSVファイルの処理
            elif file_path.suffix.lower() in ['.xlsx', '.xls', '.csv']:
                return self._read_spreadsheet(file_path)

            # テキストファイルの処理
            elif file_path.suffix.lower() in ['.txt', '.md']:
                return self._read_text(file_path)

            else:
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return None

        except Exception as e:
            logger.error(f"Error reading document {file_path}: {e}")
            return None

    def _read_pdf(self, file_path: Path) -> str:
        """PDFファイルの内容を読み取る"""
        if not PYPDF2_AVAILABLE:
            logger.warning(f"PyPDF2 not available. Cannot read PDF: {file_path}")
            return ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text[:self.max_content_length]
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return ""

    def _read_html(self, file_path: Path) -> str:
        """HTMLファイルの内容を読み取る"""
        try:
            # Check if it's actually an Excel file with .html extension
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':  # OLE header
                    logger.info(f"File {file_path} is actually an Excel file, attempting to read as Excel")
                    return self._read_spreadsheet(file_path)

            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                # スクリプトとスタイルを除去
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                # 空白行を削除
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                return "\n".join(lines)[:self.max_content_length]
        except Exception as e:
            logger.error(f"Error reading HTML {file_path}: {e}")
            return ""

    def _read_spreadsheet(self, file_path: Path) -> str:
        """Excel/CSVファイルの内容を読み取る"""
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            return df.to_string()[:self.max_content_length]
        except Exception as e:
            logger.error(f"Error reading spreadsheet {file_path}: {e}")
            return ""

    def _read_text(self, file_path: Path) -> str:
        """テキストファイルの内容を読み取る"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()[:self.max_content_length]
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return ""

    def summarize_document(self, document_info: Dict[str, Any], content: str) -> Dict[str, Any]:
        """単一の文書を要約する"""
        try:
            prompt = DOCUMENT_SUMMARY_PROMPT_TEMPLATE.render(
                document_name=document_info.get('name', 'Unknown'),
                document_type=document_info.get('type', 'unknown'),
                anken_id=document_info.get('anken_id', 'Unknown'),
                document_content=content
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは政府調達案件の文書分析専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "document_name": document_info.get('name'),
                "document_type": document_info.get('type'),
                "summary": result
            }

        except Exception as e:
            logger.error(f"Error summarizing document: {e}")
            return {
                "document_name": document_info.get('name'),
                "document_type": document_info.get('type'),
                "summary": None,
                "error": str(e)
            }

    def summarize_anken(self, anken_id: str, anken_data: Dict[str, Any],
                       document_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """案件全体を要約する"""
        try:
            # 基本情報の整形
            basic_info = {
                "case_id": anken_data.get('case_id'),
                "case_name": anken_data.get('case_name'),
                "org_name": anken_data.get('org_name'),
                "bidding_format": anken_data.get('bidding_format'),
                "announcement_date": anken_data.get('announcement_date'),
                "bidding_date": anken_data.get('bidding_date')
            }

            prompt = ANKEN_SUMMARY_PROMPT_TEMPLATE.render(
                anken_basic_info=json.dumps(basic_info, ensure_ascii=False, indent=2),
                document_summaries=json.dumps(document_summaries, ensure_ascii=False, indent=2)
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは政府調達案件の総合分析専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error summarizing anken: {e}")
            raise


def process_anken_documents(anken_id: str) -> Dict[str, Any]:
    """案件の全文書を処理し、要約を生成する"""
    db_conn = PostgreSQLConnection()
    summarizer = DocumentSummarizer()

    try:
        with db_conn.get_connection() as conn:
            with conn.cursor() as cursor:
                # 案件情報を取得
                cursor.execute("""
                    SELECT case_id, case_name, org_name, bidding_format,
                           announcement_date, bidding_date, document_directory,
                           documents
                    FROM bidding_cases
                    WHERE case_id = %s
                """, (anken_id,))

                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Anken {anken_id} not found")

                anken_data = {
                    'case_id': row[0],
                    'case_name': row[1],
                    'org_name': row[2],
                    'bidding_format': row[3],
                    'announcement_date': row[4].isoformat() if row[4] else None,
                    'bidding_date': row[5].isoformat() if row[5] else None,
                    'document_directory': row[6],
                    'documents': row[7] or []
                }

                # 文書ディレクトリの確認
                doc_dir = Path(anken_data['document_directory'])
                if not doc_dir.exists():
                    raise ValueError(f"Document directory not found: {doc_dir}")

                # 各文書を処理
                document_summaries = []
                for doc_info in anken_data['documents']:
                    # 文書ファイルのパスを構築
                    file_name = f"{doc_info['index']:02d}_{doc_info['name']}"
                    file_path = doc_dir / file_name

                    # 文書内容を読み取る
                    content = summarizer.read_document_content(str(file_path))
                    if content:
                        # 文書を要約
                        summary = summarizer.summarize_document(doc_info, content)
                        document_summaries.append(summary)
                        logger.info(f"Summarized document: {doc_info['name']}")
                    else:
                        logger.warning(f"Could not read document: {file_path}")

                # 案件全体の要約を生成
                anken_summary = summarizer.summarize_anken(
                    anken_id, anken_data, document_summaries
                )

                # 結果を保存
                result = {
                    'anken_id': anken_id,
                    'processed_at': datetime.now().isoformat(),
                    'document_count': len(anken_data['documents']),
                    'summarized_count': len(document_summaries),
                    'document_summaries': document_summaries,
                    'anken_summary': anken_summary
                }

                # データベースに要約結果を保存
                cursor.execute("""
                    UPDATE bidding_cases
                    SET document_summaries = %s,
                        anken_summary = %s,
                        updated_at = NOW()
                    WHERE case_id = %s
                """, (
                    json.dumps(document_summaries, ensure_ascii=False),
                    json.dumps(anken_summary, ensure_ascii=False),
                    anken_id
                ))
                conn.commit()

                return result

    except Exception as e:
        logger.error(f"Error processing anken documents: {e}")
        raise


def main():
    """メイン処理：最新の案件文書を要約する"""
    db_conn = PostgreSQLConnection()

    try:
        with db_conn.get_connection() as conn:
            with conn.cursor() as cursor:
                # 文書がダウンロード済みで未要約の案件を取得
                cursor.execute("""
                    SELECT case_id
                    FROM bidding_cases
                    WHERE document_count > 0
                    AND downloaded_count > 0
                    AND (document_summaries IS NULL OR anken_summary IS NULL)
                    ORDER BY created_at DESC
                    LIMIT 10
                """)

                anken_ids = [row[0] for row in cursor.fetchall()]

                if not anken_ids:
                    logger.info("No ankens found for summarization")
                    return

                logger.info(f"Found {len(anken_ids)} ankens to summarize")

                # 各案件を処理
                for anken_id in anken_ids:
                    try:
                        logger.info(f"Processing anken: {anken_id}")
                        result = process_anken_documents(str(anken_id))
                        logger.info(f"Successfully summarized anken {anken_id}: "
                                  f"{result['summarized_count']}/{result['document_count']} documents")
                    except Exception as e:
                        logger.error(f"Failed to process anken {anken_id}: {e}")
                        continue

    except Exception as e:
        logger.error(f"Error in main processing: {e}")
        raise


if __name__ == "__main__":
    main()
