-- ============================================================================
-- 入札データ用PostgreSQLデータベース初期セットアップ
-- 初回実行時のみ使用するスクリプト
-- ============================================================================

-- 0. Airflow用データベースの作成
-- Note: This needs to be run as a superuser
-- Create the airflow database if it doesn't exist
\c postgres
CREATE DATABASE airflow;

-- Switch back to the main database
\c "automation-jp-procurement"

-- 1. 必要な拡張機能を有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. 既存のビューを削除（テーブル変更前に実施）
DROP VIEW IF EXISTS active_eligible_biddings CASCADE;
DROP VIEW IF EXISTS active_biddings CASCADE;
DROP VIEW IF EXISTS recent_biddings CASCADE;
DROP VIEW IF EXISTS bidding_eligibility_stats CASCADE;
DROP VIEW IF EXISTS eligibility_by_rank CASCADE;

-- 3. メインの入札データテーブル
DROP TABLE IF EXISTS bidding_cases CASCADE;
CREATE TABLE bidding_cases (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id BIGINT UNIQUE NOT NULL,
    case_name TEXT NOT NULL,
    search_condition TEXT,
    bidding_format TEXT,
    case_url TEXT,

    -- 組織情報
    org_name TEXT,
    org_location TEXT,
    org_prefecture TEXT,
    delivery_location TEXT,

    -- スケジュール情報
    announcement_date DATE,
    bidding_date DATE,
    document_submission_date DATE,
    briefing_date DATE,
    award_announcement_date DATE,
    award_date DATE,

    -- 資格要件（JSON形式で格納）
    qualifications_raw TEXT,
    qualifications_parsed JSONB,
    qualifications_summary JSONB,
    business_types_raw TEXT,
    business_types_normalized TEXT[],
    business_type TEXT[],
    business_type_code TEXT[],

    -- コンテンツ
    overview TEXT,
    remarks TEXT,

    -- 価格情報
    planned_price_raw TEXT,
    planned_price_normalized DECIMAL,
    planned_unit_price DECIMAL,
    award_price_raw TEXT,
    award_price_normalized DECIMAL,
    award_unit_price DECIMAL,
    main_price DECIMAL,

    -- 落札情報
    winning_company TEXT,
    winning_company_address TEXT,
    winning_reason TEXT,
    winning_score DECIMAL,
    award_remarks TEXT,
    bid_result_details JSONB,
    unsuccessful_bid TEXT,

    -- 処理情報
    processed_at TIMESTAMP WITH TIME ZONE,
    qualification_confidence DECIMAL,

    -- 入札可否判定情報
    is_eligible_to_bid BOOLEAN,
    eligibility_reason TEXT,
    eligibility_details JSONB,

    -- メタデータ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 全文検索用のtsvector列
    search_vector tsvector
);

-- 4. ベクトル検索用テーブル
DROP TABLE IF EXISTS case_embeddings CASCADE;
CREATE TABLE case_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id BIGINT UNIQUE REFERENCES bidding_cases(case_id) ON DELETE CASCADE,

    case_name_embedding vector(3072),
    overview_embedding vector(3072),
    combined_embedding vector(3072),

    -- メタデータ
    embedding_model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. 定期ジョブ実行履歴テーブル
DROP TABLE IF EXISTS job_execution_logs CASCADE;
CREATE TABLE job_execution_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_name TEXT NOT NULL,
    execution_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT CHECK (status IN ('running', 'success', 'failed', 'timeout')),
    records_processed INTEGER DEFAULT 0,
    new_records_added INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    error_message TEXT,
    execution_duration_seconds INTEGER,
    metadata JSONB
);

-- 6. インデックスの作成

-- 基本的な検索用インデックス
CREATE INDEX idx_bidding_cases_case_id ON bidding_cases(case_id);
CREATE INDEX idx_bidding_cases_announcement_date ON bidding_cases(announcement_date);
CREATE INDEX idx_bidding_cases_bidding_date ON bidding_cases(bidding_date);
CREATE INDEX idx_bidding_cases_org_prefecture ON bidding_cases(org_prefecture);
CREATE INDEX idx_bidding_cases_bidding_format ON bidding_cases(bidding_format);

-- 入札可否判定用インデックス
CREATE INDEX idx_bidding_cases_is_eligible ON bidding_cases(is_eligible_to_bid);
CREATE INDEX idx_bidding_cases_eligible_bidding_date ON bidding_cases(is_eligible_to_bid, bidding_date)
    WHERE is_eligible_to_bid = true;

-- GINインデックス（JSON検索とtsvector検索用）
CREATE INDEX idx_bidding_cases_qualifications_parsed ON bidding_cases USING GIN(qualifications_parsed);
CREATE INDEX idx_bidding_cases_search_vector ON bidding_cases USING GIN(search_vector);
CREATE INDEX idx_bidding_cases_business_types ON bidding_cases USING GIN(business_types_normalized);
CREATE INDEX idx_bidding_cases_eligibility_details ON bidding_cases USING GIN(eligibility_details);

-- ベクトル検索用インデックス（IVFFlat - 3072次元をサポート）
-- Note: IVFFlatインデックスは、テーブルに十分なデータがある場合に作成する必要があります
-- 初期セットアップ時はコメントアウトし、データ投入後に作成することを推奨
-- CREATE INDEX idx_case_embeddings_case_name ON case_embeddings
--     USING ivfflat (case_name_embedding vector_cosine_ops)
--     WITH (lists = 100);
--
-- CREATE INDEX idx_case_embeddings_overview ON case_embeddings
--     USING ivfflat (overview_embedding vector_cosine_ops)
--     WITH (lists = 100);
--
-- CREATE INDEX idx_case_embeddings_combined ON case_embeddings
--     USING ivfflat (combined_embedding vector_cosine_ops)
--     WITH (lists = 100);

-- 代替案: btreeインデックスを使用（完全一致検索用）
CREATE INDEX idx_case_embeddings_case_id_btree ON case_embeddings(case_id);

-- 7. 全文検索用のトリガー関数
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('simple', COALESCE(NEW.case_name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.overview, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.org_name, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.qualifications_raw, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8. トリガーの作成
CREATE TRIGGER trigger_update_search_vector
    BEFORE INSERT OR UPDATE ON bidding_cases
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- 9. updated_atの自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_bidding_cases_updated_at
    BEFORE UPDATE ON bidding_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_case_embeddings_updated_at
    BEFORE UPDATE ON case_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 10. ビューの作成

-- アクティブな入札案件（入札可能案件のみ）
CREATE VIEW active_eligible_biddings AS
SELECT
    case_id,
    case_name,
    org_name,
    org_prefecture,
    announcement_date,
    bidding_date,
    document_submission_date,
    bidding_format,
    case_url,
    eligibility_reason,
    eligibility_details
FROM bidding_cases
WHERE
    is_eligible_to_bid = true
    AND (bidding_date >= CURRENT_DATE OR bidding_date IS NULL)
ORDER BY
    CASE WHEN bidding_date IS NULL THEN 1 ELSE 0 END,
    bidding_date ASC;

-- すべてのアクティブな入札案件
CREATE VIEW active_biddings AS
SELECT
    case_id,
    case_name,
    org_name,
    org_prefecture,
    announcement_date,
    bidding_date,
    document_submission_date,
    bidding_format,
    case_url,
    is_eligible_to_bid,
    eligibility_reason
FROM bidding_cases
WHERE bidding_date >= CURRENT_DATE OR bidding_date IS NULL
ORDER BY
    CASE WHEN bidding_date IS NULL THEN 1 ELSE 0 END,
    bidding_date ASC;

-- 最近の入札案件（過去30日）
CREATE VIEW recent_biddings AS
SELECT
    case_id,
    case_name,
    org_name,
    org_prefecture,
    announcement_date,
    bidding_date,
    bidding_format,
    case_url,
    is_eligible_to_bid,
    eligibility_reason,
    created_at
FROM bidding_cases
WHERE announcement_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY announcement_date DESC;

-- 入札可否統計ビュー
CREATE VIEW bidding_eligibility_stats AS
SELECT
    COUNT(*) AS total_cases,
    COUNT(CASE WHEN is_eligible_to_bid = true THEN 1 END) AS eligible_cases,
    COUNT(CASE WHEN is_eligible_to_bid = false THEN 1 END) AS ineligible_cases,
    COUNT(CASE WHEN is_eligible_to_bid IS NULL THEN 1 END) AS unchecked_cases,
    ROUND(100.0 * COUNT(CASE WHEN is_eligible_to_bid = true THEN 1 END) / NULLIF(COUNT(*), 0), 2) AS eligible_percentage
FROM bidding_cases;

-- ランク別入札可否統計ビュー
CREATE VIEW eligibility_by_rank AS
WITH qualification_data AS (
    SELECT
        bc.case_id,
        bc.is_eligible_to_bid,
        qual->>'level' AS required_rank
    FROM bidding_cases bc,
         LATERAL (
             SELECT jsonb_array_elements(
                 CASE
                     WHEN jsonb_typeof(bc.qualifications_parsed) = 'array'
                     THEN bc.qualifications_parsed
                     ELSE '[]'::jsonb
                 END
             ) AS qual
         ) AS q
    WHERE bc.qualifications_parsed IS NOT NULL
)
SELECT
    COALESCE(required_rank, 'No Rank') AS required_rank,
    COUNT(*) AS total_cases,
    COUNT(CASE WHEN is_eligible_to_bid = true THEN 1 END) AS eligible_cases,
    COUNT(CASE WHEN is_eligible_to_bid = false THEN 1 END) AS ineligible_cases
FROM qualification_data
GROUP BY required_rank
ORDER BY
    CASE required_rank
        WHEN 'A' THEN 1
        WHEN 'B' THEN 2
        WHEN 'C' THEN 3
        WHEN 'D' THEN 4
        WHEN 'ランク無し' THEN 5
        WHEN 'ランク不明' THEN 6
        ELSE 7
    END;

-- 11. データ検証用関数
CREATE OR REPLACE FUNCTION validate_bidding_data()
RETURNS TABLE(
    validation_type TEXT,
    case_count BIGINT,
    details TEXT
) AS $$
BEGIN
    -- 重複チェック
    RETURN QUERY
    SELECT
        'duplicate_case_ids'::TEXT,
        COUNT(*)::BIGINT,
        'Duplicate case_id entries found'::TEXT
    FROM (
        SELECT case_id
        FROM bidding_cases
        GROUP BY case_id
        HAVING COUNT(*) > 1
    ) duplicates;

    -- 日付整合性チェック
    RETURN QUERY
    SELECT
        'invalid_date_sequence'::TEXT,
        COUNT(*)::BIGINT,
        'Cases where bidding_date < announcement_date'::TEXT
    FROM bidding_cases
    WHERE bidding_date < announcement_date;

    -- 空の必須フィールドチェック
    RETURN QUERY
    SELECT
        'missing_required_fields'::TEXT,
        COUNT(*)::BIGINT,
        'Cases with missing case_name or case_id'::TEXT
    FROM bidding_cases
    WHERE case_name IS NULL OR case_name = '' OR case_id IS NULL;

    -- 入札可否判定未実施チェック
    RETURN QUERY
    SELECT
        'eligibility_not_checked'::TEXT,
        COUNT(*)::BIGINT,
        'Cases where eligibility has not been checked'::TEXT
    FROM bidding_cases
    WHERE is_eligible_to_bid IS NULL;

    -- 入札可能案件の統計
    RETURN QUERY
    SELECT
        'eligible_cases_stats'::TEXT,
        COUNT(*)::BIGINT,
        'Total eligible cases (D rank, no rank, or unknown rank)'::TEXT
    FROM bidding_cases
    WHERE is_eligible_to_bid = true;

    -- 入札不可案件の統計
    RETURN QUERY
    SELECT
        'ineligible_cases_stats'::TEXT,
        COUNT(*)::BIGINT,
        'Total ineligible cases (A, B, or C rank)'::TEXT
    FROM bidding_cases
    WHERE is_eligible_to_bid = false;

END;
$$ LANGUAGE plpgsql;

-- 12. 入札可能な案件を検索する関数
CREATE OR REPLACE FUNCTION search_eligible_cases(
    search_text TEXT DEFAULT NULL,
    prefecture TEXT DEFAULT NULL,
    from_date DATE DEFAULT NULL,
    to_date DATE DEFAULT NULL
)
RETURNS TABLE(
    case_id BIGINT,
    case_name TEXT,
    org_name TEXT,
    org_prefecture TEXT,
    bidding_date DATE,
    eligibility_reason TEXT,
    qualifications_raw TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bc.case_id,
        bc.case_name,
        bc.org_name,
        bc.org_prefecture,
        bc.bidding_date,
        bc.eligibility_reason,
        bc.qualifications_raw
    FROM bidding_cases bc
    WHERE
        bc.is_eligible_to_bid = true
        AND (search_text IS NULL OR bc.search_vector @@ plainto_tsquery('simple', search_text))
        AND (prefecture IS NULL OR bc.org_prefecture = prefecture)
        AND (from_date IS NULL OR bc.bidding_date >= from_date)
        AND (to_date IS NULL OR bc.bidding_date <= to_date)
    ORDER BY bc.bidding_date ASC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- 13. セットアップ完了メッセージ
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Database setup completed successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - bidding_cases (with eligibility columns)';
    RAISE NOTICE '  - case_embeddings';
    RAISE NOTICE '  - job_execution_logs';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - active_eligible_biddings';
    RAISE NOTICE '  - active_biddings';
    RAISE NOTICE '  - recent_biddings';
    RAISE NOTICE '  - bidding_eligibility_stats';
    RAISE NOTICE '  - eligibility_by_rank';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - validate_bidding_data()';
    RAISE NOTICE '  - search_eligible_cases()';
    RAISE NOTICE '============================================';
END $$;
