#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from data.models import BiddingCase, JobExecutionLog, JobStatus
from db.repositories import BiddingCaseRepository, JobExecutionLogRepository
from utils.file_service import FileService

logger = logging.getLogger(__name__)


class BiddingProcessingService:
    """Service layer for bidding case processing business logic"""

    def __init__(self,
                 case_repository: BiddingCaseRepository,
                 log_repository: JobExecutionLogRepository,
                 file_service: FileService):
        self.case_repo = case_repository
        self.log_repo = log_repository
        self.file_service = file_service

    def process_csv_data(self, csv_path: str) -> Tuple[int, int, int]:
        """
        Process CSV data and update database.
        Returns (total_records, new_records, updated_records)
        """
        start_time = datetime.now()
        total_records = 0
        new_records = 0
        updated_records = 0
        error_message = None

        try:
            # Read CSV data
            data = self.file_service.read_csv(csv_path)
            total_records = len(data)

            logger.info(f"Processing {total_records} records from CSV")

            # Process each record
            for _, row in data.iterrows():
                case = self._create_case_from_csv_row(row)
                success, is_new = self.case_repo.upsert_bidding_case(case.to_dict())

                if success:
                    if is_new:
                        new_records += 1
                    else:
                        updated_records += 1

            # Log successful execution
            self._log_job_execution(
                job_name="csv_processing",
                status=JobStatus.SUCCESS.value,
                records_processed=total_records,
                new_records_added=new_records,
                updated_records=updated_records,
                execution_duration_seconds=(datetime.now() - start_time).total_seconds()
            )

            logger.info(f"CSV processing completed: {new_records} new, {updated_records} updated")

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error processing CSV: {error_message}")

            # Log failed execution
            self._log_job_execution(
                job_name="csv_processing",
                status=JobStatus.FAILURE.value,
                error_message=error_message,
                execution_duration_seconds=(datetime.now() - start_time).total_seconds()
            )

            raise

        return total_records, new_records, updated_records

    def find_cases_for_llm_extraction(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Find cases that need LLM extraction"""
        return self.case_repo.find_unprocessed_cases(limit)

    def update_case_llm_extraction(self, case_id: str, extracted_data: Dict[str, Any]) -> bool:
        """Update case with LLM extracted data"""
        return self.case_repo.update_llm_extraction(case_id, extracted_data)

    def search_cases(self, search_text: str, limit: int = 20) -> List[BiddingCase]:
        """Search for cases by text"""
        results = self.case_repo.search_by_text(search_text, limit)
        return [BiddingCase.from_dict(result) for result in results]

    def get_case_details(self, case_id: str) -> Optional[BiddingCase]:
        """Get detailed information for a specific case"""
        result = self.case_repo.get_case_by_id(case_id)
        return BiddingCase.from_dict(result) if result else None

    def _create_case_from_csv_row(self, row: Dict[str, Any]) -> BiddingCase:
        """Create BiddingCase instance from CSV row"""
        # Map CSV columns to BiddingCase fields
        # Note: CSV uses Japanese column names
        case = BiddingCase(
            case_id=str(row.get('案件ID', '')),  # Convert to string
            case_name=row.get('案件名', ''),
            organization_name=row.get('機関', ''),  # Changed from '機関名' to '機関'
            department_name=row.get('機関所在地'),  # Map org_location to department_name
            procurement_type=row.get('入札形式'),  # Changed from '調達方式' to '入札形式'
            details=row.get('案件概要', ''),  # Changed from '詳細' to '案件概要'
            delivery_location=row.get('履行/納品場所'),  # Changed from '納入場所'
            bid_opening_location=row.get('開札場所'),
            contact_point=row.get('問合せ先'),
            qualification_info=row.get('入札資格'),  # Changed from '資格情報' to '入札資格'
            remarks=row.get('案件備考'),  # Changed from '備考' to '案件備考'
            attachment_info=row.get('添付情報'),
            related_info_url=row.get('関連情報URL'),
            anken_url=row.get('案件概要URL'),  # Changed from '案件URL' to '案件概要URL'
            document_directory=row.get('文書保存先'),
            document_count=int(row.get('文書数', 0)) if row.get('文書数') else 0,
            # Add missing fields
            business_types_raw=row.get('業種'),  # Add business types
            search_condition=row.get('検索条件名'),  # Add search condition
            planned_price_raw=row.get('予定価格'),  # Add planned price
            award_price_raw=row.get('落札価格'),  # Add award price
            winning_company=row.get('落札会社名'),  # Add winning company
            winning_company_address=row.get('落札会社住所'),  # Add winning company address
            winning_reason=row.get('落札理由'),  # Add winning reason
            award_remarks=row.get('落札結果備考'),  # Add award remarks
            unsuccessful_bid=row.get('不調')  # Add unsuccessful bid
        )
        
        # Debug logging
        if case.document_directory or case.document_count > 0:
            logger.info(f"CSV row for case {case.case_id} has document_directory={case.document_directory}, document_count={case.document_count}")

        # Parse dates - use correct CSV column names from preprocessor.py
        date_fields = {
            'publication_date': '案件公示日',  # Changed from '公開日'
            'deadline_date': '資料等提出日',  # Changed from '締切日' - this is the document submission deadline
            'bid_opening_date': '入札日',  # Changed from '開札日時' - this is the bidding date
            'briefing_date': '説明会日',  # Add briefing date
            'award_announcement_date': '落札結果公示日',  # Add award announcement date
            'award_date': '落札日(or 契約締結日)'  # Add award date
        }

        for field_name, csv_column in date_fields.items():
            date_str = row.get(csv_column)
            if date_str:
                try:
                    # Handle various date formats
                    if '/' in date_str:
                        # Handle YYYY/MM/DD format
                        setattr(case, field_name, datetime.strptime(date_str, '%Y/%m/%d'))
                    else:
                        setattr(case, field_name, datetime.fromisoformat(date_str))
                except:
                    logger.debug(f"Could not parse date for {field_name}: {date_str}")
                    pass  # Skip invalid dates

        return case

    def _log_job_execution(self, job_name: str, status: str, **kwargs):
        """Log job execution details"""
        self.log_repo.create_log(job_name, status, **kwargs)
