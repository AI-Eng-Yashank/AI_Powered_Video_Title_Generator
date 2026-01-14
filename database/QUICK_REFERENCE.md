#  Video Title Generator - Database Quick Reference

## For Fellow Developer - Setup Instructions

### 1. Create Neon DB Project

```
1. Go to https://console.neon.tech
2. Sign up / Log in
3. Click "New Project"
4. Name: video-title-generator
5. Region: Choose closest to your server
6. Copy the connection string
```

### 2. Connection String Format

```
postgresql://[user]:[password]@[endpoint].neon.tech/[database]?sslmode=require
```

Example:
```
postgresql://alex:AbC123xyz@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### 3. Run Schema

**Option A: Neon SQL Editor (Easiest)**
```
1. Go to Neon Console → Your Project → SQL Editor
2. Copy entire contents of schema.sql
3. Paste and click "Run"
```

**Option B: Command Line**
```bash
psql "postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require" -f schema.sql
```

**Option C: Python Script**
```python
import psycopg2

conn = psycopg2.connect("postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require")
cur = conn.cursor()

with open('schema.sql', 'r') as f:
    cur.execute(f.read())

conn.commit()
conn.close()
```

---

##  Tables Overview (10 Tables)

| # | Table | Purpose | Key Columns |
|---|-------|---------|-------------|
| 1 | `users` | User accounts | email, api_key, limits |
| 2 | `videos` | Uploaded videos | filename, size, status, platform |
| 3 | `transcripts` | Video transcriptions | full_text, language, word_count |
| 4 | `generated_titles` | AI titles | title_text, style, ranking |
| 5 | `trends_cache` | Cached trends | keyword, source, popularity |
| 6 | `video_trends_used` | Video↔Trend links | video_id, trend_id |
| 7 | `processing_jobs` | Job tracking | status, progress, timing |
| 8 | `api_usage_log` | API analytics | endpoint, calls, response |
| 9 | `user_feedback` | Title feedback | rating, edited_title |
| 10 | `system_settings` | Config store | key, value |

---

##  Key Relationships

```
users (1) ───→ (N) videos ───→ (1) transcripts
                    │
                    ├──→ (N) generated_titles
                    │
                    ├──→ (1) processing_jobs
                    │
                    └──→ (N) video_trends_used ←─── trends_cache
```

---

## ENUM Values

### processing_status
```sql
'pending', 'uploading', 'extracting', 'transcribing', 
'fetching_trends', 'generating', 'completed', 'failed'
```

### platform_type
```sql
'youtube', 'instagram', 'tiktok', 'twitter', 'general'
```

### title_style
```sql
'curiosity', 'how_to', 'listicle', 'story', 
'contrarian', 'question', 'news', 'emotional'
```

### trend_source
```sql
'google_trends', 'youtube', 'reddit', 'twitter', 'tiktok', 'manual'
```

---

##  Test Queries

### Check tables exist
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

### Insert test user
```sql
INSERT INTO users (email, name, api_key) 
VALUES ('test@example.com', 'Test User', 'test_key_123')
RETURNING *;
```

### Check ENUMs exist
```sql
SELECT typname FROM pg_type WHERE typtype = 'e';
```

---

##  Environment Variables Needed

```env
# Add to .env file
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require

# Or separate values
DB_HOST=ep-xxx.neon.tech
DB_NAME=neondb
DB_USER=your_user
DB_PASSWORD=your_password
DB_PORT=5432
```

---

##  Files Provided

```
database/
├── schema.sql              # Full PostgreSQL schema (run this!)
├── SCHEMA_DOCUMENTATION.md # Detailed ERD and docs
├── models.py               # SQLAlchemy Python models
└── QUICK_REFERENCE.md      # This file
```

---

##  Quick Commands

```sql
-- Count all videos
SELECT COUNT(*) FROM videos;

-- Get pending jobs
SELECT * FROM processing_jobs WHERE status = 'pending';

-- Get active trends
SELECT * FROM v_active_trends LIMIT 10;

-- User stats
SELECT * FROM v_user_usage_stats;

-- Clean expired trends
SELECT clean_expired_trends();
```

---

##  Troubleshooting

### "relation does not exist"
→ Run schema.sql first

### "type does not exist" 
→ ENUMs not created, run full schema.sql

### Connection refused
→ Check IP allowlist in Neon console
→ Check sslmode=require in connection string

### Timeout errors
→ Neon pauses inactive databases after 5 min
→ First query after pause may be slow

---

##  Verification Checklist

After running schema.sql, verify:

- [ ] 10 tables created
- [ ] 4 ENUM types created  
- [ ] 3 views created
- [ ] Indexes created
- [ ] Functions created
- [ ] Default settings inserted

```sql
-- Quick verification
SELECT 
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as tables,
    (SELECT COUNT(*) FROM pg_type WHERE typtype = 'e') as enums,
    (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public') as views;
```

Expected: `tables=10, enums=4, views=3`
