from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional

from app.schemas import (
    Platform,
    VideoProcessingResponse,
    TranscriptResult,
    ErrorResponse,
)
from app.modules import OrchestrationService, OrchestrationError

router = APIRouter(prefix="/api/v1", tags=["Video Title Generation"])

# Dependency to get orchestration service
def get_orchestration_service() -> OrchestrationService:
    return OrchestrationService()


@router.post(
    "/generate-titles",
    response_model=VideoProcessingResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate video titles from uploaded video",
    description="""
    Upload a video file and receive AI-generated, trend-optimized titles.
    
    The system will:
    1. Extract audio from the video
    2. Transcribe the audio to text
    3. Fetch current social media trends
    4. Generate optimized titles using AI
    
    Supported formats: MP4, MOV, AVI, MKV, WebM, FLV, WMV
    Max file size: 500MB (configurable)
    """
)
async def generate_titles(
    video: UploadFile = File(..., description="Video file to process"),
    platform: Platform = Form(
        default=Platform.GENERAL,
        description="Target platform for title optimization"
    ),
    num_titles: int = Form(
        default=5,
        ge=1,
        le=10,
        description="Number of titles to generate (1-10)"
    ),
    skip_trends: bool = Form(
        default=False,
        description="Skip trend fetching for faster processing"
    ),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Main endpoint for video title generation.
    
    Upload a video and receive optimized titles based on content and trends.
    """
    try:
        result = await service.process_video(
            video_file=video,
            platform=platform,
            num_titles=num_titles,
            skip_trends=skip_trends
        )
        return result
        
    except OrchestrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post(
    "/transcribe",
    response_model=TranscriptResult,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Transcribe video audio only",
    description="Extract and transcribe audio from video without generating titles."
)
async def transcribe_video(
    video: UploadFile = File(..., description="Video file to transcribe"),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Transcribe a video file without generating titles.
    Useful for testing or when you only need the transcript.
    """
    try:
        return await service.transcribe_only(video)
    except OrchestrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post(
    "/generate-from-text",
    summary="Generate titles from provided transcript",
    description="Generate titles from a text transcript without video upload."
)
async def generate_from_text(
    transcript: str = Form(..., min_length=50, description="Video transcript text"),
    platform: Platform = Form(
        default=Platform.GENERAL,
        description="Target platform for title optimization"
    ),
    num_titles: int = Form(
        default=5,
        ge=1,
        le=10,
        description="Number of titles to generate"
    ),
    include_trends: bool = Form(
        default=True,
        description="Include current trends in generation"
    ),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Generate titles from a text transcript.
    
    Use this endpoint when you already have a transcript and don't need
    to upload a video file.
    """
    try:
        return service.generate_titles_from_text(
            transcript=transcript,
            platform=platform,
            num_titles=num_titles,
            include_trends=include_trends
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/trends",
    summary="Get current trends",
    description="Fetch current trending topics from all configured sources."
)
async def get_trends(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Fetch current trends from all configured sources.
    
    Useful for debugging or seeing what trends will be used for title generation.
    """
    trends = service.trend_intelligence.fetch_all_trends()
    return {
        "sources": [t.model_dump() for t in trends],
        "aggregated_keywords": service.trend_intelligence.get_aggregated_keywords()
    }


@router.get(
    "/status",
    summary="Get system status",
    description="Get configuration and status of all modules."
)
async def get_status(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Get detailed status of all system modules.
    
    Shows configuration, which services are enabled, and module health.
    """
    return service.get_system_status()
