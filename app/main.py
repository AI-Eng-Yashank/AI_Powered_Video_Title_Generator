import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import video_router
from app.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()
    
    # Startup
    logger.info("=" * 50)
    logger.info("Video Title Generator - Starting Up")
    logger.info("=" * 50)
    
    # Ensure directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Log configuration
    logger.info(f"Groq API Configured: {bool(settings.groq_api_key)}")
    logger.info(f"Groq LLM Model: {settings.groq_model}")
    logger.info(f"Groq Whisper Model: {settings.groq_whisper_model}")
    logger.info(f"YouTube API Configured: {bool(settings.youtube_api_key)}")
    logger.info(f"Reddit API Configured: {bool(settings.reddit_client_id)}")
    logger.info(f"Max Upload Size: {settings.max_upload_size_mb}MB")
    
    yield
    
    # Shutdown
    logger.info("Video Title Generator - Shutting Down")


# Create FastAPI application
app = FastAPI(
    title="Video Title Generator API",
    description="""
    ## AI-Powered Video Title Generation System
    
    Generate trend-aware, click-optimized video titles from your video content.
    
    ### Features
    - **Video Processing**: Upload videos in MP4, MOV, AVI, MKV, WebM, FLV, WMV formats
    - **Transcription**: Automatic speech-to-text using Whisper
    - **Trend Intelligence**: Real-time trends from YouTube, Google, Reddit
    - **AI Title Generation**: Optimized titles via Groq API
    
    ### Platforms Supported
    - YouTube
    - Instagram  
    - TikTok
    - Twitter/X
    - General (platform-agnostic)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if get_settings().debug else None
        }
    )


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - basic health check."""
    return {"status": "ok", "message": "Video Title Generator API is running"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Detailed health check with configuration status."""
    settings = get_settings()
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        whisper_model=f"groq:{settings.groq_whisper_model}",
        groq_configured=bool(settings.groq_api_key),
        youtube_configured=bool(settings.youtube_api_key),
        reddit_configured=bool(settings.reddit_client_id)
    )


# Include routers
app.include_router(video_router)


# Run with uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
