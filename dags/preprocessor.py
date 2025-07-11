#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from string import Template
from openai import OpenAI

from sql_connection import PostgreSQLConnection
from consts import CSV_FILE_PATH

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# LangChainのPyPDFLoaderをインポート
try:
    from langchain.document_loaders import PyPDFLoader
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("langchain not installed. Install with: pip install langchain")
    LANGCHAIN_AVAILABLE = False


class FileProcessor:
    """各種ファイルフォーマットを処理してテキストを抽出するクラス"""

    def __init__(self):
        self.supported_extensions = {
            '.pdf': self.process_pdf,
            '.html': self.process_html,
            '.htm': self.process_html,
            '.txt': self.process_text,
            '.md': self.process_text,
        }

    def process_pdf(self, file_path: Path) -> str:
        """PDFファイルからテキストを抽出"""
        if not LANGCHAIN_AVAILABLE:
            logger.warning(f"Cannot process PDF {file_path.name}: langchain not available")
            return ""

        try:
            loader = PyPDFLoader(str(file_path))
            pages = loader.load()

            # 全ページのテキストを結合
            text_content = []
            for i, page in enumerate(pages):
                page_text = page.page_content.strip()
                if page_text:
                    text_content.append(f"[Page {i+1}]\n{page_text}")

            return "\n\n".join(text_content)

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return ""

    def process_html(self, file_path: Path) -> str:
        """HTMLファイルからテキストを抽出（タグを除去）"""
        try:
            # まずバイナリで読んでファイルタイプをチェック
            with open(file_path, 'rb') as f:
                header = f.read(8)
                # OLEヘッダー（Excel等のMS Office形式）をチェック
                if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                    logger.info(f"File {file_path.name} is actually an Excel file, skipping...")
                    return f"[File is Excel format with .html extension, cannot process]"

            # HTMLとして読み込み
            encodings = ['utf-8', 'shift_jis', 'euc-jp', 'iso-2022-jp']
            content = None

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                logger.error(f"Could not decode HTML file {file_path}")
                return ""

            # BeautifulSoupでHTMLをパース
            soup = BeautifulSoup(content, 'html.parser')

            # スクリプトとスタイルタグを削除
            for element in soup(['script', 'style', 'meta', 'link']):
                element.decompose()

            # テキストを抽出
            text = soup.get_text()

            # 連続する空白や改行を整理
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if line:
                    lines.append(line)

            return '\n'.join(lines)

        except Exception as e:
            logger.error(f"Error processing HTML {file_path}: {e}")
            return ""

    def process_text(self, file_path: Path) -> str:
        """テキストファイルをそのまま読み込む"""
        try:
            encodings = ['utf-8', 'shift_jis', 'euc-jp']

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read().strip()
                except UnicodeDecodeError:
                    continue

            logger.error(f"Could not decode text file {file_path}")
            return ""

        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            return ""

    def process_file(self, file_path: Path) -> Tuple[str, str]:
        """ファイルを処理してテキストを抽出"""
        extension = file_path.suffix.lower()

        if extension in self.supported_extensions:
            processor = self.supported_extensions[extension]
            content = processor(file_path)
            return file_path.name, content
        else:
            logger.warning(f"Unsupported file type: {file_path.name}")
            return file_path.name, ""


def concatenate_files(directory_path: str, output_file: str = 'concatenated_output.txt',
                     include_patterns: List[str] = None,
                     exclude_patterns: List[str] = None) -> str:
    """
    ディレクトリ内の全ファイルを処理して1つのテキストファイルに結合

    Args:
        directory_path: 処理するディレクトリのパス
        output_file: 出力ファイル名
        include_patterns: 含めるファイルパターン
        exclude_patterns: 除外するファイルパターン (デフォルト: ['.git', '__pycache__', '.pyc', '.log'])

    Returns:
        str: 出力ファイルのパス
    """

    # デフォルトの除外パターン
    if exclude_patterns is None:
        exclude_patterns = ['.git', '__pycache__', '.pyc', '.log']

    directory_path = Path(directory_path)
    if not directory_path.exists():
        raise ValueError(f"ディレクトリが見つかりません: {directory_path}")

    if not directory_path.is_dir():
        raise ValueError(f"パスがディレクトリではありません: {directory_path}")

    processor = FileProcessor()
    processed_files = []

    # ディレクトリ内の全ファイルを走査
    all_files = sorted(directory_path.rglob("*"))

    for file_path in all_files:
        if not file_path.is_file():
            continue

        # 除外パターンのチェック
        if exclude_patterns:
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                logger.info(f"Skipping excluded file: {file_path.name}")
                continue

        # 含めるパターンのチェック
        if include_patterns:
            if not any(pattern in str(file_path) for pattern in include_patterns):
                continue

        logger.info(f"Processing: {file_path.name}")
        file_name, content = processor.process_file(file_path)

        if content:
            processed_files.append({
                'path': str(file_path.relative_to(directory_path)),
                'name': file_name,
                'content': content
            })

    # 結果を1つのファイルに出力
    output_path = Path(output_file)
    logger.info(f"Writing {len(processed_files)} files to {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, file_data in enumerate(processed_files):
            if i > 0:
                f.write("\n\n###\n\n")

            # ファイル情報のヘッダー
            f.write(f"File: {file_data['path']}\n")
            f.write(f"Name: {file_data['name']}\n")
            f.write("="*80 + "\n\n")

            # コンテンツ
            f.write(file_data['content'])

    # サマリーを表示
    logger.info(f"処理完了:")
    logger.info(f"  - 処理したファイル数: {len(processed_files)}")
    logger.info(f"  - 出力ファイル: {output_path}")
    logger.info(f"  - ファイルサイズ: {output_path.stat().st_size:,} bytes")

    # 処理したファイルのリスト
    logger.info(f"処理したファイル:")
    for file_data in processed_files:
        logger.info(f"  - {file_data['path']}")

    return str(output_path)


# 入札情報抽出プロンプトテンプレート
EXTRACT_BID_INFO_PROMPT_TEMPLATE = Template("""
あなたは政府調達・公共入札の専門アナリストです。長年の経験を持ち、入札文書から重要情報を正確に抽出し、リスクを見極める能力があります。
以下の入札案件文書を詳細に分析し、入札参加判断に必要な全ての重要情報を抽出してください。

## 分析対象文書
$query

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


class BidDocumentExtractor:
    """LLMを使用して入札文書から情報を抽出するクラス"""

    def __init__(self, openai_api_key: str = None):
        """
        Args:
            openai_api_key: OpenAI APIキー。指定されない場合は環境変数から取得
        """
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
        else:
            # 環境変数から取得
            self.client = OpenAI()

        self.model = "gpt-4o-2024-11-20"

    def extract_bid_information(self, document_text: str, case_id: str = None) -> Dict[str, Any]:
        """
        入札文書から情報を抽出

        Args:
            document_text: 分析対象の文書テキスト
            case_id: 案件ID（ログ用）

        Returns:
            Dict[str, Any]: 抽出された入札情報
        """
        try:
            # プロンプトの生成
            prompt = EXTRACT_BID_INFO_PROMPT_TEMPLATE.substitute(query=document_text)

            logger.info(f"LLMによる情報抽出開始: 案件ID={case_id}")

            # OpenAI APIコール
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは政府調達・公共入札の専門アナリストです。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # より決定的な出力のため低めに設定
                max_tokens=4000
            )

            # レスポンスの解析
            extracted_data = json.loads(response.choices[0].message.content)

            # メタデータの追加
            extracted_data['_metadata'] = {
                'extraction_timestamp': datetime.now().isoformat(),
                'model_used': self.model,
                'case_id': case_id,
                'token_usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }

            logger.info(f"情報抽出完了: 案件ID={case_id}, トークン使用量={response.usage.total_tokens}")

            return extracted_data

        except Exception as e:
            logger.error(f"情報抽出エラー: 案件ID={case_id}, エラー={e}")
            return {
                'error': str(e),
                'case_id': case_id,
                'extraction_timestamp': datetime.now().isoformat()
            }

    def extract_from_concatenated_file(self, file_path: str, case_id: str = None) -> Dict[str, Any]:
        """
        結合されたファイルから情報を抽出

        Args:
            file_path: 結合されたテキストファイルのパス
            case_id: 案件ID

        Returns:
            Dict[str, Any]: 抽出された入札情報
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                document_text = f.read()

            return self.extract_bid_information(document_text, case_id)

        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {file_path}, エラー={e}")
            raise


class QualificationParser:
    """資格要件パーサー"""

    def __init__(self):
        # 資格パターン定義
        self.qualification_patterns = {
            # 全省庁統一資格
            'unified_qualification': r'全省庁統一資格\s+([^\s]+)\s+([ABCD]|ランク無し|ランク不明)',

            # 地方整備局系
            'regional_bureau': r'(.+?開発局|.+?地方整備局).*?競争入札参加資格\s+([^\s]+)\s+([ABCD]|ランク無し|ランク不明)',

            # 都道府県・市町村系
            'local_government': r'(.+?県|.+?都|.+?府|.+?市|.+?町|.+?村).*?入札参加資格\s+([^\s]+)\s+([ABCD]|ランク無し|ランク不明)',

            # 省庁別資格
            'ministry_qualification': r'(.+?省|.+?庁).*?競争.*?参加資格\s+([^\s]+)\s+([ABCD]|ランク無し|ランク不明)',

            # 資格不要
            'no_qualification': r'資格不要',

            # 特定業種資格
            'industry_specific': r'(.+?協会|.+?組合|.+?連盟).*?資格'
        }

        # 業種カテゴリマッピング
        self.category_mapping = {
            '物品の製造・販売・買受系': 'manufacturing_sales',
            '物品の製造・販売・買受け系': 'manufacturing_sales',
            '物品の製造': 'manufacturing',
            '物品の販売': 'sales',
            '物品の買受け': 'procurement',
            '役務の提供系': 'service_provision',
            '役務の提供': 'service_provision',
            '建設工事': 'construction',
            '建設関連業務': 'construction_related',
            'コンサルタント': 'consulting',
            '設計': 'design',
            '調査': 'research',
            '測量': 'surveying',
            '種類不明': 'unknown_category'
        }

        # レベルマッピング
        self.level_mapping = {
            'A': 'level_a',
            'B': 'level_b',
            'C': 'level_c',
            'D': 'level_d',
            'ランク無し': 'no_rank',
            'ランク不明': 'unknown_rank'
        }

    def normalize_qualification_text(self, text: str) -> str:
        """資格テキストを正規化"""
        if not text or pd.isna(text):
            return ""

        # 全角・半角統一、余分な空白除去
        text = str(text).replace('　', ' ').strip()
        text = re.sub(r'\s+', ' ', text)

        return text

    def extract_qualifications(self, qualification_text: str) -> List[Dict[str, Any]]:
        """資格要件を抽出・正規化"""
        if not qualification_text or pd.isna(qualification_text):
            return []

        # テキスト正規化
        normalized_text = self.normalize_qualification_text(qualification_text)

        qualifications = []
        lines = normalized_text.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # 各パターンでマッチング
            qualification = self.parse_qualification_line(line, line_num)
            if qualification:
                qualifications.append(qualification)

        return qualifications

    def parse_qualification_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """単一行の資格要件を解析"""

        # 資格不要パターン
        if re.search(self.qualification_patterns['no_qualification'], line):
            return {
                'type': 'no_qualification_required',
                'organization': None,
                'category': None,
                'category_normalized': None,
                'level': None,
                'level_normalized': None,
                'raw_text': line,
                'line_number': line_num,
                'confidence': 1.0
            }

        # 全省庁統一資格パターン
        match = re.search(self.qualification_patterns['unified_qualification'], line)
        if match:
            category = match.group(1).strip()
            level = match.group(2).strip()

            return {
                'type': 'unified_qualification',
                'organization': '全省庁統一資格',
                'category': category,
                'category_normalized': self.category_mapping.get(category, 'other'),
                'level': level,
                'level_normalized': self.level_mapping.get(level, 'unknown'),
                'raw_text': line,
                'line_number': line_num,
                'confidence': 0.95
            }

        # 地方整備局パターン
        match = re.search(self.qualification_patterns['regional_bureau'], line)
        if match:
            organization = match.group(1).strip()
            category = match.group(2).strip()
            level = match.group(3).strip()

            return {
                'type': 'regional_bureau_qualification',
                'organization': organization,
                'category': category,
                'category_normalized': self.category_mapping.get(category, 'other'),
                'level': level,
                'level_normalized': self.level_mapping.get(level, 'unknown'),
                'raw_text': line,
                'line_number': line_num,
                'confidence': 0.9
            }

        # 都道府県・市町村パターン
        match = re.search(self.qualification_patterns['local_government'], line)
        if match:
            organization = match.group(1).strip()
            category = match.group(2).strip()
            level = match.group(3).strip()

            return {
                'type': 'local_government_qualification',
                'organization': organization,
                'category': category,
                'category_normalized': self.category_mapping.get(category, 'other'),
                'level': level,
                'level_normalized': self.level_mapping.get(level, 'unknown'),
                'raw_text': line,
                'line_number': line_num,
                'confidence': 0.85
            }

        # 省庁別資格パターン
        match = re.search(self.qualification_patterns['ministry_qualification'], line)
        if match:
            organization = match.group(1).strip()
            category = match.group(2).strip()
            level = match.group(3).strip()

            return {
                'type': 'ministry_qualification',
                'organization': organization,
                'category': category,
                'category_normalized': self.category_mapping.get(category, 'other'),
                'level': level,
                'level_normalized': self.level_mapping.get(level, 'unknown'),
                'raw_text': line,
                'line_number': line_num,
                'confidence': 0.8
            }

        # 業界団体資格パターン
        match = re.search(self.qualification_patterns['industry_specific'], line)
        if match:
            organization = match.group(1).strip()

            return {
                'type': 'industry_specific_qualification',
                'organization': organization,
                'category': None,
                'category_normalized': 'industry_specific',
                'level': None,
                'level_normalized': None,
                'raw_text': line,
                'line_number': line_num,
                'confidence': 0.7
            }

        # パターンにマッチしない場合
        return {
            'type': 'unknown_qualification',
            'organization': None,
            'category': None,
            'category_normalized': 'unknown',
            'level': None,
            'level_normalized': None,
            'raw_text': line,
            'line_number': line_num,
            'confidence': 0.1
        }

    def get_qualification_summary(self, qualifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """資格要件の要約を作成"""
        if not qualifications:
            return {
                'total_requirements': 0,
                'has_no_qualification_required': False,
                'unified_qualifications': [],
                'regional_qualifications': [],
                'local_qualifications': [],
                'ministry_qualifications': [],
                'industry_qualifications': [],
                'unknown_qualifications': [],
                'required_categories': [],
                'required_levels': [],
                'confidence_score': 0
            }

        # 種別ごとに分類
        unified_quals = [q for q in qualifications if q['type'] == 'unified_qualification']
        regional_quals = [q for q in qualifications if q['type'] == 'regional_bureau_qualification']
        local_quals = [q for q in qualifications if q['type'] == 'local_government_qualification']
        ministry_quals = [q for q in qualifications if q['type'] == 'ministry_qualification']
        industry_quals = [q for q in qualifications if q['type'] == 'industry_specific_qualification']
        unknown_quals = [q for q in qualifications if q['type'] == 'unknown_qualification']

        # 必要なカテゴリとレベルを抽出
        required_categories = list(set([
            q['category_normalized'] for q in qualifications
            if q['category_normalized'] and q['category_normalized'] != 'unknown'
        ]))

        required_levels = list(set([
            q['level_normalized'] for q in qualifications
            if q['level_normalized'] and q['level_normalized'] != 'unknown'
        ]))

        # 信頼度スコア計算
        confidence_scores = [q['confidence'] for q in qualifications]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return {
            'total_requirements': len(qualifications),
            'has_no_qualification_required': any(q['type'] == 'no_qualification_required' for q in qualifications),
            'unified_qualifications': unified_quals,
            'regional_qualifications': regional_quals,
            'local_qualifications': local_quals,
            'ministry_qualifications': ministry_quals,
            'industry_qualifications': industry_quals,
            'unknown_qualifications': unknown_quals,
            'required_categories': required_categories,
            'required_levels': required_levels,
            'confidence_score': round(avg_confidence, 2)
        }


class DataNormalizer:
    """データ正規化クラス"""

    def __init__(self):
        self.business_code_map = {
            "船舶・航空機関連": "B01",
            "保守・点検・整備": "B02",
            "気象・環境・衛生関連サービス": "B03",
            "建設・工事": "B04",
            "ITサービス": "B05",
            "システム開発": "B05",
            "情報処理": "B05",
            "コンサルタント": "B06",
            "調査・検査": "B06",
            "調査・企画": "B06",
            "物品・備品": "B07",
            "機器・設備": "B07",
            "役務": "B08",
            "サービス": "B08",
            "測量": "B09",
            "医療・介護・福祉関連物品": "B10",
            "情報・通信関連物品": "B11",
            "事務機器・パソコン関連機器": "B12",
            "リース・レンタル・賃貸借": "B13",
            "日用品": "B14",
            "自動車・バス・鉄道関連": "B15",
            "その他": "B99"
        }

    def normalize_price(self, price_str: str) -> Optional[float]:
        """金額を正規化"""
        if not price_str or pd.isna(price_str):
            return None

        price_str = str(price_str).replace(',', '').replace('円', '').replace('￥', '')

        if '万' in price_str:
            price_str = price_str.replace('万', '')
            multiplier = 10000
        elif '千' in price_str:
            price_str = price_str.replace('千', '')
            multiplier = 1000
        else:
            multiplier = 1

        numbers = re.findall(r'\d+(?:\.\d+)?', price_str)
        if numbers:
            try:
                return float(numbers[0]) * multiplier
            except ValueError:
                return None
        return None

    def normalize_date(self, date_str: str) -> Optional[str]:
        """日付を正規化"""
        if not date_str or pd.isna(date_str):
            return None

        date_str = str(date_str).strip()
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        ]

        for pattern in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups[0]) == 4:
                    year, month, day = groups
                else:
                    month, day, year = groups

                try:
                    normalized_date = datetime(int(year), int(month), int(day))
                    return normalized_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None

    def normalize_business_types(self, business_str: str) -> List[str]:
        """業種を正規化"""
        if not business_str or pd.isna(business_str):
            return []

        business_types = []
        lines = str(business_str).split('\n')

        for line in lines:
            line = line.strip()
            if line:
                found_code = None
                for business_name, code in self.business_code_map.items():
                    if business_name in line:
                        found_code = code
                        break

                if found_code:
                    business_types.append(found_code)
                else:
                    business_types.append("B99")

        return list(set(business_types))

    def extract_business_types_with_codes(self, business_str: str) -> tuple[List[str], List[str]]:
        """業種名と業種コードを抽出"""
        if not business_str or pd.isna(business_str):
            return [], []

        business_names = []
        business_codes = []
        lines = str(business_str).split('\n')

        for line in lines:
            line = line.strip()
            if line:
                found_code = None
                found_name = None
                for business_name, code in self.business_code_map.items():
                    if business_name in line:
                        found_code = code
                        found_name = business_name
                        break

                if found_code:
                    business_codes.append(found_code)
                    business_names.append(found_name)
                else:
                    business_codes.append("B99")
                    business_names.append(line)

        # Remove duplicates while preserving order
        seen_codes = set()
        unique_codes = []
        unique_names = []
        for code, name in zip(business_codes, business_names):
            if code not in seen_codes:
                seen_codes.add(code)
                unique_codes.append(code)
                unique_names.append(name)

        return unique_names, unique_codes

    def extract_prefecture(self, location_str: str) -> Optional[str]:
        """都道府県を抽出"""
        if not location_str or pd.isna(location_str):
            return None

        prefecture_patterns = [
            r'(北海道)',
            r'(青森県|岩手県|宮城県|秋田県|山形県|福島県)',
            r'(茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県)',
            r'(新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県)',
            r'(三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県)',
            r'(鳥取県|島根県|岡山県|広島県|山口県)',
            r'(徳島県|香川県|愛媛県|高知県)',
            r'(福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
        ]

        for pattern in prefecture_patterns:
            match = re.search(pattern, location_str)
            if match:
                return match.group(1)
        return None


class BiddingDataManager:
    """入札データ管理・DB保存クラス"""

    def __init__(self, db_connection: PostgreSQLConnection):
        self.db = db_connection
        self.qualification_parser = QualificationParser()
        self.data_normalizer = DataNormalizer()
        self.document_extractor = None  # 必要に応じて初期化

    def log_job_execution(self, job_name: str, status: str, **kwargs):
        """ジョブ実行ログを記録"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO job_execution_logs
                        (job_name, status, records_processed, new_records_added,
                         updated_records, error_message, execution_duration_seconds, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        job_name,
                        status,
                        kwargs.get('records_processed', 0),
                        kwargs.get('new_records_added', 0),
                        kwargs.get('updated_records', 0),
                        kwargs.get('error_message'),
                        kwargs.get('execution_duration_seconds'),
                        json.dumps(kwargs.get('metadata', {}))
                    ))
                    conn.commit()
                    logger.info(f"ジョブログ記録: {job_name} - {status}")
        except Exception as e:
            logger.error(f"ジョブログ記録失敗: {e}")

    def upsert_bidding_case(self, data: Dict[str, Any]) -> bool:
        """入札案件データをUPSERT"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # データ準備
                    org = data.get('organization', {})
                    schedule = data.get('schedule', {})
                    qualifications = data.get('qualifications', {})
                    content = data.get('content', {})
                    pricing = data.get('pricing', {})
                    award_info = data.get('award_info', {})
                    processing_info = data.get('processing_info', {})
                    eligibility = data.get('eligibility', {})
                    documents = data.get('documents', {})

                    cursor.execute("""
                        INSERT INTO bidding_cases (
                            case_id, case_name, search_condition, bidding_format, case_url,
                            org_name, org_location, org_prefecture, delivery_location,
                            announcement_date, bidding_date, document_submission_date,
                            briefing_date, award_announcement_date, award_date,
                            qualifications_raw, qualifications_parsed, qualifications_summary,
                            business_types_raw, business_types_normalized, business_type, business_type_code,
                            overview, remarks,
                            planned_price_raw, planned_price_normalized, planned_unit_price,
                            award_price_raw, award_price_normalized, award_unit_price, main_price,
                            winning_company, winning_company_address, winning_reason,
                            winning_score, award_remarks, bid_result_details, unsuccessful_bid,
                            processed_at, qualification_confidence,
                            is_eligible_to_bid, eligibility_reason, eligibility_details,
                            document_directory, document_count, downloaded_count, documents
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        ON CONFLICT (case_id) DO UPDATE SET
                            case_name = EXCLUDED.case_name,
                            search_condition = EXCLUDED.search_condition,
                            bidding_format = EXCLUDED.bidding_format,
                            case_url = EXCLUDED.case_url,
                            org_name = EXCLUDED.org_name,
                            org_location = EXCLUDED.org_location,
                            org_prefecture = EXCLUDED.org_prefecture,
                            delivery_location = EXCLUDED.delivery_location,
                            announcement_date = EXCLUDED.announcement_date,
                            bidding_date = EXCLUDED.bidding_date,
                            document_submission_date = EXCLUDED.document_submission_date,
                            briefing_date = EXCLUDED.briefing_date,
                            award_announcement_date = EXCLUDED.award_announcement_date,
                            award_date = EXCLUDED.award_date,
                            qualifications_raw = EXCLUDED.qualifications_raw,
                            qualifications_parsed = EXCLUDED.qualifications_parsed,
                            qualifications_summary = EXCLUDED.qualifications_summary,
                            business_types_raw = EXCLUDED.business_types_raw,
                            business_types_normalized = EXCLUDED.business_types_normalized,
                            business_type = EXCLUDED.business_type,
                            business_type_code = EXCLUDED.business_type_code,
                            overview = EXCLUDED.overview,
                            remarks = EXCLUDED.remarks,
                            planned_price_raw = EXCLUDED.planned_price_raw,
                            planned_price_normalized = EXCLUDED.planned_price_normalized,
                            planned_unit_price = EXCLUDED.planned_unit_price,
                            award_price_raw = EXCLUDED.award_price_raw,
                            award_price_normalized = EXCLUDED.award_price_normalized,
                            award_unit_price = EXCLUDED.award_unit_price,
                            main_price = EXCLUDED.main_price,
                            winning_company = EXCLUDED.winning_company,
                            winning_company_address = EXCLUDED.winning_company_address,
                            winning_reason = EXCLUDED.winning_reason,
                            winning_score = EXCLUDED.winning_score,
                            award_remarks = EXCLUDED.award_remarks,
                            bid_result_details = EXCLUDED.bid_result_details,
                            unsuccessful_bid = EXCLUDED.unsuccessful_bid,
                            processed_at = EXCLUDED.processed_at,
                            qualification_confidence = EXCLUDED.qualification_confidence,
                            is_eligible_to_bid = EXCLUDED.is_eligible_to_bid,
                            eligibility_reason = EXCLUDED.eligibility_reason,
                            eligibility_details = EXCLUDED.eligibility_details,
                            document_directory = EXCLUDED.document_directory,
                            document_count = EXCLUDED.document_count,
                            downloaded_count = EXCLUDED.downloaded_count,
                            documents = EXCLUDED.documents,
                            updated_at = NOW()
                    """, (
                        data.get('case_id'),
                        data.get('case_name'),
                        data.get('search_condition'),
                        data.get('bidding_format'),
                        data.get('case_url'),
                        org.get('name'),
                        org.get('location'),
                        org.get('prefecture'),
                        org.get('delivery_location'),
                        schedule.get('announcement_date'),
                        schedule.get('bidding_date'),
                        schedule.get('document_submission_date'),
                        schedule.get('briefing_date'),
                        schedule.get('award_announcement_date'),
                        schedule.get('award_date'),
                        qualifications.get('requirements_raw'),
                        json.dumps(qualifications.get('requirements_parsed')) if qualifications.get('requirements_parsed') else None,
                        json.dumps(qualifications.get('requirements_summary')) if qualifications.get('requirements_summary') else None,
                        qualifications.get('business_types_raw'),
                        qualifications.get('business_types_normalized'),
                        qualifications.get('business_type'),
                        qualifications.get('business_type_code'),
                        content.get('overview'),
                        content.get('remarks'),
                        pricing.get('planned_price_raw'),
                        pricing.get('planned_price_normalized'),
                        pricing.get('planned_unit_price'),
                        pricing.get('award_price_raw'),
                        pricing.get('award_price_normalized'),
                        pricing.get('award_unit_price'),
                        pricing.get('main_price'),
                        award_info.get('winning_company'),
                        award_info.get('winning_company_address'),
                        award_info.get('winning_reason'),
                        award_info.get('winning_score'),
                        award_info.get('award_remarks'),
                        json.dumps(award_info.get('bid_result_details')) if award_info.get('bid_result_details') else None,
                        award_info.get('unsuccessful_bid'),
                        processing_info.get('processed_at'),
                        processing_info.get('qualification_confidence'),
                        eligibility.get('is_eligible'),
                        eligibility.get('reason'),
                        json.dumps(eligibility.get('details')) if eligibility.get('details') else None,
                        documents.get('directory'),
                        documents.get('count', 0),
                        documents.get('downloaded_count', 0),
                        json.dumps(documents.get('details', [])) if documents.get('details') else '[]'
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"案件保存失敗 {data.get('case_id')}: {e}")
            return False

    def process_csv_data(self, csv_path: str) -> Dict[str, int]:
        """CSVデータを処理してデータベースに保存"""
        start_time = time.time()
        stats = {
            'processed': 0,
            'saved': 0,
            'failed': 0,
            'skipped': 0,
            'eligible_count': 0,  # 入札可能案件数
            'ineligible_count': 0  # 入札不可案件数
        }

        try:
            # CSVファイル読み込み
            logger.info(f"CSV読み込み開始: {csv_path}")
            try:
                df = pd.read_csv(csv_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='shift_jis')

            logger.info(f"読み込み完了: {len(df)}件")

            # ジョブ開始ログ
            self.log_job_execution('csv_data_import', 'running', metadata={'file_path': csv_path})

            for idx, row in df.iterrows():
                try:
                    # case_idの確認
                    if pd.isna(row.get('案件ID')):
                        logger.warning(f"案件ID不明のためスキップ: 行{idx+1}")
                        stats['skipped'] += 1
                        continue

                    case_id = int(row['案件ID'])

                    # 基本データ正規化
                    normalized_data = self.normalize_basic_data(row)

                    # 資格要件の正規化
                    qualification_text = row.get('入札資格', '') if not pd.isna(row.get('入札資格')) else ""
                    qualifications = self.qualification_parser.extract_qualifications(qualification_text)
                    qualification_summary = self.qualification_parser.get_qualification_summary(qualifications)

                    # 入札可否判定はLLMで行うため、ここでは仮の値を設定
                    # 実際の判定はllm.pyで実施
                    is_eligible = None  # LLMで判定予定
                    eligibility_reason = "LLM判定待ち"
                    eligibility_details = []

                    # 統計更新
                    if is_eligible:
                        stats['eligible_count'] += 1
                        logger.info(f"入札可能: {case_id} - {row.get('案件名')} - {eligibility_reason}")
                    else:
                        stats['ineligible_count'] += 1
                        logger.info(f"入札不可: {case_id} - {row.get('案件名')} - {eligibility_reason}")

                    # データ構造作成
                    processed_data = {
                        'case_id': case_id,
                        'case_name': row.get('案件名') if not pd.isna(row.get('案件名')) else None,
                        'search_condition': row.get('検索条件名') if not pd.isna(row.get('検索条件名')) else None,
                        'bidding_format': row.get('入札形式') if not pd.isna(row.get('入札形式')) else None,
                        'case_url': row.get('案件概要URL') if not pd.isna(row.get('案件概要URL')) else None,

                        'organization': {
                            'name': row.get('機関') if not pd.isna(row.get('機関')) else None,
                            'location': row.get('機関所在地') if not pd.isna(row.get('機関所在地')) else None,
                            'prefecture': normalized_data['prefecture'],
                            'delivery_location': row.get('履行/納品場所') if not pd.isna(row.get('履行/納品場所')) else None,
                        },

                        'schedule': {
                            'announcement_date': normalized_data['announcement_date'],
                            'bidding_date': normalized_data['bidding_date'],
                            'document_submission_date': normalized_data['document_submission_date'],
                            'briefing_date': self.data_normalizer.normalize_date(row.get('説明会日')),
                            'award_announcement_date': normalized_data['award_announcement_date'],
                            'award_date': normalized_data['award_date']
                        },

                        'qualifications': {
                            'requirements_raw': qualification_text,
                            'requirements_parsed': qualifications,
                            'requirements_summary': qualification_summary,
                            'business_types_raw': row.get('業種') if not pd.isna(row.get('業種')) else None,
                            'business_types_normalized': normalized_data['business_types'],
                            'business_type': normalized_data['business_type_names'],
                            'business_type_code': normalized_data['business_type_codes']
                        },

                        'content': {
                            'overview': row.get('案件概要') if not pd.isna(row.get('案件概要')) else None,
                            'remarks': row.get('案件備考') if not pd.isna(row.get('案件備考')) else None,
                        },

                        'pricing': {
                            'planned_price_raw': row.get('予定価格') if not pd.isna(row.get('予定価格')) else None,
                            'planned_price_normalized': normalized_data['normalized_planned_price'],
                            'planned_unit_price': row.get('予定単価') if not pd.isna(row.get('予定単価')) else None,
                            'award_price_raw': row.get('落札価格') if not pd.isna(row.get('落札価格')) else None,
                            'award_price_normalized': normalized_data['normalized_award_price'],
                            'award_unit_price': row.get('落札単価') if not pd.isna(row.get('落札単価')) else None,
                            'main_price': normalized_data['normalized_price']
                        },

                        'award_info': {
                            'winning_company': row.get('落札会社名') if not pd.isna(row.get('落札会社名')) else None,
                            'winning_company_address': row.get('落札会社住所') if not pd.isna(row.get('落札会社住所')) else None,
                            'winning_reason': row.get('落札理由') if not pd.isna(row.get('落札理由')) else None,
                            'winning_score': row.get('落札評点') if not pd.isna(row.get('落札評点')) else None,
                            'award_remarks': row.get('落札結果備考') if not pd.isna(row.get('落札結果備考')) else None,
                            'bid_result_details': row.get('入札結果詳細') if not pd.isna(row.get('入札結果詳細')) else None,
                            'unsuccessful_bid': row.get('不調') if not pd.isna(row.get('不調')) else None
                        },

                        'processing_info': {
                            'processed_at': datetime.now().isoformat(),
                            'qualification_confidence': qualification_summary['confidence_score']
                        },

                        'eligibility': {
                            'is_eligible': is_eligible,
                            'reason': eligibility_reason,
                            'details': eligibility_details
                        },

                        'documents': {
                            'directory': row.get('文書ディレクトリ') if not pd.isna(row.get('文書ディレクトリ')) else None,
                            'count': int(row.get('文書数', 0)) if not pd.isna(row.get('文書数')) else 0,
                            'downloaded_count': int(row.get('ダウンロード済み数', 0)) if not pd.isna(row.get('ダウンロード済み数')) else 0,
                            'details': json.loads(row.get('文書情報', '[]')) if not pd.isna(row.get('文書情報')) else []
                        }
                    }

                    # データベースに保存
                    if self.upsert_bidding_case(processed_data):
                        stats['saved'] += 1
                        logger.info(f"保存完了: {case_id} - {processed_data['case_name']}")
                    else:
                        stats['failed'] += 1

                    stats['processed'] += 1

                except Exception as e:
                    logger.error(f"行処理エラー {idx+1}: {e}")
                    stats['failed'] += 1

            # 処理完了
            execution_time = int(time.time() - start_time)

            self.log_job_execution(
                'csv_data_import',
                'success',
                records_processed=stats['processed'],
                new_records_added=stats['saved'],
                execution_duration_seconds=execution_time,
                metadata=stats
            )

            logger.info(f"CSV処理完了: {stats}")
            return stats

        except Exception as e:
            execution_time = int(time.time() - start_time)
            error_msg = str(e)

            self.log_job_execution(
                'csv_data_import',
                'failed',
                error_message=error_msg,
                execution_duration_seconds=execution_time,
                metadata=stats
            )

            logger.error(f"CSV処理失敗: {e}")
            raise

    def normalize_basic_data(self, row: pd.Series) -> Dict[str, Any]:
        """基本データの正規化"""
        # 価格の正規化
        normalized_price = self.data_normalizer.normalize_price(row.get('落札価格'))
        if normalized_price is None:
            normalized_price = self.data_normalizer.normalize_price(row.get('予定価格'))

        # 業種情報の抽出
        business_names, business_codes = self.data_normalizer.extract_business_types_with_codes(row.get('業種'))

        return {
            'announcement_date': self.data_normalizer.normalize_date(row.get('案件公示日')),
            'bidding_date': self.data_normalizer.normalize_date(row.get('入札日')),
            'document_submission_date': self.data_normalizer.normalize_date(row.get('資料等提出日')),
            'award_announcement_date': self.data_normalizer.normalize_date(row.get('落札結果公示日')),
            'award_date': self.data_normalizer.normalize_date(row.get('落札日(or 契約締結日)')),
            'normalized_price': normalized_price,
            'normalized_planned_price': self.data_normalizer.normalize_price(row.get('予定価格')),
            'normalized_award_price': self.data_normalizer.normalize_price(row.get('落札価格')),
            'business_types': self.data_normalizer.normalize_business_types(row.get('業種')),
            'business_type_names': business_names,
            'business_type_codes': business_codes,
            'prefecture': self.data_normalizer.extract_prefecture(row.get('機関所在地'))
        }

    def initialize_document_extractor(self, openai_api_key: str = None):
        """LLM文書抽出器を初期化"""
        if self.document_extractor is None:
            self.document_extractor = BidDocumentExtractor(openai_api_key)

    def update_case_with_llm_extraction(self, case_id: int, extracted_data: Dict[str, Any]) -> bool:
        """LLM抽出結果でケースを更新"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # LLM抽出データ専用のカラムを追加（ALTER TABLEが必要な場合）
                    # まず既存のカラムを確認
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name='bidding_cases' AND column_name='llm_extracted_data'
                    """)

                    if not cursor.fetchone():
                        # カラムが存在しない場合は追加
                        cursor.execute("""
                            ALTER TABLE bidding_cases
                            ADD COLUMN IF NOT EXISTS llm_extracted_data JSONB,
                            ADD COLUMN IF NOT EXISTS llm_extraction_timestamp TIMESTAMP WITH TIME ZONE
                        """)
                        conn.commit()

                    # 抽出データを更新
                    cursor.execute("""
                        UPDATE bidding_cases
                        SET
                            llm_extracted_data = %s,
                            llm_extraction_timestamp = %s,
                            updated_at = NOW()
                        WHERE case_id = %s
                    """, (
                        json.dumps(extracted_data),
                        datetime.now(),
                        case_id
                    ))

                    # 抽出データから重要な情報を既存カラムにも反映
                    if 'error' not in extracted_data:
                        # 日付情報の更新
                        dates = extracted_data.get('important_dates', {})
                        if dates:
                            updates = []
                            params = []

                            if dates.get('announcement_date') and dates['announcement_date'] != 'null':
                                updates.append("announcement_date = %s")
                                params.append(dates['announcement_date'])

                            if dates.get('submission_deadline') and dates['submission_deadline'] != 'null':
                                updates.append("bidding_date = %s")
                                params.append(dates['submission_deadline'].split(' ')[0])  # 日付部分のみ

                            if updates:
                                params.append(case_id)
                                cursor.execute(f"""
                                    UPDATE bidding_cases
                                    SET {', '.join(updates)}
                                    WHERE case_id = %s
                                """, params)

                        # 資格要件の更新
                        qual_req = extracted_data.get('qualification_requirements', {})
                        if qual_req:
                            unified = qual_req.get('unified_qualification', {})
                            if unified.get('rank'):
                                # 既存の資格要件解析結果と統合
                                cursor.execute("""
                                    UPDATE bidding_cases
                                    SET qualifications_summary =
                                        COALESCE(qualifications_summary, '{}'::jsonb) || %s::jsonb
                                    WHERE case_id = %s
                                """, (
                                    json.dumps({'llm_extracted_rank': unified['rank']}),
                                    case_id
                                ))

                    conn.commit()
                    logger.info(f"LLM抽出データ更新完了: case_id={case_id}")
                    return True

        except Exception as e:
            logger.error(f"LLM抽出データ更新エラー: case_id={case_id}, error={e}")
            return False

    def process_case_documents(self, case_id: int, document_directory: str,
                              openai_api_key: str = None) -> Dict[str, Any]:
        """
        案件の文書を処理してLLM抽出を実行

        Args:
            case_id: 案件ID
            document_directory: 文書ディレクトリパス
            openai_api_key: OpenAI APIキー

        Returns:
            Dict[str, Any]: 処理結果
        """
        stats = {
            'case_id': case_id,
            'concatenated': False,
            'extracted': False,
            'saved': False,
            'error': None
        }

        try:
            # LLM抽出器の初期化
            self.initialize_document_extractor(openai_api_key)

            # 文書の結合
            logger.info(f"文書結合開始: case_id={case_id}, directory={document_directory}")
            concat_file = concatenate_files(
                document_directory,
                output_file=f"concat_{case_id}.txt",
                exclude_patterns=['.git', '__pycache__', '.pyc', '.log', '.jpg', '.jpeg', '.png']
            )
            stats['concatenated'] = True

            # LLM抽出
            logger.info(f"LLM情報抽出開始: case_id={case_id}")
            extracted_data = self.document_extractor.extract_from_concatenated_file(
                concat_file,
                str(case_id)
            )
            stats['extracted'] = True

            # データベース更新
            if self.update_case_with_llm_extraction(case_id, extracted_data):
                stats['saved'] = True
                logger.info(f"処理完了: case_id={case_id}")
            else:
                stats['error'] = "データベース更新失敗"

            # 一時ファイルの削除（オプション）
            try:
                os.remove(concat_file)
            except:
                pass

        except Exception as e:
            stats['error'] = str(e)
            logger.error(f"文書処理エラー: case_id={case_id}, error={e}")

        return stats


def process_llm_extraction():
    """LLM文書抽出処理のメイン関数（Airflow用）"""
    logger.info("LLM文書抽出処理開始")

    stats = {
        'total_cases': 0,
        'processed_cases': 0,
        'success_cases': 0,
        'failed_cases': 0,
        'errors': []
    }

    try:
        # データベース接続
        db_connection = PostgreSQLConnection()

        # 接続テスト
        if not db_connection.test_connection():
            logger.error("データベース接続失敗")
            raise Exception("Database connection failed")

        # データ管理クラス初期化
        manager = BiddingDataManager(db_connection)

        # 未処理案件の取得
        with db_connection.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT case_id, document_directory
                    FROM bidding_cases
                    WHERE
                        llm_extracted_data IS NULL
                        AND document_directory IS NOT NULL
                        AND document_count > 0
                    ORDER BY created_at DESC
                    LIMIT 50  -- バッチサイズ
                """)
                cases = cursor.fetchall()

        stats['total_cases'] = len(cases)
        logger.info(f"処理対象案件数: {stats['total_cases']}")

        # 各案件の処理
        for case_id, doc_dir in cases:
            try:
                logger.info(f"処理開始: case_id={case_id}")
                result = manager.process_case_documents(
                    case_id=case_id,
                    document_directory=doc_dir
                )

                stats['processed_cases'] += 1
                if result.get('saved'):
                    stats['success_cases'] += 1
                    logger.info(f"処理成功: case_id={case_id}")
                else:
                    stats['failed_cases'] += 1
                    stats['errors'].append({
                        'case_id': case_id,
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                stats['failed_cases'] += 1
                stats['errors'].append({
                    'case_id': case_id,
                    'error': str(e)
                })
                logger.error(f"案件処理エラー: case_id={case_id}, error={e}")

        # ジョブ実行ログの記録
        manager.log_job_execution(
            'llm_document_extraction',
            'success' if stats['failed_cases'] == 0 else 'partial_success',
            records_processed=stats['processed_cases'],
            new_records_added=stats['success_cases'],
            metadata=stats
        )

        logger.info("=" * 60)
        logger.info("LLM抽出処理結果:")
        logger.info(f"  対象案件数: {stats['total_cases']}")
        logger.info(f"  処理済み: {stats['processed_cases']}")
        logger.info(f"  成功: {stats['success_cases']}")
        logger.info(f"  失敗: {stats['failed_cases']}")
        logger.info("=" * 60)

        return stats

    except Exception as e:
        logger.error(f"LLM抽出処理エラー: {e}")
        raise


def main():
    """メイン実行関数"""
    logger.info("入札データ処理・DB保存開始")

    try:
        # データベース接続
        db_connection = PostgreSQLConnection()

        # 接続テスト
        if not db_connection.test_connection():
            logger.error("データベース接続失敗")
            sys.exit(1)

        # データ管理クラス初期化
        manager = BiddingDataManager(db_connection)

        # CSVファイルパス（実際のパスに変更してください）
        csv_path = CSV_FILE_PATH

        if not os.path.exists(csv_path):
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            sys.exit(1)

        # CSV処理実行
        results = manager.process_csv_data(csv_path)

        logger.info("=" * 60)
        logger.info("処理結果:")
        logger.info(f"  処理件数: {results['processed']}")
        logger.info(f"  保存成功: {results['saved']}")
        logger.info(f"  保存失敗: {results['failed']}")
        logger.info(f"  スキップ: {results['skipped']}")
        logger.info(f"  入札可能案件: {results['eligible_count']}")
        logger.info(f"  入札不可案件: {results['ineligible_count']}")
        logger.info("=" * 60)

        print("✅ CSV処理・DB保存が完了しました")

    except Exception as e:
        logger.error(f"処理エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
