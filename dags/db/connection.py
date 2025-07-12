import os
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLConnection:
    """PostgreSQL接続管理クラス"""

    def __init__(self):
        # 環境変数から接続情報を取得
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = os.getenv('POSTGRES_PORT', '5432')
        self.database = os.getenv('POSTGRES_DB', 'airflow')
        self.user = os.getenv('POSTGRES_USER', 'airflow')
        self.password = os.getenv('POSTGRES_PASSWORD', 'airflow')

        # 接続文字列
        self.connection_string = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.psycopg2_params = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }

    @contextmanager
    def get_connection(self):
        """psycopg2接続のコンテキストマネージャー"""
        conn = None
        try:
            conn = psycopg2.connect(**self.psycopg2_params)
            logger.info("PostgreSQL接続成功")
            yield conn
        except Exception as e:
            logger.error(f"PostgreSQL接続エラー: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.info("PostgreSQL接続終了")

    def get_engine(self):
        """SQLAlchemy engine取得"""
        try:
            engine = create_engine(self.connection_string)
            logger.info("SQLAlchemy engine作成成功")
            return engine
        except Exception as e:
            logger.error(f"SQLAlchemy engine作成エラー: {e}")
            raise

    def test_connection(self):
        """接続テスト"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()
                    logger.info(f"PostgreSQL version: {version[0]}")
                    return True
        except Exception as e:
            logger.error(f"接続テスト失敗: {e}")
            return False
