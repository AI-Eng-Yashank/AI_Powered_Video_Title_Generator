-- ============================================================================
-- VIDEO TITLE GENERATOR - NEON DB SCHEMA
-- ============================================================================
-- Database: PostgreSQL (Neon DB)
-- Version: 1.0.0
-- Description: Complete schema for AI-powered video title generation system
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- For encryption if needed

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- Supported platforms for title optimization
CREATE TYPE platform_type AS ENUM (
    'youtube',
    'instagram',
    'tiktok',
    'twitter',
    'general'
);

-- Video processing status
CREATE TYPE processing_status AS ENUM (
    'pending',          -- Just uploaded, waiting to process
    'uploading',        -- File upload in progress
    'extracting',       -- Extracting audio from video
    'transcribing',     -- Transcribing audio to text
    'fetching_trends',  -- Fetching trend data
    'generating',       -- Generating titles
    'completed',        -- Successfully completed
    'failed'            -- Processing failed
);

-- Title style categories
CREATE TYPE title_style AS ENUM (
    'curiosity',        -- Creates intrigue
    'how_to',           -- Educational/tutorial
    'listicle',         -- Number-based (5 ways, 10 tips)
    'story',            -- Personal narrative
    'contrarian',       -- Challenges assumptions
    'question',         -- Asks a question
    'news',             -- Breaking/trending news style
    'emotional'         -- Emotional triggers
);

-- Trend source platforms
CREATE TYPE trend_source AS ENUM (
    'google_trends',
    'youtube',
    'reddit',
    'twitter',
    'tiktok',
    'manual'
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. USERS TABLE
-- ----------------------------------------------------------------------------
-- Stores user information (if you add authentication later)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    api_key VARCHAR(64) UNIQUE,                  -- For API authentication
    is_active BOOLEAN DEFAULT true,
    
    -- Usage limits
    daily_video_limit INTEGER DEFAULT 10,
    monthly_video_limit INTEGER DEFAULT 100,
    max_video_size_mb INTEGER DEFAULT 500,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Index for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);

-- ----------------------------------------------------------------------------
-- 2. VIDEOS TABLE
-- ----------------------------------------------------------------------------
-- Stores uploaded video metadata
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- File information
    original_filename VARCHAR(500) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL UNIQUE,
    file_size_bytes BIGINT NOT NULL,
    file_format VARCHAR(20) NOT NULL,           -- mp4, mov, avi, etc.
    mime_type VARCHAR(100),
    
    -- Video metadata (extracted via ffprobe)
    duration_seconds DECIMAL(10, 2),
    resolution_width INTEGER,
    resolution_height INTEGER,
    fps DECIMAL(5, 2),
    video_codec VARCHAR(50),
    audio_codec VARCHAR(50),
    bitrate_kbps INTEGER,
    
    -- Storage paths
    storage_path VARCHAR(500),                   -- Path on server/S3
    thumbnail_path VARCHAR(500),                 -- Optional thumbnail
    
    -- Processing info
    status processing_status DEFAULT 'pending',
    target_platform platform_type DEFAULT 'general',
    requested_titles_count INTEGER DEFAULT 5,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE          -- Soft delete
);

-- Indexes
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX idx_videos_stored_filename ON videos(stored_filename);

-- ----------------------------------------------------------------------------
-- 3. TRANSCRIPTS TABLE
-- ----------------------------------------------------------------------------
-- Stores video transcriptions
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    
    -- Transcript content
    full_text TEXT NOT NULL,
    summary TEXT,                                -- AI-generated summary
    word_count INTEGER NOT NULL,
    
    -- Language detection
    detected_language VARCHAR(10) NOT NULL,      -- en, es, fr, etc.
    language_confidence DECIMAL(3, 2),           -- 0.00 to 1.00
    
    -- Processing metadata
    transcription_model VARCHAR(100),            -- whisper-large-v3-turbo
    chunks_processed INTEGER DEFAULT 1,
    processing_time_seconds DECIMAL(10, 2),
    
    -- Audio file info (intermediate)
    audio_file_size_mb DECIMAL(10, 2),
    audio_duration_seconds DECIMAL(10, 2),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_transcripts_video_id ON transcripts(video_id);
CREATE INDEX idx_transcripts_language ON transcripts(detected_language);

-- Full-text search index for transcript content
CREATE INDEX idx_transcripts_fulltext ON transcripts USING GIN(to_tsvector('english', full_text));

-- ----------------------------------------------------------------------------
-- 4. GENERATED TITLES TABLE
-- ----------------------------------------------------------------------------
-- Stores AI-generated titles for each video
CREATE TABLE generated_titles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    
    -- Title content
    title_text VARCHAR(500) NOT NULL,
    title_style title_style,
    reasoning TEXT,                              -- Why this title works
    
    -- Ranking/ordering
    rank_position INTEGER NOT NULL,              -- 1, 2, 3, 4, 5
    confidence_score DECIMAL(3, 2),              -- AI confidence 0.00-1.00
    
    -- Platform optimization
    target_platform platform_type NOT NULL,
    character_count INTEGER,
    
    -- User feedback
    is_selected BOOLEAN DEFAULT false,           -- User chose this title
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_generated_titles_video_id ON generated_titles(video_id);
CREATE INDEX idx_generated_titles_platform ON generated_titles(target_platform);
CREATE INDEX idx_generated_titles_selected ON generated_titles(is_selected) WHERE is_selected = true;

-- ----------------------------------------------------------------------------
-- 5. TRENDS CACHE TABLE
-- ----------------------------------------------------------------------------
-- Caches trending topics from various sources
CREATE TABLE trends_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Trend data
    source trend_source NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    topic VARCHAR(500),
    hashtag VARCHAR(255),
    
    -- Metrics
    popularity_score INTEGER,                    -- Relative score
    search_volume INTEGER,                       -- If available
    growth_percentage DECIMAL(5, 2),             -- Trend growth
    
    -- Geographic/category info
    region VARCHAR(10) DEFAULT 'US',             -- Country code
    category VARCHAR(100),                       -- Tech, Entertainment, etc.
    
    -- Cache management
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

-- Indexes
CREATE INDEX idx_trends_source ON trends_cache(source);
CREATE INDEX idx_trends_keyword ON trends_cache(keyword);
CREATE INDEX idx_trends_expires ON trends_cache(expires_at);
CREATE INDEX idx_trends_active ON trends_cache(is_active) WHERE is_active = true;

-- Composite index for efficient trend lookups
CREATE INDEX idx_trends_source_active_expires ON trends_cache(source, is_active, expires_at DESC);

-- ----------------------------------------------------------------------------
-- 6. VIDEO TRENDS JUNCTION TABLE
-- ----------------------------------------------------------------------------
-- Links videos to the trends used in title generation
CREATE TABLE video_trends_used (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    trend_id UUID REFERENCES trends_cache(id) ON DELETE SET NULL,
    
    -- Store keyword even if trend_id is deleted
    trend_keyword VARCHAR(255) NOT NULL,
    trend_source trend_source,
    
    -- Was this trend actually used in a title?
    was_incorporated BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_video_trends_video_id ON video_trends_used(video_id);
CREATE INDEX idx_video_trends_trend_id ON video_trends_used(trend_id);

-- ----------------------------------------------------------------------------
-- 7. PROCESSING JOBS TABLE
-- ----------------------------------------------------------------------------
-- Tracks video processing jobs and their progress
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    
    -- Job status
    status processing_status DEFAULT 'pending',
    current_step VARCHAR(50),                    -- upload, extract, transcribe, etc.
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    total_processing_time_seconds DECIMAL(10, 2),
    
    -- Step-by-step timing (for analytics)
    upload_time_seconds DECIMAL(10, 2),
    extraction_time_seconds DECIMAL(10, 2),
    transcription_time_seconds DECIMAL(10, 2),
    trend_fetch_time_seconds DECIMAL(10, 2),
    generation_time_seconds DECIMAL(10, 2),
    
    -- Error handling
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Worker info (if using job queues)
    worker_id VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_processing_jobs_video_id ON processing_jobs(video_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_created ON processing_jobs(created_at DESC);

-- ----------------------------------------------------------------------------
-- 8. API USAGE LOG TABLE
-- ----------------------------------------------------------------------------
-- Tracks API usage for rate limiting and analytics
CREATE TABLE api_usage_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Request info
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,                 -- GET, POST, etc.
    request_ip VARCHAR(45),                      -- IPv4 or IPv6
    user_agent TEXT,
    
    -- Video processing specific
    video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    video_size_bytes BIGINT,
    processing_time_seconds DECIMAL(10, 2),
    
    -- External API calls made
    groq_whisper_calls INTEGER DEFAULT 0,
    groq_llm_calls INTEGER DEFAULT 0,
    youtube_api_calls INTEGER DEFAULT 0,
    google_trends_calls INTEGER DEFAULT 0,
    reddit_api_calls INTEGER DEFAULT 0,
    
    -- Response info
    response_status INTEGER,
    response_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_api_usage_user_id ON api_usage_log(user_id);
CREATE INDEX idx_api_usage_created ON api_usage_log(created_at DESC);
CREATE INDEX idx_api_usage_endpoint ON api_usage_log(endpoint);

-- Partition by month for better performance (optional, for high volume)
-- CREATE INDEX idx_api_usage_created_month ON api_usage_log(date_trunc('month', created_at));

-- ----------------------------------------------------------------------------
-- 9. USER FEEDBACK TABLE
-- ----------------------------------------------------------------------------
-- Stores user feedback on generated titles (for improving AI)
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    title_id UUID REFERENCES generated_titles(id) ON DELETE CASCADE,
    
    -- Feedback data
    feedback_type VARCHAR(50) NOT NULL,          -- selected, rejected, edited, rated
    original_title VARCHAR(500),
    edited_title VARCHAR(500),                   -- If user modified the title
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    
    -- Context
    selected_platform platform_type,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_user_feedback_video_id ON user_feedback(video_id);
CREATE INDEX idx_user_feedback_title_id ON user_feedback(title_id);
CREATE INDEX idx_user_feedback_type ON user_feedback(feedback_type);

-- ----------------------------------------------------------------------------
-- 10. SYSTEM SETTINGS TABLE
-- ----------------------------------------------------------------------------
-- Stores system-wide configuration
CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'string',     -- string, integer, boolean, json
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);

-- Insert default settings
INSERT INTO system_settings (key, value, value_type, description) VALUES
    ('max_video_size_mb', '5000', 'integer', 'Maximum video upload size in MB'),
    ('max_video_duration_hours', '3', 'integer', 'Maximum video duration in hours'),
    ('default_titles_count', '5', 'integer', 'Default number of titles to generate'),
    ('trend_cache_ttl_seconds', '3600', 'integer', 'How long to cache trend data'),
    ('groq_whisper_model', 'whisper-large-v3-turbo', 'string', 'Whisper model for transcription'),
    ('groq_llm_model', 'llama-3.3-70b-versatile', 'string', 'LLM model for title generation'),
    ('enable_youtube_trends', 'true', 'boolean', 'Enable YouTube trend fetching'),
    ('enable_google_trends', 'true', 'boolean', 'Enable Google Trends fetching'),
    ('enable_reddit_trends', 'true', 'boolean', 'Enable Reddit trend fetching');


-- ============================================================================
-- VIEWS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- View: Video Processing Summary
-- ----------------------------------------------------------------------------
CREATE VIEW v_video_processing_summary AS
SELECT 
    v.id AS video_id,
    v.original_filename,
    v.file_size_bytes,
    v.duration_seconds AS video_duration,
    v.status,
    v.target_platform,
    v.created_at AS upload_time,
    
    -- Transcript info
    t.word_count,
    t.detected_language,
    t.processing_time_seconds AS transcription_time,
    
    -- Titles count
    COUNT(gt.id) AS titles_generated,
    
    -- Processing job info
    pj.total_processing_time_seconds,
    pj.error_message
    
FROM videos v
LEFT JOIN transcripts t ON v.id = t.video_id
LEFT JOIN generated_titles gt ON v.id = gt.video_id
LEFT JOIN processing_jobs pj ON v.id = pj.video_id
WHERE v.deleted_at IS NULL
GROUP BY v.id, t.id, pj.id;

-- ----------------------------------------------------------------------------
-- View: Active Trends
-- ----------------------------------------------------------------------------
CREATE VIEW v_active_trends AS
SELECT 
    source,
    keyword,
    topic,
    hashtag,
    popularity_score,
    region,
    category,
    fetched_at,
    expires_at
FROM trends_cache
WHERE is_active = true
AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
ORDER BY popularity_score DESC NULLS LAST;

-- ----------------------------------------------------------------------------
-- View: User Usage Statistics
-- ----------------------------------------------------------------------------
CREATE VIEW v_user_usage_stats AS
SELECT 
    u.id AS user_id,
    u.email,
    COUNT(DISTINCT v.id) AS total_videos,
    COUNT(DISTINCT v.id) FILTER (WHERE v.created_at > CURRENT_DATE) AS videos_today,
    COUNT(DISTINCT v.id) FILTER (WHERE v.created_at > date_trunc('month', CURRENT_DATE)) AS videos_this_month,
    SUM(v.file_size_bytes) AS total_bytes_processed,
    AVG(pj.total_processing_time_seconds) AS avg_processing_time
FROM users u
LEFT JOIN videos v ON u.id = v.user_id AND v.deleted_at IS NULL
LEFT JOIN processing_jobs pj ON v.id = pj.video_id
GROUP BY u.id;


-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Function: Update updated_at timestamp
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_jobs_updated_at BEFORE UPDATE ON processing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- Function: Clean expired trends
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION clean_expired_trends()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE trends_cache
    SET is_active = false
    WHERE expires_at < CURRENT_TIMESTAMP
    AND is_active = true;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- Function: Get user daily usage count
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_daily_video_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM videos
        WHERE user_id = p_user_id
        AND created_at >= CURRENT_DATE
        AND deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- Function: Check if user can upload
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION can_user_upload(p_user_id UUID, p_file_size_bytes BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_user users%ROWTYPE;
    v_daily_count INTEGER;
BEGIN
    SELECT * INTO v_user FROM users WHERE id = p_user_id;
    
    IF NOT FOUND OR NOT v_user.is_active THEN
        RETURN false;
    END IF;
    
    -- Check file size
    IF p_file_size_bytes > (v_user.max_video_size_mb * 1024 * 1024) THEN
        RETURN false;
    END IF;
    
    -- Check daily limit
    v_daily_count := get_user_daily_video_count(p_user_id);
    IF v_daily_count >= v_user.daily_video_limit THEN
        RETURN false;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Uncomment to insert sample data for testing
/*
-- Sample user
INSERT INTO users (id, email, name, api_key) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', 'test@example.com', 'Test User', 'test_api_key_12345');

-- Sample trends
INSERT INTO trends_cache (source, keyword, topic, popularity_score, region, expires_at) VALUES
    ('google_trends', 'AI', 'Artificial Intelligence', 95, 'US', CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    ('google_trends', 'ChatGPT', 'AI Chatbots', 90, 'US', CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    ('youtube', 'Tutorial', 'How-to Videos', 85, 'US', CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    ('reddit', 'viral', 'Viral Content', 80, 'US', CURRENT_TIMESTAMP + INTERVAL '1 hour');
*/


-- ============================================================================
-- GRANTS (Adjust based on your database roles)
-- ============================================================================

-- Example grants (uncomment and modify as needed)
/*
-- Create application role
CREATE ROLE app_user LOGIN PASSWORD 'secure_password';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;
*/


-- ============================================================================
-- MAINTENANCE QUERIES (Run periodically)
-- ============================================================================

-- Clean expired trends (run hourly via cron)
-- SELECT clean_expired_trends();

-- Vacuum and analyze for performance (run daily)
-- VACUUM ANALYZE;

-- Reindex if needed (run weekly)
-- REINDEX DATABASE your_database_name;
