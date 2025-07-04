import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from crawler import TempCrawler
from preprocessor import main as preprocessor_main
from text_embedding import main as text_embeddgin_main
from llm import main as llm_main


dag = DAG(
    dag_id="main",
    schedule_interval=None,
)

TempCrawler = TempCrawler()
crawl_op = PythonOperator(task_id="crawl_njss_csv",
                         python_callable=TempCrawler.crawl_njss_csv,
                         dag=dag)

preprocess_op = PythonOperator(task_id="preprocess",
                         python_callable=preprocessor_main,
                         dag=dag)

text_embed_op = PythonOperator(task_id="text_embedding",
                         python_callable=text_embeddgin_main,
                         dag=dag)

llm_inference_op = PythonOperator(task_id="llm_inference",
                         python_callable=llm_main,
                         dag=dag)

crawl_op >> preprocess_op >> text_embed_op >> llm_inference_op
