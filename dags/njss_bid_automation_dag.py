#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fully refactored main DAG using the new modular architecture.
All components are now using the new service-based approach.
"""

import os
import datetime
import logging
import asyncio
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import services
from db.connection import PostgreSQLConnection
from db.repositories import BiddingCaseRepository, JobExecutionLogRepository, BiddingEmbeddingRepository
from core.authentication import NJSSAuthenticationService
from core.crawler_service import NJSSCrawlerService
from core.services import BiddingProcessingService
from processing.text_processor import TextProcessor
from processing.llm_extraction_service import LLMExtractionService
from processing.llm_inference_service import LLMInferenceService
# from processing.embedding_service import EmbeddingService
from utils.file_service import FileService
from slack_notification import notify_success, notify_failure
from constants import DATA_DIR, DOC_DIR

logger = logging.getLogger(__name__)


def crawl_njss_task(**context):
    """Task 1: Crawl NJSS and save results - using same logic as original crawler"""
    logger.info("Starting NJSS CSV download...")

    # Get credentials - try Airflow connection first, then environment
    username = None
    password = None

    try:
        # Try to get from Airflow connection
        from njss_auth_config import NJSSAuthConfig
        username, password = NJSSAuthConfig.get_credentials()
        logger.info(f"Got credentials from Airflow config for user: {username}")
    except Exception as e:
        logger.debug(f"Could not get Airflow credentials: {e}")
        # Fall back to environment variables
        username = os.environ.get('NJSS_USERNAME', '')
        password = os.environ.get('NJSS_PASSWORD', '')

    if not username or not password:
        raise ValueError("NJSS credentials not found")

    headless = os.environ.get('CRAWLER_HEADLESS', 'true').lower() == 'true'

    # Generate date-based filename
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m%d')
    csv_filename = f"search_result_{date_str}.csv"
    csv_path = Path(DATA_DIR) / csv_filename

    # Check if today's CSV file already exists
    if csv_path.exists():
        logger.info(f"Today's CSV file already exists at {csv_path}, skipping download")
        # Push result to XCom if in Airflow context
        if context and 'task_instance' in context:
            context['task_instance'].xcom_push(key='csv_path', value=str(csv_path))
            context['task_instance'].xcom_push(key='download_status', value='skipped')
        return str(csv_path)

    # Initialize services
    auth_service = NJSSAuthenticationService(username, password, headless)
    file_service = FileService(base_dir=DATA_DIR)

    # Import the new home crawler
    from core.njss_home_crawler import NJSSHomeCrawlerService

    # Create and run crawler
    crawler = NJSSHomeCrawlerService(auth_service, file_service, headless=headless, timeout=60000)

    try:
        # Download files from home page
        downloaded_files = asyncio.run(crawler.download_from_home())

        # Process and merge files into final CSV with custom filename
        csv_path = crawler.process_downloaded_files(downloaded_files, output_filename=csv_filename)

        # Push result to XCom if in Airflow context
        if context and 'task_instance' in context:
            context['task_instance'].xcom_push(key='csv_path', value=str(csv_path))
            context['task_instance'].xcom_push(key='download_status', value='success')

        logger.info(f"Successfully saved CSV to {csv_path}")
        return str(csv_path)

    except Exception as e:
        logger.error(f"Failed to download NJSS CSV: {str(e)}")

        # Push error to XCom if in Airflow context
        if context and 'task_instance' in context:
            context['task_instance'].xcom_push(key='download_status', value='failed')
            context['task_instance'].xcom_push(key='error_message', value=str(e))

        raise


def download_documents_task(**context):
    """Task 2: Download documents for new cases - using exact original logic"""
    logger.info("Starting document download task...")

    # Get credentials - try Airflow connection first, then environment
    username = None
    password = None

    try:
        # Try to get from Airflow connection
        from njss_auth_config import NJSSAuthConfig
        username, password = NJSSAuthConfig.get_credentials()
        logger.info(f"Got credentials from Airflow config for user: {username}")
    except Exception as e:
        logger.debug(f"Could not get Airflow credentials: {e}")
        # Fall back to environment variables
        username = os.environ.get('NJSS_USERNAME', '')
        password = os.environ.get('NJSS_PASSWORD', '')

    if not username or not password:
        raise ValueError("NJSS credentials not found")

    headless = os.environ.get('CRAWLER_HEADLESS', 'true').lower() == 'true'

    # Initialize services
    auth_service = NJSSAuthenticationService(username, password, headless)
    file_service = FileService(base_dir=DATA_DIR)

    # Get CSV path from XCom
    csv_path = context['task_instance'].xcom_pull(task_ids='crawl_njss', key='csv_path')
    if not csv_path:
        raise ValueError("CSV path not found in XCom")

    # Read cases from CSV
    import pandas as pd
    df = pd.read_csv(csv_path)

    # Check available columns
    logger.info(f"CSV columns: {list(df.columns)}")

    # Prepare cases for download (limit to recent ones)
    cases = []
    for _, row in df.head(10).iterrows():  # Process top 10 cases
        # Look for the correct column name - might be '案件概要URL' instead of '案件URL'
        url_column = None
        for col in ['案件概要URL', '案件URL', 'case_url']:
            if col in row and pd.notna(row.get(col)):
                url_column = col
                break

        if url_column:
            cases.append({
                'case_id': str(row['案件ID']),
                'anken_url': row[url_column]
            })

    logger.info(f"Found {len(cases)} cases with URLs to download")

    if not cases:
        logger.warning("No cases with URLs found for document download")
        return {'cases_processed': 0, 'successful_downloads': 0}

    # Use the document downloader service
    from core.document_downloader_service import DocumentDownloaderService
    downloader = DocumentDownloaderService(auth_service, file_service)

    import asyncio
    results = asyncio.run(downloader.download_documents_for_cases(cases))

    success_count = sum(1 for r in results if r.get('success', False))
    total_docs = sum(r.get('documents_downloaded', 0) for r in results if r.get('success', False))

    logger.info(f"Downloaded documents for {success_count}/{len(cases)} cases, total {total_docs} documents")

    # Update database with download information
    if success_count > 0:
        db_connection = PostgreSQLConnection()
        case_repo = BiddingCaseRepository(db_connection)

        # Create a mapping of case_id to row data for easy lookup
        case_data_map = {}
        for _, row in df.iterrows():
            case_data_map[str(row['案件ID'])] = row

        for result in results:
            if result.get('success', False) and result.get('documents_downloaded', 0) > 0:
                case_id = result['case_id']
                doc_dir = result.get('directory', str(Path(DOC_DIR) / case_id))

                # Get the full case data from CSV
                if case_id in case_data_map:
                    csv_row = case_data_map[case_id]

                    # Prepare case data with all available fields from CSV
                    case_data = {
                        'case_id': case_id,
                        'document_directory': doc_dir,
                        'document_count': result['documents_downloaded'],
                        'downloaded_count': result['documents_downloaded'],  # Add downloaded_count
                        'documents': result.get('files', [])  # Add documents array
                    }

                    # Add case_name (required field)
                    if '案件名' in csv_row and pd.notna(csv_row['案件名']):
                        case_data['case_name'] = str(csv_row['案件名'])

                    # Add other fields if available (matching column names from services.py)
                    if '機関' in csv_row and pd.notna(csv_row['機関']):
                        case_data['organization_name'] = str(csv_row['機関'])

                    if '入札形式' in csv_row and pd.notna(csv_row['入札形式']):
                        case_data['procurement_type'] = str(csv_row['入札形式'])

                    if '案件公示日' in csv_row and pd.notna(csv_row['案件公示日']):
                        case_data['publication_date'] = str(csv_row['案件公示日'])

                    if '開札日時' in csv_row and pd.notna(csv_row['開札日時']):
                        case_data['bid_opening_date'] = str(csv_row['開札日時'])
                    elif '入札日' in csv_row and pd.notna(csv_row['入札日']):
                        case_data['bid_opening_date'] = str(csv_row['入札日'])

                    # Get the URL
                    for col in ['案件概要URL', '案件URL', 'case_url']:
                        if col in csv_row and pd.notna(csv_row.get(col)):
                            case_data['anken_url'] = str(csv_row[col])
                            break

                    case_repo.upsert_bidding_case(case_data)
                else:
                    logger.warning(f"Case {case_id} not found in CSV data, skipping database update")

    # Also update CSV like original
    if results:
        # Add document info to CSV
        for idx, row in df.iterrows():
            anken_id = str(row['案件ID'])
            for result in results:
                if result['case_id'] == anken_id:
                    df.at[idx, '文書保存先'] = result.get('directory', '')
                    df.at[idx, '文書数'] = result.get('documents_downloaded', 0)
                    logger.info(f"Updated CSV row for case {anken_id}: dir={result.get('directory')}, count={result.get('documents_downloaded')}")
                    break

        # Save updated CSV
        df.to_csv(csv_path, index=False)
        logger.info(f"Updated CSV: {csv_path}")

    return {
        'cases_processed': len(cases),
        'successful_downloads': success_count,
        'total_documents': total_docs
    }


def preprocess_data_task(**context):
    """Task 3: Process CSV data and update database"""
    # Get CSV path from XCom
    csv_path = context['task_instance'].xcom_pull(task_ids='crawl_njss', key='csv_path')
    if not csv_path:
        raise ValueError("CSV path not found in XCom")

    # Initialize database connection
    db_connection = PostgreSQLConnection()

    # Initialize repositories
    case_repo = BiddingCaseRepository(db_connection)
    log_repo = JobExecutionLogRepository(db_connection)

    # Initialize services
    file_service = FileService(base_dir=DATA_DIR)
    processing_service = BiddingProcessingService(case_repo, log_repo, file_service)

    # Process CSV data
    total, new, updated = processing_service.process_csv_data(csv_path)

    logger.info(f"Processed {total} records: {new} new, {updated} updated")
    return {'total': total, 'new': new, 'updated': updated}


def llm_extraction_task(**context):
    """Task 4: Extract structured data from documents using LLM"""
    # Get OpenAI API key
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    # Initialize services
    db_connection = PostgreSQLConnection()
    case_repo = BiddingCaseRepository(db_connection)
    file_service = FileService(base_dir=DATA_DIR)
    text_processor = TextProcessor(file_service)

    # Create extraction service
    extraction_service = LLMExtractionService(
        case_repo, text_processor, file_service, openai_api_key
    )

    # Process cases
    result = extraction_service.process_cases_with_llm(limit=20)

    if not result['success']:
        raise Exception(f"LLM extraction failed: {result.get('error', 'Unknown error')}")

    logger.info(f"LLM extraction completed: {result['successful']}/{result['processed']} cases")
    return result


def llm_inference_task(**context):
    """Task 5: Run eligibility inference using LLM"""
    # Get OpenAI API key
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    # Initialize services
    db_connection = PostgreSQLConnection()
    case_repo = BiddingCaseRepository(db_connection)

    # Create inference service
    inference_service = LLMInferenceService(case_repo, openai_api_key)

    # Run inference
    result = inference_service.run_inference_batch(limit=50)

    if not result['success']:
        raise Exception(f"LLM inference failed: {result.get('error', 'Unknown error')}")

    logger.info(f"Inference completed: {result['eligible']}/{result['processed']} eligible cases")
    return result


def generate_embeddings_task(**context):
    """Task 6: Generate embeddings for semantic search"""
    # Get OpenAI API key
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    # Initialize services
    db_connection = PostgreSQLConnection()
    case_repo = BiddingCaseRepository(db_connection)

    # embedding_repo = BiddingEmbeddingRepository(db_connection)
    # Create embedding service
    # embedding_service = EmbeddingService(case_repo, embedding_repo, openai_api_key)

    # Generate embeddings
    # result = embedding_service.generate_embeddings_batch(limit=50)

    # if not result['success']:
    #     raise Exception(f"Embedding generation failed: {result.get('error', 'Unknown error')}")

    # logger.info(f"Generated {result['successful']} embeddings")
    # return result


# DAG definition
dag = DAG(
    dag_id="njss_procurement_pipeline_v2",
    description="Fully refactored NJSS procurement automation pipeline",
    schedule_interval="0 3 * * *",  # Run daily at 3 AM JST
    start_date=datetime.datetime(2025, 7, 1),
    catchup=False,
)

# Define tasks
crawl_task = PythonOperator(
    task_id="crawl_njss",
    python_callable=crawl_njss_task,
    provide_context=True,
    dag=dag
)

download_task = PythonOperator(
    task_id="download_documents",
    python_callable=download_documents_task,
    provide_context=True,
    dag=dag
)

preprocess_task = PythonOperator(
    task_id="preprocess_data",
    python_callable=preprocess_data_task,
    provide_context=True,
    dag=dag
)

extraction_task = PythonOperator(
    task_id="llm_extraction",
    python_callable=llm_extraction_task,
    provide_context=True,
    dag=dag
)

inference_task = PythonOperator(
    task_id="llm_inference",
    python_callable=llm_inference_task,
    provide_context=True,
    dag=dag
)

# embedding_task = PythonOperator(
#     task_id="generate_embeddings",
#     python_callable=generate_embeddings_task,
#     provide_context=True,
#     dag=dag
# )

notification_task = PythonOperator(
    task_id="slack_notification",
    python_callable=notify_success,
    trigger_rule="all_done",
    dag=dag
)

# Set up task dependencies
crawl_task >> download_task >> preprocess_task >> extraction_task >> inference_task >> notification_task

# Add failure callbacks
for task in [crawl_task, download_task, preprocess_task, extraction_task, inference_task]:
    task.on_failure_callback = notify_failure
