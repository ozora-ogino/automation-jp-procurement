import os
import json
import logging
from datetime import datetime, date
from openai import OpenAI
from sql_connection import PostgreSQLConnection
from prompts import VERIFY_BID_PROMPT_TEMPLATE

# OpenAI client initialization
client = OpenAI()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAILLMInference:
    """OpenAI LLMを使用した入札可否判定クラス"""

    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        self.temperature = 0.1  # 一貫性のある判定のため低めに設定

    def analyze_bid_eligibility(self, bid_data: dict) -> dict:
        """入札データを分析し、入札可否を判定"""
        try:
            # プロンプトテンプレートにデータを挿入
            prompt = VERIFY_BID_PROMPT_TEMPLATE.render(
                bid_data=json.dumps(bid_data, ensure_ascii=False, indent=2)
            )

            # OpenAI APIを呼び出し
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは政府調達の入札判定アナリストです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}  # JSON形式で応答を要求
            )

            # レスポンスをパース
            result = json.loads(response.choices[0].message.content)

            # 結果の検証
            if "is_eligible_bid" not in result or "reason" not in result:
                raise ValueError("レスポンスに必要なフィールドが含まれていません")

            # reasonが配列の場合は結合して文字列にする
            reason_text = result["reason"]
            if isinstance(reason_text, list):
                reason_text = " / ".join(reason_text)

            return {
                "is_eligible": result["is_eligible_bid"],
                "reason": reason_text,
                "details": result
            }

        except Exception as e:
            logger.error(f"LLM分析エラー: {e}")
            raise RuntimeError(f"入札可否判定中にエラーが発生しました: {e}") from e


def prepare_bid_data_for_prompt(row) -> dict:
    """データベースの行データをプロンプト用の辞書形式に変換"""
    return {
        "case_id": row[0],
        "case_name": row[1],
        "org_name": row[2],
        "org_prefecture": row[3],
        "announcement_date": row[4].isoformat() if row[4] else None,
        "bidding_date": row[5].isoformat() if row[5] else None,
        "bidding_format": row[6],
        "qualifications_raw": row[7],
        "business_types_raw": row[8],
        "overview": row[9],
        "planned_price_raw": row[10],
        "delivery_location": row[11],
        "remarks": row[12]
    }


def main():
    """メイン関数：今日の入札データを取得し、LLMで入札可否を判定"""

    db_conn = PostgreSQLConnection()
    llm_inference = OpenAILLMInference()

    try:
        with db_conn.get_connection() as conn:
            with conn.cursor() as cursor:
                # 今日作成された入札データを取得（判定済みかどうかに関わらず）
                today = date.today()
                cursor.execute("""
                    SELECT
                        case_id,
                        case_name,
                        org_name,
                        org_prefecture,
                        announcement_date,
                        bidding_date,
                        bidding_format,
                        qualifications_raw,
                        business_types_raw,
                        overview,
                        planned_price_raw,
                        delivery_location,
                        remarks
                    FROM bidding_cases
                    WHERE
                        DATE(created_at) = %s
                    ORDER BY created_at DESC
                """, (today,))

                unprocessed_cases = cursor.fetchall()
                logger.info(f"本日の入札データ数: {len(unprocessed_cases)}")

                if not unprocessed_cases:
                    logger.info("処理対象データがありません")
                    return

                processed_count = 0
                error_count = 0
                skipped_count = 0

                for row in unprocessed_cases:
                    case_id = row[0]

                    try:
                        # 既に判定済みかチェック
                        cursor.execute("""
                            SELECT is_eligible_to_bid
                            FROM bidding_cases
                            WHERE case_id = %s
                        """, (case_id,))
                        existing_result = cursor.fetchone()

                        if existing_result and existing_result[0] is not None:
                            if existing_result[0] == False:  # 既に入札不可と判定されている
                                logger.info(f"Case ID {case_id} は既に入札不可と判定されているため、スキップします")
                                skipped_count += 1
                                continue
                            else:
                                logger.info(f"Case ID {case_id} は既に判定済みですが、再判定します")

                        # プロンプト用データを準備
                        bid_data = prepare_bid_data_for_prompt(row)

                        # LLMで入札可否を判定
                        logger.info(f"Case ID {case_id} の判定を開始...")
                        result = llm_inference.analyze_bid_eligibility(bid_data)

                        # データベースを更新
                        cursor.execute("""
                            UPDATE bidding_cases
                            SET
                                is_eligible_to_bid = %s,
                                eligibility_reason = %s,
                                eligibility_details = %s,
                                updated_at = NOW()
                            WHERE case_id = %s
                        """, (
                            result["is_eligible"],
                            result["reason"],
                            json.dumps(result["details"], ensure_ascii=False),
                            case_id
                        ))

                        processed_count += 1
                        logger.info(f"Case ID {case_id}: {'入札可能' if result['is_eligible'] else '入札不可'}")

                        # 10件ごとにコミット
                        if processed_count % 10 == 0:
                            conn.commit()
                            logger.info(f"進捗: {processed_count}/{len(unprocessed_cases)}")

                    except Exception as e:
                        error_count += 1
                        logger.error(f"Case ID {case_id} の処理中にエラー: {e}")
                        continue

                # 最終コミット
                conn.commit()

                # 処理結果のサマリー
                logger.info(f"""
                処理完了:
                - 総件数: {len(unprocessed_cases)}
                - 成功: {processed_count}
                - スキップ（既に入札不可）: {skipped_count}
                - エラー: {error_count}
                """)

                # 判定結果の統計を取得
                cursor.execute("""
                    SELECT
                        COUNT(CASE WHEN is_eligible_to_bid = true THEN 1 END) as eligible_count,
                        COUNT(CASE WHEN is_eligible_to_bid = false THEN 1 END) as ineligible_count
                    FROM bidding_cases
                    WHERE DATE(created_at) = %s
                """, (today,))

                stats = cursor.fetchone()
                logger.info(f"""
                本日の判定結果統計:
                - 入札可能: {stats[0]}件
                - 入札不可: {stats[1]}件
                """)

    except Exception as e:
        logger.error(f"メイン処理中にエラー: {e}")
        raise


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()
    main()
