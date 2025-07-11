import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from crawler import main as crawler_main
from preprocessor import main as preprocessor_main
from text_embedding import main as text_embeddgin_main
from llm import main as llm_main
from pdf_downloader import download_njss_multi_docs


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

# text_embed_op = PythonOperator(task_id="text_embedding",
#                          python_callable=text_embeddgin_main,
#                          dag=dag)

llm_inference_op = PythonOperator(task_id="llm_inference",
                         python_callable=llm_main,
                         dag=dag)

crawl_op >> download_docs_op >> preprocess_op >> llm_inference_op
