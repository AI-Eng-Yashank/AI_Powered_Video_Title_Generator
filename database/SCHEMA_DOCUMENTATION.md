# Video Title Generator - Database Schema Documentation

##  Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           VIDEO TITLE GENERATOR - ERD                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐         ┌─────────────────┐         ┌──────────────────┐
    │   USERS     │         │     VIDEOS      │         │   TRANSCRIPTS    │
    ├─────────────┤         ├─────────────────┤         ├──────────────────┤
    │ id (PK)     │────┐    │ id (PK)         │────┬───▶│ id (PK)          │
    │ email       │    │    │ user_id (FK)    │◀───┘    │ video_id (FK)    │
    │ name        │    └───▶│ original_file   │         │ full_text        │
    │ api_key     │         │ stored_filename │         │ summary          │
    │ daily_limit │         │ file_size_bytes │         │ word_count       │
    │ monthly_lim │         │ duration_secs   │         │ detected_lang    │
    │ max_size_mb │         │ status          │         │ processing_time  │
    │ created_at  │         │ target_platform │         │ created_at       │
    │ updated_at  │         │ created_at      │         └──────────────────┘
    └─────────────┘         │ processed_at    │
           │                └─────────────────┘
           │                        │
           │                        │ 1:N
           │                        ▼
           │                ┌─────────────────┐         ┌──────────────────┐
           │                │GENERATED_TITLES │         │  TRENDS_CACHE    │
           │                ├─────────────────┤         ├──────────────────┤
           │                │ id (PK)         │         │ id (PK)          │
           │                │ video_id (FK)   │         │ source           │
           │                │ title_text      │         │ keyword          │
           │                │ title_style     │         │ topic            │
           │                │ reasoning       │         │ hashtag          │
           │                │ rank_position   │         │ popularity_score │
           │                │ confidence      │         │ region           │
           │                │ is_selected     │         │ expires_at       │
           │                │ user_rating     │         │ is_active        │
           │                │ created_at      │         └──────────────────┘
           │                └─────────────────┘                  │
           │                        │                            │
           │                        │ N:M                        │
           │                        ▼                            │
           │                ┌─────────────────┐                  │
           │                │VIDEO_TRENDS_USED│◀─────────────────┘
           │                ├─────────────────┤
           │                │ id (PK)         │
           │                │ video_id (FK)   │
           │                │ trend_id (FK)   │
           │                │ trend_keyword   │
           │                │ was_incorporated│
           │                └─────────────────┘
           │
           │                ┌─────────────────┐
           │                │PROCESSING_JOBS  │
           │                ├─────────────────┤
           │                │ id (PK)         │
           │                │ video_id (FK)   │◀──── Links to VIDEOS
           │                │ status          │
           │                │ current_step    │
           │                │ progress_%      │
           │                │ error_message   │
           │                │ started_at      │
           │                │ completed_at    │
           │                │ timing_details  │
           │                └─────────────────┘
           │
           │                ┌─────────────────┐
           └───────────────▶│ API_USAGE_LOG   │
                            ├─────────────────┤
                            │ id (PK)         │
                            │ user_id (FK)    │
                            │ video_id (FK)   │
                            │ endpoint        │
                            │ method          │
                            │ api_calls       │
                            │ response_status │
                            │ created_at      │
                            └─────────────────┘

                            ┌─────────────────┐
                            │ USER_FEEDBACK   │
                            ├─────────────────┤
                            │ id (PK)         │
                            │ user_id (FK)    │
                            │ video_id (FK)   │
                            │ title_id (FK)   │
                            │ feedback_type   │
                            │ rating          │
                            │ comment         │
                            └─────────────────┘

                            ┌─────────────────┐
                            │SYSTEM_SETTINGS  │
                            ├─────────────────┤
                            │ key (PK)        │
                            │ value           │
                            │ value_type      │
                            │ description     │
                            └─────────────────┘
```

##  Table Descriptions

### 1. `users`
Stores user account information and usage limits.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `email` | VARCHAR(255) | Unique email address |
| `name` | VARCHAR(255) | User's display name |
| `api_key` | VARCHAR(64) | API authentication key |
| `daily_video_limit` | INTEGER | Max videos per day (default: 10) |
| `monthly_video_limit` | INTEGER | Max videos per month (default: 100) |
| `max_video_size_mb` | INTEGER | Max upload size (default: 500MB) |

### 2. `videos`
Core table storing uploaded video metadata.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key to users |
| `original_filename` | VARCHAR(500) | Original file name |
| `stored_filename` | VARCHAR(255) | Unique stored name |
| `file_size_bytes` | BIGINT | File size in bytes |
| `duration_seconds` | DECIMAL | Video duration |
| `status` | ENUM | Processing status |
| `target_platform` | ENUM | YouTube, TikTok, etc. |

### 3. `transcripts`
Stores transcription results.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `video_id` | UUID | Foreign key to videos |
| `full_text` | TEXT | Complete transcript |
| `summary` | TEXT | AI-generated summary |
| `word_count` | INTEGER | Total words |
| `detected_language` | VARCHAR(10) | Language code (en, es, etc.) |
| `chunks_processed` | INTEGER | Number of audio chunks |

### 4. `generated_titles`
Stores AI-generated titles for each video.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `video_id` | UUID | Foreign key to videos |
| `title_text` | VARCHAR(500) | The generated title |
| `title_style` | ENUM | curiosity, how_to, listicle, etc. |
| `reasoning` | TEXT | Why this title works |
| `rank_position` | INTEGER | Order (1-5) |
| `is_selected` | BOOLEAN | User chose this title |

### 5. `trends_cache`
Caches trending topics from various sources.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `source` | ENUM | google_trends, youtube, reddit |
| `keyword` | VARCHAR(255) | Trending keyword |
| `popularity_score` | INTEGER | Relative popularity |
| `expires_at` | TIMESTAMP | Cache expiration |

### 6. `video_trends_used`
Junction table linking videos to trends used in generation.

| Column | Type | Description |
|--------|------|-------------|
| `video_id` | UUID | Foreign key to videos |
| `trend_id` | UUID | Foreign key to trends_cache |
| `was_incorporated` | BOOLEAN | Was trend used in a title? |

### 7. `processing_jobs`
Tracks video processing progress.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `video_id` | UUID | Foreign key to videos |
| `status` | ENUM | Current job status |
| `progress_percentage` | INTEGER | 0-100% |
| `upload_time_seconds` | DECIMAL | Time for upload step |
| `extraction_time_seconds` | DECIMAL | Time for audio extraction |
| `transcription_time_seconds` | DECIMAL | Time for transcription |

### 8. `api_usage_log`
Logs API usage for analytics and rate limiting.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | UUID | Who made the request |
| `endpoint` | VARCHAR | API endpoint called |
| `groq_whisper_calls` | INTEGER | Whisper API calls made |
| `groq_llm_calls` | INTEGER | LLM API calls made |

### 9. `user_feedback`
Stores user feedback on generated titles.

| Column | Type | Description |
|--------|------|-------------|
| `title_id` | UUID | Which title |
| `feedback_type` | VARCHAR | selected, rejected, edited |
| `edited_title` | VARCHAR | User's modified version |
| `rating` | INTEGER | 1-5 star rating |

### 10. `system_settings`
Key-value store for system configuration.

| Column | Type | Description |
|--------|------|-------------|
| `key` | VARCHAR | Setting name |
| `value` | TEXT | Setting value |
| `value_type` | VARCHAR | string, integer, boolean, json |

---

##  Relationships

```
USERS (1) ──────────────────────┬──────────────────────── (N) VIDEOS
                                │
                                ├──────────────────────── (N) API_USAGE_LOG
                                │
                                └──────────────────────── (N) USER_FEEDBACK

VIDEOS (1) ─────────────────────┬──────────────────────── (1) TRANSCRIPTS
                                │
                                ├──────────────────────── (N) GENERATED_TITLES
                                │
                                ├──────────────────────── (N) VIDEO_TRENDS_USED
                                │
                                ├──────────────────────── (1) PROCESSING_JOBS
                                │
                                └──────────────────────── (N) USER_FEEDBACK

TRENDS_CACHE (1) ───────────────────────────────────────── (N) VIDEO_TRENDS_USED

GENERATED_TITLES (1) ───────────────────────────────────── (N) USER_FEEDBACK
```

---

##  Key Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| `users` | `idx_users_email` | Fast login lookup |
| `users` | `idx_users_api_key` | API authentication |
| `videos` | `idx_videos_status` | Filter by processing status |
| `videos` | `idx_videos_user_id` | Get user's videos |
| `transcripts` | `idx_transcripts_fulltext` | Full-text search |
| `trends_cache` | `idx_trends_active` | Get active trends quickly |

---

##  ENUM Types

### `processing_status`
```sql
'pending' → 'uploading' → 'extracting' → 'transcribing' → 'fetching_trends' → 'generating' → 'completed'
                                                                                           ↘ 'failed'
```

### `platform_type`
```sql
'youtube', 'instagram', 'tiktok', 'twitter', 'general'
```

### `title_style`
```sql
'curiosity', 'how_to', 'listicle', 'story', 'contrarian', 'question', 'news', 'emotional'
```

### `trend_source`
```sql
'google_trends', 'youtube', 'reddit', 'twitter', 'tiktok', 'manual'
```

---

##  Neon DB Setup Instructions

### 1. Create Database in Neon
```
1. Go to https://console.neon.tech
2. Create new project
3. Copy connection string
```

### 2. Run Schema
```bash
# Option 1: Using psql
psql "postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname" -f schema.sql

# Option 2: Using Neon SQL Editor
# Copy schema.sql content and paste in Neon's SQL Editor
```

### 3. Connection String Format
```
postgresql://[user]:[password]@[endpoint].neon.tech/[database]?sslmode=require
```

### 4. Python Connection Example
```python
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = "postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
```

---

##  Maintenance Queries

### Clean expired trends (run hourly)
```sql
SELECT clean_expired_trends();
```

### Get user statistics
```sql
SELECT * FROM v_user_usage_stats WHERE user_id = 'xxx';
```

### Get video processing summary
```sql
SELECT * FROM v_video_processing_summary WHERE video_id = 'xxx';
```

### Get active trends
```sql
SELECT * FROM v_active_trends LIMIT 20;
```
