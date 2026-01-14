#  AI-Powered Video Title Generator

A production-ready FastAPI system that generates **trend-aware, click-optimized video titles** from video content using AI. Upload any video, get viral-worthy titles optimized for YouTube, TikTok, Instagram, or Twitter.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

---

##  Table of Contents

- [Features](#-features)
- [How It Works](#-how-it-works)
- [System Architecture](#-system-architecture)
- [User Guide](#-user-guide)
- [Developer Guide](#-developer-guide)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Database Schema](#-database-schema)
- [Problems & Solutions](#-problems--solutions)
- [Performance Benchmarks](#-performance-benchmarks)
- [Extending the System](#-extending-the-system)
- [Troubleshooting](#-troubleshooting)

---

##  Features

| Feature | Description |
|---------|-------------|
|  **Video Processing** | Upload MP4, MOV, AVI, MKV, WebM, FLV, WMV (up to 5GB) |
|  **AI Transcription** | Automatic speech-to-text via Groq Whisper API |
|  **Trend Intelligence** | Real-time trends from Google, YouTube, Reddit |
|  **AI Title Generation** | 5 unique titles with different styles per video |
|  **Platform Optimization** | Titles tailored for YouTube, TikTok, Instagram, Twitter |
|  **Database Integration** | Neon DB (PostgreSQL) for data persistence |
|  **Fast Processing** | ~1 minute for 10-minute videos |

### Large File Support (3GB+ Videos)

```
┌─────────────────────────────────────────────────────────────────┐
│               LARGE VIDEO PROCESSING PIPELINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  3GB Video ──▶ Extract ──▶ Compress ──▶ Chunk ──▶ Transcribe  │
│                 50MB        <25MB                               │
│                                                                 │
│  Compression: 60-100x size reduction (3GB → 30-50MB)            │
│  Chunking: Auto-split if audio > 25MB                           │
│  Merging: Seamless transcript with context continuity           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

##  How It Works

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│    VIDEO   ────▶   AUDIO ────▶   TEXT  ────▶    TITLES         │
│                                                                  │
│  Upload        Extract &      Transcribe     Generate with      │
│  Video         Compress       with Whisper   Trends + AI        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Processing

```
STEP 1: VIDEO UPLOAD (~5-30 sec)
══════════════════════════════════════════════════════════════════
User uploads video file
       │
       ├──▶ Validate Format (mp4, mov, avi, mkv, webm, flv, wmv)
       ├──▶ Validate Size (< 5GB limit)
       ├──▶ Generate UUID (unique filename: abc123.mp4)
       └──▶ Save to Disk (/uploads/abc123.mp4)


STEP 2: AUDIO EXTRACTION (~10-30 sec)
══════════════════════════════════════════════════════════════════
FFmpeg Command:
┌────────────────────────────────────────────────────────────────┐
│ ffmpeg -i video.mp4 -vn -c:a libopus -b:a 32k -ar 16000 out.ogg│
└────────────────────────────────────────────────────────────────┘

Parameters:
• -vn          : Remove video track (audio only)
• -c:a libopus : Opus codec (best compression for speech)
• -b:a 32k     : 32kbps bitrate (sufficient for speech)
• -ar 16000    : 16kHz sample rate (Whisper optimal)

Result: 500MB Video ──▶ 5MB Audio (100x compression!)


STEP 3: TRANSCRIPTION (~20-60 sec)
══════════════════════════════════════════════════════════════════
                    AUDIO SIZE CHECK
                          │
            ┌─────────────┴─────────────┐
            │                           │
       < 25MB                       > 25MB
            │                           │
            ▼                           ▼
    ┌───────────────┐         ┌───────────────┐
    │ Direct Upload │         │ Smart Chunking│
    │ to Groq API   │         │ (10 min each) │
    └───────┬───────┘         └───────┬───────┘
            │                         │
            │                    Split into:
            │                    Chunk 1 (0-10m)
            │                    Chunk 2 (10-20m)
            │                    Chunk N (...)
            │                         │
            │                    Transcribe Each
            │                    with Context
            │                         │
            │                    Merge Results
            │                         │
            └────────────┬────────────┘
                         │
                         ▼
    Output: { "text": "...", "language": "en", "word_count": 1569 }


STEP 4: TREND FETCHING (~5-10 sec) - Parallel
══════════════════════════════════════════════════════════════════
     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │   Google    │    │   YouTube   │    │   Reddit    │
     │   Trends    │    │   API       │    │   API       │
     └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
            │                  │                  │
            ▼                  ▼                  ▼
       ["AI tools",      ["tutorial",      ["viral",
        "ChatGPT",        "tech review",    "TIL",
        "2024"]           "how to"]         "lifehack"]
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
              AGGREGATED: ["AI", "ChatGPT", "tutorial", ...]


STEP 5: AI TITLE GENERATION (~10-20 sec)
══════════════════════════════════════════════════════════════════
┌────────────────────────────────────────────────────────────────┐
│ PROMPT TO GROQ LLM:                                            │
│                                                                │
│ SYSTEM: You are an expert video title strategist...           │
│                                                                │
│ USER:                                                          │
│ TRANSCRIPT: "Hey everyone, welcome back to my channel..."     │
│ TRENDING: AI, ChatGPT, tutorial, viral, productivity          │
│ PLATFORM: YouTube (max 70 characters)                          │
│                                                                │
│ Generate 5 unique titles:                                      │
│ 1. Curiosity - Create intrigue                                 │
│ 2. How-to - Educational/tutorial                               │
│ 3. Listicle - Number-based                                     │
│ 4. Story - Personal narrative                                  │
│ 5. Contrarian - Challenge assumptions                          │
└────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│ GENERATED TITLES:                                              │
│                                                                │
│ 1. "Siri's Big Update" (curiosity)                            │
│ 2. "How Apple Fixed Siri" (how-to)                            │
│ 3. "5 Ways Apple's AI Crisis Ends" (listicle)                 │
│ 4. "I Reacted to Apple's Siri News" (story)                   │
│ 5. "Why Apple's AI Failure Isn't Surprising" (contrarian)     │
└────────────────────────────────────────────────────────────────┘


STEP 6: RESPONSE
══════════════════════════════════════════════════════════════════
{
  "success": true,
  "video_filename": "5b1af6ad0193.mp4",
  "transcript": { "text": "...", "word_count": 1569 },
  "generated_titles": [...],
  "transcript_summary": "Apple is partnering with Google...",
  "processing_time_seconds": 54.82
}
```

---

##  System Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                           CLIENT LAYER                               │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │ │
│  │  │ Swagger UI │  │  cURL/CLI  │  │ Custom App │  │ Mobile App │    │ │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘    │ │
│  │        └───────────────┴───────────────┴───────────────┘           │ │
│  └──────────────────────────────────┬──────────────────────────────────┘ │
│                                     │                                     │
│                                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                      API LAYER (FastAPI)                             │ │
│  │                                                                      │ │
│  │  POST /api/v1/generate-titles    POST /api/v1/transcribe            │ │
│  │  POST /api/v1/generate-from-text GET  /api/v1/trends                │ │
│  │  GET  /api/v1/status             GET  /health                       │ │
│  │                                                                      │ │
│  └──────────────────────────────────┬──────────────────────────────────┘ │
│                                     │                                     │
│                                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                     ORCHESTRATION LAYER                              │ │
│  │                                                                      │ │
│  │  • Coordinates workflow between modules                             │ │
│  │  • Handles errors and cleanup                                       │ │
│  │  • Manages temporary files                                          │ │
│  │                                                                      │ │
│  └─────┬────────┬────────┬────────┬────────┬───────────────────────────┘ │
│        │        │        │        │        │                              │
│        ▼        ▼        ▼        ▼        ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         MODULE LAYER                                 │ │
│  │                                                                      │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │ │
│  │  │  Video   │ │  Audio   │ │ Transcr. │ │  Trend   │ │  Title   │  │ │
│  │  │  Upload  │ │ Extract  │ │  Module  │ │  Intel   │ │   Gen    │  │ │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │ │
│  │       │            │            │            │            │        │ │
│  │       ▼            ▼            ▼            ▼            ▼        │ │
│  │   [Disk]       [FFmpeg]    [Groq API]   [External]   [Groq API]   │ │
│  │                            (Whisper)      APIs         (LLM)      │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                     │                                     │
│                                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                          DATA LAYER                                  │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │                   Neon DB (PostgreSQL)                        │   │ │
│  │  │                                                               │   │ │
│  │  │  users │ videos │ transcripts │ generated_titles │ trends    │   │ │
│  │  │                                                               │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### Module Dependency Graph

```
                         ┌─────────────────┐
                         │   main.py       │
                         │   (FastAPI)     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   router.py     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ orchestration   │
                         └────────┬────────┘
                                  │
       ┌──────────┬───────────────┼───────────────┬──────────┐
       │          │               │               │          │
       ▼          ▼               ▼               ▼          ▼
┌───────────┐┌───────────┐┌───────────┐┌───────────┐┌───────────┐
│  video    ││  audio    ││ transcr.  ││  trend    ││  title    │
│  upload   ││ extract   ││  module   ││  intel    ││   gen     │
└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘└─────┬─────┘
      │            │            │            │            │
      ▼            ▼            ▼            ▼            ▼
  [Disk]       [FFmpeg]    [Groq API]   [External]   [Groq API]
                                          APIs
```

---

##  User Guide

### Getting Started

**Step 1: Access the System**
```
Open browser → http://localhost:8000/docs
```

**Step 2: Upload Video**
```
┌────────────────────────────────────────────────────────────┐
│  POST /api/v1/generate-titles     [Try it out]             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  video*        [Choose File] my_video.mp4  ← Required     │
│  platform      [youtube ▼]                  ← Select one   │
│  num_titles    [5        ]                  ← 1-10 titles  │
│  skip_trends   [ ]                          ← Optional     │
│                                                            │
│  [Execute]                                                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Step 3: Wait for Processing**

| Video Duration | Processing Time |
|----------------|-----------------|
| 2 minutes | ~30 seconds |
| 5 minutes | ~45 seconds |
| 10 minutes | ~1 minute |
| 30 minutes | ~2-3 minutes |
| 1 hour | ~4-5 minutes |

**Step 4: Get Results**
```json
{
  "success": true,
  "generated_titles": [
    {
      "title": "Siri's Big Update",
      "style": "curiosity",
      "reasoning": "Creates intrigue without revealing details"
    },
    {
      "title": "How Apple Fixed Siri",
      "style": "how-to",
      "reasoning": "Educational angle, clear value proposition"
    }
  ],
  "transcript": {
    "text": "Full transcript...",
    "word_count": 1569,
    "language": "English"
  },
  "processing_time_seconds": 54.82
}
```

### Platform Guidelines

| Platform | Max Length | Style |
|----------|------------|-------|
| **YouTube** | 70 chars | SEO-focused, keyword-rich |
| **TikTok** | 150 chars | Hook-driven, trend-aware |
| **Instagram** | Varies | Story-driven, emotional |
| **Twitter** | 280 chars | Punchy, engagement-focused |

---

##  Developer Guide

### Project Structure

```
video-title-generator/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Environment configuration
│   ├── database.py             # Neon DB connection
│   ├── modules/
│   │   ├── video_upload.py     # Video validation & storage
│   │   ├── audio_extraction.py # FFmpeg audio extraction
│   │   ├── transcription.py    # Groq Whisper integration
│   │   ├── trend_intelligence.py # Multi-source trends
│   │   ├── title_generation.py # Groq LLM titles
│   │   └── orchestration.py    # Workflow coordination
│   ├── routers/
│   │   └── video.py            # API routes
│   └── schemas/
│       └── models.py           # Pydantic models
├── database/
│   ├── schema.sql              # PostgreSQL schema
│   ├── models.py               # SQLAlchemy ORM
│   └── init_db.py              # DB initialization
├── .env                        # Environment variables
├── requirements.txt            # Dependencies
└── check_setup.py              # Setup verification
```

### Module Responsibilities

| Module | Responsibilities |
|--------|------------------|
| **video_upload.py** | Validate format, enforce size limits, generate UUID, stream to disk |
| **audio_extraction.py** | FFmpeg extraction, OGG compression, timeout handling |
| **transcription.py** | Groq Whisper API, chunking for large files, context continuity |
| **trend_intelligence.py** | Google/YouTube/Reddit trends, caching (1hr TTL), graceful degradation |
| **title_generation.py** | Prompt engineering, Groq LLM, 5 title styles, JSON parsing |
| **orchestration.py** | Coordinate modules, error handling, cleanup, timing |

---

##  Installation

### Prerequisites

- Python 3.10+
- FFmpeg
- Groq API Key (free at https://console.groq.com)

### Quick Start

```bash
# 1. Extract and enter project
unzip video-title-generator.zip
cd video-title-generator

# 2. Create virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (add GROQ_API_KEY)
# Edit .env file

# 5. Initialize database
python database/init_db.py

# 6. Verify setup
python check_setup.py

# 7. Run server
uvicorn app.main:app --reload
```

### Windows FFmpeg Installation

```powershell
# Install via Winget
winget install FFmpeg

# Add to PATH (if needed)
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"

# Verify
ffmpeg -version
```

---

##  Configuration

### Environment Variables

```env
# REQUIRED
GROQ_API_KEY=gsk_xxxxxxxxxxxx          # Get from console.groq.com

# DATABASE
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# OPTIONAL - AI Models
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_WHISPER_MODEL=whisper-large-v3-turbo

# OPTIONAL - Trend Sources
YOUTUBE_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# OPTIONAL - Server
MAX_UPLOAD_SIZE_MB=5000
TREND_CACHE_TTL=3600
```

### Whisper Models

| Model | Speed | Accuracy | Languages |
|-------|-------|----------|-----------|
| `whisper-large-v3-turbo` |  Fast | ★★★★☆ | 99+ |
| `whisper-large-v3` | Medium | ★★★★★ | 99+ |
| `distil-whisper-large-v3-en` |  Fastest | ★★★★☆ | English |

---

##  API Reference

### POST /api/v1/generate-titles

Generate titles from uploaded video.

**Request:**
```
Content-Type: multipart/form-data

video*       : File (MP4, MOV, etc.)
platform     : youtube | instagram | tiktok | twitter
num_titles   : 1-10 (default: 5)
skip_trends  : boolean
```

**Response:**
```json
{
  "success": true,
  "video_filename": "abc123.mp4",
  "transcript": {
    "text": "Full transcript...",
    "language": "English",
    "duration_seconds": 502.21,
    "word_count": 1569
  },
  "generated_titles": [
    {
      "title": "Siri's Big Update",
      "style": "curiosity",
      "reasoning": "Creates intrigue..."
    }
  ],
  "processing_time_seconds": 54.82
}
```

### Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/transcribe` | Transcribe only |
| POST | `/api/v1/generate-from-text` | Titles from text |
| GET | `/api/v1/trends` | Current trends |
| GET | `/api/v1/status` | System status |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

---

##  Database Schema

### Entity Relationships

```
┌─────────────┐       ┌─────────────┐       ┌──────────────┐
│   USERS     │       │   VIDEOS    │       │ TRANSCRIPTS  │
├─────────────┤       ├─────────────┤       ├──────────────┤
│ id (PK)     │──┐    │ id (PK)     │──────▶│ id (PK)      │
│ email       │  │    │ user_id(FK) │◀──┐   │ video_id(FK) │
│ api_key     │  └───▶│ filename    │   │   │ full_text    │
│ limits      │       │ status      │   │   │ language     │
└─────────────┘       └─────────────┘   │   └──────────────┘
                            │           │
                            │ 1:N       │
                            ▼           │
                      ┌─────────────────┐
                      │GENERATED_TITLES │
                      ├─────────────────┤
                      │ id (PK)         │
                      │ video_id (FK)   │────┘
                      │ title_text      │
                      │ style           │
                      │ reasoning       │
                      └─────────────────┘
```

### Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts, API keys, limits |
| `videos` | Uploaded video metadata, status |
| `transcripts` | Full text, language, word count |
| `generated_titles` | AI titles with style/reasoning |
| `trends_cache` | Cached trends (1hr TTL) |
| `processing_jobs` | Job tracking, progress |
| `api_usage_log` | Analytics, monitoring |

---

## 🔧 Problems & Solutions

### Problem 1: FFmpeg Not Found on Windows

```
Symptom:
'ffmpeg' is not recognized as the name of a cmdlet...

Cause:
Winget installs FFmpeg but PATH update requires shell restart

Solution:
1. Find FFmpeg: 
   dir "C:\Users\$env:USERNAME\AppData\Local\Microsoft\WinGet\Packages\*ffmpeg*"

2. Add to PATH:
   $env:Path += ";C:\...\ffmpeg-8.0.1-full_build\bin"

3. Or restart VS Code/PowerShell
```

### Problem 2: Groq Whisper 25MB Limit

```
Symptom:
HTTP 413: Request Entity Too Large

Cause:
Long videos produce audio > 25MB

Solution (Auto-handled):
1. Aggressive Compression: OGG Opus 32kbps (100x reduction)
2. Smart Chunking: Split into 10-minute segments
3. Context Merging: Pass last 200 chars as context prompt
```

### Problem 3: PATH Not Updated in VS Code

```
Symptom:
FFmpeg installed but still not found

Cause:
VS Code terminal inherits PATH from when opened

Solution:
1. Click trash icon 🗑️ to kill terminal
2. Open new terminal: Ctrl + `
3. Reactivate venv: venv\Scripts\activate
```

### Problem 4: Empty Trends

```
Symptom:
"trends": [] in response

Cause:
YOUTUBE_API_KEY and REDDIT_CLIENT_ID not configured

Solution:
This is expected! Trends are optional.
System works perfectly without them.
Add API keys to .env for enhanced results.
```

---

##  Performance Benchmarks

### Processing Time

| Video Size | Duration | Total Time |
|------------|----------|------------|
| 50 MB | ~2 min | ~30 sec |
| 200 MB | ~8 min | ~1 min |
| 500 MB | ~15 min | ~1.5 min |
| 1 GB | ~25 min | ~2 min |
| 2 GB | ~45 min | ~3.5 min |
| 3 GB | ~60 min | ~5 min |

### Compression Ratios

| Original | Compressed | Ratio |
|----------|------------|-------|
| 500 MB video | 5 MB audio | 100:1 |
| 1 GB video | 10 MB audio | 100:1 |
| 3 GB video | 30 MB audio | 100:1 |

---

##  Extending the System

### Add New Trend Source

```python
# In trend_intelligence.py

class TikTokTrendsSource(BaseTrendSource):
    source_name = "tiktok"
    
    def is_configured(self) -> bool:
        return bool(self.settings.tiktok_api_key)
    
    def fetch_trends(self, category=None) -> TrendData:
        # Your implementation
        return TrendData(source=self.source_name, keywords=[...])

# Register in __init__:
self.sources.append(TikTokTrendsSource())
```

### Add New Platform

```python
# In title_generation.py

PLATFORM_CONFIGS = {
    "linkedin": {
        "max_length": 150,
        "style_emphasis": "professional",
        "prompt_addition": "Use B2B language."
    }
}
```

---

##  Troubleshooting

| Issue | Solution |
|-------|----------|
| `FFmpeg not found` | Install FFmpeg, add to PATH |
| `GROQ_API_KEY not configured` | Add key to `.env` file |
| `413 Request Entity Too Large` | Auto-handled by chunking |
| `Empty transcription` | Check source video audio |
| `Database connection failed` | Verify DATABASE_URL |
| `Timeout error` | Auto-scaled for large files |

### Quick Diagnostics

```bash
# Run setup check
python check_setup.py

# Health check
curl http://localhost:8000/health

# Full status
curl http://localhost:8000/api/v1/status
```

---

## Acknowledgments

- **Groq** - Lightning-fast AI inference
- **FFmpeg** - Media processing
- **FastAPI** - Web framework
- **Neon DB** - Serverless PostgreSQL

---

**Built for content creators who want viral-worthy titles**
