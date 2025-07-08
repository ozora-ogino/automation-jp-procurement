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

from sql_connection import PostgreSQLConnection
from consts import CSV_FILE_PATH

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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


class BiddingEligibilityChecker:
    """入札資格判定クラス"""

    def __init__(self):
        # 入札可能なランク（D、ランク無し、ランク不明）
        self.eligible_levels = ['level_d', 'no_rank', 'unknown_rank']

    def check_eligibility(self, qualifications: List[Dict[str, Any]],
                         qualification_summary: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """
        入札可能かどうかを判定

        Returns:
            Tuple[bool, str, List[str]]: (入札可否, 判定理由, 詳細理由リスト)
        """

        # 資格不要の場合は入札可能
        if qualification_summary.get('has_no_qualification_required'):
            return True, "資格不要案件のため入札可能", ["資格要件: 不要"]

        # 資格要件が空の場合は入札不可
        if not qualifications:
            return False, "資格要件が不明のため入札不可", ["資格要件が記載されていません"]

        eligible_qualifications = []
        ineligible_qualifications = []

        for qual in qualifications:
            level = qual.get('level_normalized')

            # レベルが不明な資格は除外
            if not level:
                continue

            # 各資格要件をチェック
            if level in self.eligible_levels:
                eligible_qualifications.append(
                    f"✓ {qual.get('organization', '不明')} - {qual.get('category', '不明')} - {qual.get('level', '不明')}"
                )
            else:
                ineligible_qualifications.append(
                    f"✗ {qual.get('organization', '不明')} - {qual.get('category', '不明')} - {qual.get('level', '不明')}"
                )

        # 判定結果
        if ineligible_qualifications:
            # 入札不可能な資格要件が一つでもある場合
            reason = f"入札不可（要求ランクが高い: {len(ineligible_qualifications)}件）"
            details = ineligible_qualifications + eligible_qualifications
            return False, reason, details
        elif eligible_qualifications:
            # すべての資格要件が入札可能な場合
            reason = f"入札可能（すべての要件を満たす: {len(eligible_qualifications)}件）"
            return True, reason, eligible_qualifications
        else:
            # 判定不能な場合
            return False, "資格要件の解析に失敗", ["資格要件の形式が認識できません"]


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
        self.eligibility_checker = BiddingEligibilityChecker()

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
                            is_eligible_to_bid, eligibility_reason, eligibility_details
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                        json.dumps(eligibility.get('details')) if eligibility.get('details') else None
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

                    # 入札可否判定
                    is_eligible, eligibility_reason, eligibility_details = self.eligibility_checker.check_eligibility(
                        qualifications, qualification_summary
                    )

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
