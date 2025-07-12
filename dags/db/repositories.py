#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

from db.connection import PostgreSQLConnection

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common database operations"""

    def __init__(self, db_connection: PostgreSQLConnection):
        self.db = db_connection

    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic cleanup"""
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                yield cursor
                conn.commit()


class BiddingCaseRepository(BaseRepository):
    """Repository for bidding case operations"""

    def find_unprocessed_cases(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Find cases that haven't been processed with LLM extraction"""
        with self.get_cursor() as cursor:
            # First, let's check what we have in the database
            cursor.execute("""
                SELECT COUNT(*)
                FROM bidding_cases
                WHERE document_directory IS NOT NULL
            """)
            total_with_dir = cursor.fetchone()[0]
            logger.info(f"Total cases with document_directory: {total_with_dir}")

            cursor.execute("""
                SELECT COUNT(*)
                FROM bidding_cases
                WHERE document_directory IS NOT NULL AND document_count > 0
            """)
            total_with_docs = cursor.fetchone()[0]
            logger.info(f"Total cases with documents: {total_with_docs}")

            cursor.execute("""
                SELECT COUNT(*)
                FROM bidding_cases
                WHERE llm_extracted_data IS NULL AND document_directory IS NOT NULL AND document_count > 0
            """)
            total_unprocessed = cursor.fetchone()[0]
            logger.info(f"Total unprocessed cases: {total_unprocessed}")

            # Now get the actual cases
            cursor.execute("""
                SELECT case_id, document_directory, document_count
                FROM bidding_cases
                WHERE
                    llm_extracted_data IS NULL
                    AND document_directory IS NOT NULL
                    AND document_count > 0
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))

            results = cursor.fetchall()
            cases = [
                {"case_id": row[0], "document_directory": row[1], "document_count": row[2]}
                for row in results
            ]
            logger.info(f"Returning {len(cases)} cases for LLM extraction")
            return cases

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get a single case by ID"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM bidding_cases WHERE case_id = %s
            """, (case_id,))

            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def upsert_bidding_case(self, case_data: Dict[str, Any]) -> Tuple[bool, bool]:
        """
        Upsert a bidding case record.
        Returns (success, is_new_record)
        """
        # Map model fields to database columns
        field_mapping = {
            'case_id': 'case_id',
            'case_name': 'case_name',
            'organization_name': 'org_name',  # Map to database column
            'department_name': 'org_location',  # Note: database doesn't have department_name
            'procurement_type': 'bidding_format',  # Map to database column
            'details': 'overview',  # Map to database column (was case_summary)
            'delivery_location': 'delivery_location',
            'bid_opening_location': 'org_location',  # Note: database doesn't have bid_opening_location
            'contact_point': 'org_location',  # Note: database doesn't have contact_point
            'qualification_info': 'qualifications_raw',  # Map to database column
            'remarks': 'remarks',  # Map to database column (was case_notes)
            'attachment_info': 'documents',  # Map to JSONB column
            'documents': 'documents',  # Direct mapping for documents
            'related_info_url': 'case_url',  # Note: database doesn't have related_info_url
            'anken_url': 'case_url',  # Map to database column
            'document_directory': 'document_directory',  # Map to database column (was document_path)
            'document_count': 'document_count',  # Map to database column (was doc_count)
            'downloaded_count': 'downloaded_count',  # Map to database column
            'publication_date': 'announcement_date',  # Map to database column
            'deadline_date': 'document_submission_date',  # Map to database column
            'delivery_deadline': 'award_date',  # Note: database doesn't have delivery_deadline
            'bid_opening_date': 'bidding_date',  # Map to database column
            'briefing_date': 'briefing_date',  # Map to database column
            'award_announcement_date': 'award_announcement_date',  # Map to database column
            'award_date': 'award_date',  # Map to database column
            'business_types_raw': 'business_types_raw',  # Map to database column
            'search_condition': 'search_condition',  # Map to database column
            'planned_price_raw': 'planned_price_raw',  # Map to database column
            'award_price_raw': 'award_price_raw',  # Map to database column
            'winning_company': 'winning_company',  # Map to database column
            'winning_company_address': 'winning_company_address',  # Map to database column
            'winning_reason': 'winning_reason',  # Map to database column
            'award_remarks': 'award_remarks',  # Map to database column
            'unsuccessful_bid': 'unsuccessful_bid'  # Map to database column
        }

        # Convert model data to database data
        db_data = {}
        for model_field, db_field in field_mapping.items():
            if model_field in case_data and case_data[model_field] is not None:
                value = case_data[model_field]
                # Convert lists/dicts to JSON for JSONB fields
                if db_field in ['documents', 'qualifications_parsed', 'qualifications_summary',
                               'eligibility_details', 'bid_result_details', 'llm_extracted_data']:
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value, ensure_ascii=False)
                db_data[db_field] = value

        # Log document-related fields for debugging
        if 'document_directory' in db_data or 'document_count' in db_data:
            logger.info(f"Upserting case {case_data.get('case_id')} with document_directory={db_data.get('document_directory')}, document_count={db_data.get('document_count')}")

        # Ensure case_id is numeric
        if 'case_id' in db_data:
            try:
                db_data['case_id'] = int(db_data['case_id'])
            except (ValueError, TypeError):
                logger.error(f"Invalid case_id: {db_data['case_id']}")
                return (False, False)

        with self.get_cursor() as cursor:
            # Check if case exists
            cursor.execute(
                "SELECT case_id FROM bidding_cases WHERE case_id = %s",
                (db_data['case_id'],)
            )
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing record
                update_fields = []
                update_values = []

                for field, value in db_data.items():
                    if field != 'case_id':
                        update_fields.append(f"{field} = %s")
                        update_values.append(value)

                # Add processed_at if not already set
                update_fields.append("processed_at = COALESCE(processed_at, CURRENT_TIMESTAMP)")

                update_values.append(db_data['case_id'])

                query = f"""
                    UPDATE bidding_cases
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE case_id = %s
                """

                cursor.execute(query, update_values)
                return (True, False)
            else:
                # Insert new record with processed_at
                fields = list(db_data.keys())
                fields.append('processed_at')
                placeholders = ['%s'] * len(db_data) + ['CURRENT_TIMESTAMP']

                query = f"""
                    INSERT INTO bidding_cases ({', '.join(fields)})
                    VALUES ({', '.join(placeholders)})
                """

                cursor.execute(query, list(db_data.values()))
                return (True, True)

    def update_llm_extraction(self, case_id: str, extracted_data: Dict[str, Any]) -> bool:
        """Update case with LLM extracted data"""
        # Convert case_id to int for database
        try:
            case_id_int = int(case_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid case_id: {case_id}")
            return False

        with self.get_cursor() as cursor:
            # Ensure columns exist
            cursor.execute("""
                ALTER TABLE bidding_cases
                ADD COLUMN IF NOT EXISTS llm_extracted_data JSONB,
                ADD COLUMN IF NOT EXISTS llm_extraction_timestamp TIMESTAMP WITH TIME ZONE
            """)

            # Update the case
            cursor.execute("""
                UPDATE bidding_cases
                SET
                    llm_extracted_data = %s,
                    llm_extraction_timestamp = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE case_id = %s
            """, (json.dumps(extracted_data, ensure_ascii=False), case_id_int))

            return cursor.rowcount > 0

    def search_by_text(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search cases by text across multiple fields"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM bidding_cases
                WHERE
                    case_name ILIKE %s OR
                    org_name ILIKE %s OR
                    bidding_format ILIKE %s OR
                    overview ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (f'%{search_text}%',) * 4 + (limit,))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


class JobExecutionLogRepository(BaseRepository):
    """Repository for job execution logs"""

    def create_log(self, job_name: str, status: str, **kwargs) -> None:
        """Create a job execution log entry"""
        with self.get_cursor() as cursor:
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
                kwargs.get('execution_duration_seconds', 0),
                json.dumps(kwargs.get('metadata', {}))
            ))

    def get_recent_logs(self, job_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent job execution logs"""
        with self.get_cursor() as cursor:
            if job_name:
                cursor.execute("""
                    SELECT * FROM job_execution_logs
                    WHERE job_name = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (job_name, limit))
            else:
                cursor.execute("""
                    SELECT * FROM job_execution_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


class BiddingEmbeddingRepository(BaseRepository):
    """Repository for bidding case embeddings"""

    def create_embedding(self, case_id: str, embedding: List[float],
                        model: str = "text-embedding-ada-002") -> bool:
        """Create or update embedding for a case"""
        with self.get_cursor() as cursor:
            # Ensure the embedding column exists and has proper index
            cursor.execute("""
                ALTER TABLE bidding_anken_embeddings
                ADD COLUMN IF NOT EXISTS embedding vector(1536)
            """)

            cursor.execute("""
                INSERT INTO bidding_anken_embeddings (case_id, embedding, model, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (case_id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model = EXCLUDED.model,
                    updated_at = CURRENT_TIMESTAMP
            """, (case_id, embedding, model))

            return cursor.rowcount > 0

    def find_similar_cases(self, embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar cases using vector similarity search"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT
                    be.case_id,
                    be.embedding <-> %s::vector as distance,
                    bc.case_name,
                    bc.org_name,
                    bc.bidding_format
                FROM bidding_anken_embeddings be
                JOIN bidding_cases bc ON be.case_id = bc.case_id
                ORDER BY distance
                LIMIT %s
            """, (embedding, limit))

            rows = cursor.fetchall()
            return [
                {
                    "case_id": row[0],
                    "distance": row[1],
                    "case_name": row[2],
                    "org_name": row[3],
                    "bidding_format": row[4]
                }
                for row in rows
            ]
