from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Platform(str, Enum):
    """Supported social media platforms."""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    GENERAL = "general"


class TrendData(BaseModel):
    """Trend information from a source."""
    source: str = Field(description="Source of the trend (youtube, google, reddit)")
    keywords: list[str] = Field(default_factory=list, description="Trending keywords")
    topics: list[str] = Field(default_factory=list, description="Trending topics")
    hashtags: list[str] = Field(default_factory=list, description="Trending hashtags")


class TranscriptResult(BaseModel):
    """Transcription result."""
    text: str = Field(description="Full transcript text")
    language: str = Field(description="Detected language")
    duration_seconds: float = Field(description="Audio duration in seconds")
    word_count: int = Field(description="Number of words in transcript")


class GeneratedTitle(BaseModel):
    """A single generated title with metadata."""
    title: str = Field(description="The generated title")
    style: str = Field(description="Title style (curiosity, how-to, listicle, etc.)")
    reasoning: Optional[str] = Field(default=None, description="Why this title works")


class TitleGenerationRequest(BaseModel):
    """Request for title generation (used internally)."""
    transcript: str = Field(description="Video transcript")
    platform: Platform = Field(default=Platform.GENERAL)
    trends: list[TrendData] = Field(default_factory=list)
    num_titles: int = Field(default=5, ge=1, le=10)


class TitleGenerationResponse(BaseModel):
    """Response containing generated titles."""
    titles: list[GeneratedTitle] = Field(description="List of generated titles")
    transcript_summary: str = Field(description="Brief summary of video content")
    trends_used: list[str] = Field(description="Trend keywords incorporated")


class VideoProcessingResponse(BaseModel):
    """Complete response for video processing endpoint."""
    success: bool
    video_filename: str
    transcript: TranscriptResult
    trends: list[TrendData]
    generated_titles: list[GeneratedTitle]
    transcript_summary: str
    processing_time_seconds: float


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    whisper_model: str
    groq_configured: bool
    youtube_configured: bool
    reddit_configured: bool
