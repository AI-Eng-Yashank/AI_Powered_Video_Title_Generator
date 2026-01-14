import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check Python version is 3.10+"""
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} (need 3.10+)")
        return False


def check_ffmpeg():
    """Check FFmpeg is installed"""
    print("Checking FFmpeg...", end=" ")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ {version[:50]}...")
            return True
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("❌ Not found - install with: apt install ffmpeg (or brew install ffmpeg)")
    return False


def check_imports():
    """Check all required packages can be imported"""
    packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("groq", "Groq (LLM + Whisper)"),
        ("sqlalchemy", "SQLAlchemy"),
        ("psycopg2", "psycopg2 (PostgreSQL)"),
        ("pytrends.request", "pytrends"),
        ("pydantic", "Pydantic"),
        ("aiofiles", "aiofiles"),
        ("cachetools", "cachetools"),
    ]
    
    all_ok = True
    print("\nChecking Python packages:")
    
    for module, name in packages:
        print(f"  {name}...", end=" ")
        try:
            __import__(module)
            print("✅")
        except ImportError as e:
            print(f"❌ Not installed")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Check .env file exists and has required keys"""
    print("\nChecking .env configuration...")
    env_path = Path(".env")
    
    if not env_path.exists():
        print("  ⚠️  .env file not found")
        print("     Copy .env.example to .env and add your API keys")
        return False
    
    content = env_path.read_text()
    
    required = [("GROQ_API_KEY", True)]
    optional = [
        ("DATABASE_URL", True),
        ("YOUTUBE_API_KEY", False),
        ("REDDIT_CLIENT_ID", False),
    ]
    
    all_required_ok = True
    
    for key, is_required in required + optional:
        if key in content:
            lines = [l for l in content.split('\n') if l.startswith(f"{key}=")]
            if lines:
                value = lines[0].split("=", 1)[1] if "=" in lines[0] else ""
                # Check it's not placeholder or empty
                if value and "your_" not in value.lower() and value != "":
                    print(f"  ✅ {key} configured")
                else:
                    if is_required:
                        print(f"  ❌ {key} not set (required)")
                        all_required_ok = False
                    else:
                        print(f"  ⚠️  {key} not set (optional)")
            else:
                if is_required:
                    print(f"  ❌ {key} not found (required)")
                    all_required_ok = False
        else:
            if is_required:
                print(f"  ❌ {key} not found (required)")
                all_required_ok = False
            else:
                print(f"  ⚠️  {key} not found (optional)")
    
    return all_required_ok


def check_database():
    """Check database connection"""
    print("\nChecking database connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("  ⚠️  DATABASE_URL not configured")
            return True  # Not critical for basic operation
        
        import psycopg2
        conn = psycopg2.connect(database_url)
        
        # Check if tables exist
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'users'
        """)
        tables_exist = cur.fetchone()[0] > 0
        
        conn.close()
        
        if tables_exist:
            print("  ✅ Database connected and schema exists")
        else:
            print("  ✅ Database connected")
            print("  ⚠️  Schema not created yet - run: python database/init_db.py")
        
        return True
        
    except ImportError:
        print("  ⚠️  psycopg2 not installed")
        return True
    except Exception as e:
        print(f"  ❌ Connection failed: {str(e)[:50]}")
        return False


def check_directories():
    """Check required directories exist"""
    print("\nChecking directories...")
    
    dirs = ["uploads", "outputs"]
    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f"  ✅ {d}/")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {d}/ (created)")
    
    return True


def main():
    print("=" * 50)
    print("Video Title Generator - Setup Verification")
    print("=" * 50)
    print()
    
    checks = [
        check_python_version(),
        check_ffmpeg(),
        check_imports(),
        check_env_file(),
        check_database(),
        check_directories(),
    ]
    
    print()
    print("=" * 50)
    
    if all(checks):
        print("✅ All checks passed! Ready to run.")
        print()
        print("Start the server with:")
        print("  uvicorn app.main:app --reload")
        print()
        print("Then open: http://localhost:8000/docs")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
