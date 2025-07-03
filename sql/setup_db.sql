-- ============================================================================
-- 入札データ用PostgreSQLデータベース設定
-- ============================================================================

-- 1. 必要な拡張機能を有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. メインの入札データテーブル
CREATE TABLE IF NOT EXISTS bidding_cases (
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

    -- メタデータ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 全文検索用のtsvector列
    search_vector tsvector
);

-- 3. ベクトル検索用テーブル
CREATE TABLE IF NOT EXISTS case_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id BIGINT REFERENCES bidding_cases(case_id) ON DELETE CASCADE,

    -- ベクトルデータ（次元数は使用するembeddingモデルに応じて調整）
    case_name_embedding vector(1536),  -- OpenAI text-embedding-ada-002の場合
    overview_embedding vector(1536),
    combined_embedding vector(1536),   -- case_name + overview の組み合わせ

    -- メタデータ
    embedding_model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. 定期ジョブ実行履歴テーブル
CREATE TABLE IF NOT EXISTS job_execution_logs (
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

-- 5. インデックスの作成

-- 基本的な検索用インデックス
CREATE INDEX IF NOT EXISTS idx_bidding_cases_case_id ON bidding_cases(case_id);
CREATE INDEX IF NOT EXISTS idx_bidding_cases_announcement_date ON bidding_cases(announcement_date);
CREATE INDEX IF NOT EXISTS idx_bidding_cases_bidding_date ON bidding_cases(bidding_date);
CREATE INDEX IF NOT EXISTS idx_bidding_cases_org_prefecture ON bidding_cases(org_prefecture);
CREATE INDEX IF NOT EXISTS idx_bidding_cases_bidding_format ON bidding_cases(bidding_format);

-- GINインデックス（JSON検索とtsvector検索用）
CREATE INDEX IF NOT EXISTS idx_bidding_cases_qualifications_parsed ON bidding_cases USING GIN(qualifications_parsed);
CREATE INDEX IF NOT EXISTS idx_bidding_cases_search_vector ON bidding_cases USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_bidding_cases_business_types ON bidding_cases USING GIN(business_types_normalized);

-- ベクトル検索用インデックス（HNSW）
CREATE INDEX IF NOT EXISTS idx_case_embeddings_case_name ON case_embeddings USING hnsw (case_name_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_case_embeddings_overview ON case_embeddings USING hnsw (overview_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_case_embeddings_combined ON case_embeddings USING hnsw (combined_embedding vector_cosine_ops);

-- 6. 全文検索用のトリガー関数
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

-- 7. トリガーの作成
DROP TRIGGER IF EXISTS trigger_update_search_vector ON bidding_cases;
CREATE TRIGGER trigger_update_search_vector
    BEFORE INSERT OR UPDATE ON bidding_cases
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- 8. updated_atの自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_bidding_cases_updated_at ON bidding_cases;
CREATE TRIGGER trigger_update_bidding_cases_updated_at
    BEFORE UPDATE ON bidding_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_update_case_embeddings_updated_at ON case_embeddings;
CREATE TRIGGER trigger_update_case_embeddings_updated_at
    BEFORE UPDATE ON case_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 9. ビューの作成（よく使用するクエリ用）
CREATE OR REPLACE VIEW active_biddings AS
SELECT
    case_id,
    case_name,
    org_name,
    org_prefecture,
    announcement_date,
    bidding_date,
    document_submission_date,
    bidding_format,
    case_url
FROM bidding_cases
WHERE bidding_date >= CURRENT_DATE OR bidding_date IS NULL
ORDER BY
    CASE WHEN bidding_date IS NULL THEN 1 ELSE 0 END,
    bidding_date ASC;

-- 最近の入札案件（過去30日）
CREATE OR REPLACE VIEW recent_biddings AS
SELECT
    case_id,
    case_name,
    org_name,
    org_prefecture,
    announcement_date,
    bidding_date,
    bidding_format,
    case_url,
    created_at
FROM bidding_cases
WHERE announcement_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY announcement_date DESC;

-- 10. データ検証用関数
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

END;
$$ LANGUAGE plpgsql;
