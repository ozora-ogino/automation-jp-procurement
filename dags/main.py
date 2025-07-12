import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from crawler import main as crawler_main
from preprocessor import main as preprocessor_main, process_llm_extraction
from text_embedding import main as text_embeddgin_main
from llm import main as llm_main
from pdf_downloader import download_njss_multi_docs
from slack_notification import notify_success, notify_failure


dag = DAG(
    dag_id="main",
    schedule_interval=None,
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
)

# Use the main function from crawler that downloads to /data/search_result.csv
crawl_op = PythonOperator(
    task_id="crawl_njss_csv",
    python_callable=crawler_main,
    provide_context=True,
    dag=dag
)

# Download documents after crawling
download_docs_op = PythonOperator(
    task_id="download_documents",
    python_callable=download_njss_multi_docs,
    dag=dag
)

preprocess_op = PythonOperator(task_id="preprocess",
                         python_callable=preprocessor_main,
                         dag=dag)

# LLM document extraction operation
llm_extraction_op = PythonOperator(
    task_id="llm_document_extraction",
    python_callable=process_llm_extraction,
    dag=dag
)

# text_embed_op = PythonOperator(task_id="text_embedding",
#                          python_callable=text_embeddgin_main,
#                          dag=dag)

llm_inference_op = PythonOperator(task_id="llm_inference",
                         python_callable=llm_main,
                         dag=dag)

# Create Slack notification task
slack_notification_op = PythonOperator(
    task_id="slack_notification",
    python_callable=notify_success,
    trigger_rule="all_done",  # Run regardless of upstream success/failure
    dag=dag
)

# Set up task dependencies
crawl_op >> download_docs_op >> preprocess_op >> llm_extraction_op >> llm_inference_op >> slack_notification_op

# Add failure callbacks to each task
for task in [crawl_op, download_docs_op, preprocess_op, llm_extraction_op, llm_inference_op]:
    task.on_failure_callback = notify_failure
