# 🚀 How to Run Video Title Generator

## Quick Start (5 Minutes)

### Step 1: Prerequisites

Make sure you have installed:

```bash
# Check Python (need 3.10+)
python3 --version

# Check FFmpeg
ffmpeg -version

# If FFmpeg not installed:
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows - Download from https://ffmpeg.org/download.html
```

### Step 2: Setup Project

```bash
# 1. Unzip and enter project
unzip video-title-generator.zip
cd video-title-generator

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

Edit the `.env` file and add your **Groq API key**:

```bash
# Open .env file
nano .env   # or use any text editor
```

**Required: Add your Groq API key**
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get your free Groq API key at: https://console.groq.com

### Step 4: Setup Database

```bash
# Run database schema (one-time setup)
# Option 1: Using Python
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://neondb_owner:npg_hIRz9jMt0sfO@ep-nameless-waterfall-ad6efja6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require')
cur = conn.cursor()
with open('database/schema.sql', 'r') as f:
    cur.execute(f.read())
conn.commit()
print('✅ Database schema created!')
conn.close()
"

# Option 2: Using psql (if installed)
psql "postgresql://neondb_owner:npg_hIRz9jMt0sfO@ep-nameless-waterfall-ad6efja6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require" -f database/schema.sql
```

### Step 5: Verify Setup

```bash
python check_setup.py
```

Expected output:
```
✅ Python 3.10+
✅ FFmpeg installed
✅ All packages installed
✅ GROQ_API_KEY configured
✅ Ready to run!
```

### Step 6: Run the Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# OR Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step 7: Test the API

Open your browser: **http://localhost:8000/docs**

You'll see the Swagger UI where you can:
1. Upload a video
2. Select platform (YouTube, TikTok, etc.)
3. Generate titles!

---

## 📋 Complete Command Summary

```bash
# One-liner setup (Linux/macOS)
unzip video-title-generator.zip && \
cd video-title-generator && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
echo "GROQ_API_KEY=your_key_here" >> .env && \
python check_setup.py && \
uvicorn app.main:app --reload
```

---

## 🔧 Configuration Details

### Required Configuration

| Variable | How to Get | Notes |
|----------|------------|-------|
| `GROQ_API_KEY` | https://console.groq.com | **Required** - Free tier available |

### Optional Configuration (Improves Trend Quality)

| Variable | How to Get | Notes |
|----------|------------|-------|
| `YOUTUBE_API_KEY` | Google Cloud Console | Free 10,000 calls/day |
| `REDDIT_CLIENT_ID` | reddit.com/prefs/apps | Free unlimited |
| `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps | Free unlimited |

---

## 🌐 API Endpoints

Once running, these endpoints are available:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/generate-titles` | Upload video → Get titles |
| `POST` | `/api/v1/transcribe` | Upload video → Get transcript only |
| `POST` | `/api/v1/generate-from-text` | Submit text → Get titles |
| `GET` | `/api/v1/trends` | Get current trends |
| `GET` | `/api/v1/status` | System status |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |

---

## 🧪 Test with cURL

```bash
# Health check
curl http://localhost:8000/health

# Generate titles from video
curl -X POST "http://localhost:8000/api/v1/generate-titles" \
  -F "video=@your_video.mp4" \
  -F "platform=youtube" \
  -F "num_titles=5"

# Generate titles from text
curl -X POST "http://localhost:8000/api/v1/generate-from-text" \
  -F "transcript=Your video transcript text here..." \
  -F "platform=youtube" \
  -F "num_titles=5"
```

---

## 🐛 Troubleshooting

### "GROQ_API_KEY not configured"
```bash
# Edit .env and add your key
echo "GROQ_API_KEY=gsk_your_actual_key" >> .env
```

### "FFmpeg not found"
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### "Module not found" errors
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database connection error
```bash
# Test connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://neondb_owner:npg_hIRz9jMt0sfO@ep-nameless-waterfall-ad6efja6-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require')
print('✅ Connected!')
conn.close()
"
```

### Port already in use
```bash
# Use different port
uvicorn app.main:app --reload --port 8001
```

---

## 📁 Project Structure

```
video-title-generator/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── modules/
│   │   ├── video_upload.py      # Video upload handling
│   │   ├── audio_extraction.py  # FFmpeg audio extraction
│   │   ├── transcription.py     # Groq Whisper transcription
│   │   ├── trend_intelligence.py # Trend fetching
│   │   ├── title_generation.py  # Groq LLM title generation
│   │   └── orchestration.py     # Workflow coordination
│   ├── routers/
│   │   └── video.py         # API endpoints
│   └── schemas/
│       └── models.py        # Pydantic models
├── database/
│   ├── schema.sql           # PostgreSQL schema
│   ├── models.py            # SQLAlchemy models
│   └── *.md                 # Documentation
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── check_setup.py           # Setup verification
└── test_api.py              # API test client
```

---

## 🚀 Running in Production (AWS)

### EC2 Setup

```bash
# 1. Launch EC2 (t3.medium recommended)
# 2. SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Install dependencies
sudo apt update
sudo apt install python3.10 python3-pip python3-venv ffmpeg

# 4. Upload and setup project
# ... same as above ...

# 5. Run with Gunicorn (production)
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 6. (Optional) Setup systemd service for auto-restart
```

### Using Docker (Alternative)

```bash
# Build
docker build -t video-title-generator .

# Run
docker run -d -p 8000:8000 --env-file .env video-title-generator
```

---

## ✅ Success Checklist

- [ ] Python 3.10+ installed
- [ ] FFmpeg installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file has `GROQ_API_KEY`
- [ ] Database schema created
- [ ] Server running (`uvicorn app.main:app --reload`)
- [ ] Can access http://localhost:8000/docs

**You're ready to generate titles! 🎉**
