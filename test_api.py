import httpx
import sys
from pathlib import Path


BASE_URL = "http://localhost:8000"


def check_health():
    """Check if the server is running."""
    print("Checking server health...")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data['status']}")
            print(f"  Whisper Model: {data['whisper_model']}")
            print(f"  Groq Configured: {data['groq_configured']}")
            print(f"  YouTube Configured: {data['youtube_configured']}")
            print(f"  Reddit Configured: {data['reddit_configured']}")
            return True
        else:
            print(f"  ❌ Server returned status {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"  ❌ Cannot connect to {BASE_URL}")
        print("     Make sure the server is running: uvicorn app.main:app --reload")
        return False


def get_trends():
    """Fetch current trends."""
    print("\nFetching current trends...")
    try:
        response = httpx.get(f"{BASE_URL}/api/v1/trends", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"  Sources fetched: {len(data['sources'])}")
            for source in data['sources']:
                print(f"    - {source['source']}: {len(source['keywords'])} keywords")
            print(f"  Top aggregated keywords: {data['aggregated_keywords'][:5]}")
            return True
        else:
            print(f"  ❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def generate_titles_from_text(transcript: str, platform: str = "youtube"):
    """Generate titles from a text transcript."""
    print(f"\nGenerating titles for {platform}...")
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/v1/generate-from-text",
            data={
                "transcript": transcript,
                "platform": platform,
                "num_titles": 5,
                "include_trends": True
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Summary: {data['transcript_summary'][:100]}...")
            print(f"  Trends used: {data['trends_used']}")
            print("\n  Generated Titles:")
            for i, title in enumerate(data['titles'], 1):
                print(f"    {i}. [{title['style']}] {title['title']}")
            return True
        else:
            print(f"  ❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def generate_titles_from_video(video_path: str, platform: str = "youtube"):
    """Generate titles from a video file."""
    path = Path(video_path)
    
    if not path.exists():
        print(f"❌ Video file not found: {video_path}")
        return False
    
    print(f"\nProcessing video: {path.name}")
    print(f"  Size: {path.stat().st_size / (1024*1024):.2f} MB")
    print("  This may take a few minutes...")
    
    try:
        with open(path, "rb") as f:
            response = httpx.post(
                f"{BASE_URL}/api/v1/generate-titles",
                files={"video": (path.name, f, "video/mp4")},
                data={
                    "platform": platform,
                    "num_titles": 5,
                    "skip_trends": False
                },
                timeout=300  # 5 minute timeout for video processing
            )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n  ✅ Processing complete!")
            print(f"  Processing time: {data['processing_time_seconds']:.2f}s")
            print(f"  Transcript: {data['transcript']['word_count']} words")
            print(f"  Language: {data['transcript']['language']}")
            print(f"  Summary: {data['transcript_summary'][:150]}...")
            print("\n  Generated Titles:")
            for i, title in enumerate(data['generated_titles'], 1):
                print(f"    {i}. [{title['style']}] {title['title']}")
            return True
        else:
            print(f"  ❌ Failed: {response.text[:500]}")
            return False
            
    except httpx.ReadTimeout:
        print("  ❌ Request timed out. Video may be too long.")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Video Title Generator - API Client")
    print("=" * 60)
    
    # Check server health
    if not check_health():
        return 1
    
    # Get trends
    get_trends()
    
    # Sample transcript for testing
    sample_transcript = """
    Today I'm going to show you how I built a complete AI-powered application 
    from scratch using Python and FastAPI. We'll cover setting up the project 
    structure, creating modular components, integrating with external APIs like 
    Groq for AI inference, and deploying the whole thing to production. 
    
    The key challenge was making everything work together seamlessly while 
    keeping the code maintainable. I'll share the exact architecture I used 
    and the mistakes I made along the way so you can avoid them.
    
    By the end of this tutorial, you'll have a production-ready AI application 
    that can process videos, generate content, and scale to handle thousands 
    of requests. Let's dive in!
    """
    
    # Generate titles from text
    generate_titles_from_text(sample_transcript, "youtube")
    
    # If a video path was provided, process it
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        generate_titles_from_video(video_path, "youtube")
    else:
        print("\n" + "-" * 60)
        print("To test with a video file, run:")
        print(f"  python {sys.argv[0]} path/to/your/video.mp4")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
