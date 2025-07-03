import os
from openai import OpenAI
from sql_connection import PostgreSQLConnection
import logging

client = OpenAI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAITextEmbedModel:
    def __init__(self):
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

    def embed_text(self, text: str):
        try:
            response = client.embeddings.create(input=text,
            model=self.embedding_model)
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"OpenAI APIエラー: {e}") from e

def main():
    """メイン関数：PostgreSQLから入札データを取得し、テキスト埋め込みを生成・保存"""

    db_conn = PostgreSQLConnection()
    embedder = OpenAITextEmbedModel()

    try:
        with db_conn.get_connection() as conn:
            with conn.cursor() as cursor:
                # 埋め込み未生成の入札データを取得
                cursor.execute("""
                    SELECT bc.case_id, bc.case_name, bc.overview
                    FROM bidding_cases bc
                    LEFT JOIN case_embeddings ce ON bc.case_id = ce.case_id
                    WHERE ce.case_id IS NULL
                    ORDER BY bc.created_at DESC
                """)

                unprocessed_cases = cursor.fetchall()
                logger.info(f"処理対象の入札データ数: {len(unprocessed_cases)}")

                if not unprocessed_cases:
                    logger.info("処理対象データがありません")
                    return

                processed_count = 0
                for case_id, case_name, overview in unprocessed_cases:
                    try:
                        # case_nameの埋め込み生成
                        case_name_embedding = None
                        if case_name:
                            case_name_embedding = embedder.embed_text(case_name)

                        # overviewの埋め込み生成
                        overview_embedding = None
                        if overview:
                            overview_embedding = embedder.embed_text(overview)

                        # 結合テキストの埋め込み生成
                        combined_text = f"{case_name or ''} {overview or ''}".strip()
                        combined_embedding = None
                        if combined_text:
                            combined_embedding = embedder.embed_text(combined_text)

                        # データベースに保存
                        cursor.execute("""
                            INSERT INTO case_embeddings (
                                case_id,
                                case_name_embedding,
                                overview_embedding,
                                combined_embedding,
                                embedding_model
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (case_id) DO UPDATE SET
                                case_name_embedding = EXCLUDED.case_name_embedding,
                                overview_embedding = EXCLUDED.overview_embedding,
                                combined_embedding = EXCLUDED.combined_embedding,
                                embedding_model = EXCLUDED.embedding_model,
                                updated_at = NOW()
                        """, (
                            case_id,
                            case_name_embedding,
                            overview_embedding,
                            combined_embedding,
                            embedder.embedding_model
                        ))

                        processed_count += 1

                        if processed_count % 10 == 0:
                            conn.commit()
                            logger.info(f"処理済み: {processed_count}/{len(unprocessed_cases)}")

                    except Exception as e:
                        logger.error(f"Case ID {case_id} の処理中にエラー: {e}")
                        continue

                conn.commit()
                logger.info(f"埋め込み生成完了: {processed_count} 件")

    except Exception as e:
        logger.error(f"メイン処理中にエラー: {e}")
        raise


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()
    main()
