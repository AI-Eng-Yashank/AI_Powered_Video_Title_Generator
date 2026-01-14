import time
import logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from app.config import get_settings
from app.schemas import (
    Platform,
    VideoProcessingResponse,
    TranscriptResult,
    TrendData,
    GeneratedTitle,
)
from app.modules.video_upload import VideoUploadModule
from app.modules.audio_extraction import AudioExtractionModule, AudioExtractionError
from app.modules.transcription import TranscriptionModule, TranscriptionError
from app.modules.trend_intelligence import TrendIntelligenceModule
from app.modules.title_generation import AITitleGenerationModule, TitleGenerationError

logger = logging.getLogger(__name__)


class OrchestrationError(Exception):
    """Raised when orchestration fails."""
    pass


class OrchestrationService:
    """
    Orchestrates the complete video title generation workflow.
    
    Flow:
    1. Upload & validate video
    2. Extract audio
    3. Transcribe audio
    4. Fetch trends
    5. Generate titles
    6. Return results
    
    Each step is isolated, allowing for partial processing and
    easy debugging.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize all modules
        self.video_upload = VideoUploadModule()
        self.audio_extraction = AudioExtractionModule()
        self.transcription = TranscriptionModule()
        self.trend_intelligence = TrendIntelligenceModule()
        self.title_generation = AITitleGenerationModule()
        
        logger.info("Orchestration service initialized with all modules")
    
    async def process_video(
        self,
        video_file: UploadFile,
        platform: Platform = Platform.GENERAL,
        num_titles: int = 5,
        skip_trends: bool = False
    ) -> VideoProcessingResponse:
        """
        Process a video through the complete pipeline.
        
        Args:
            video_file: Uploaded video file
            platform: Target platform for title optimization
            num_titles: Number of titles to generate
            skip_trends: If True, skip trend fetching (faster, offline)
            
        Returns:
            Complete processing response with titles
            
        Raises:
            OrchestrationError: If any critical step fails
        """
        start_time = time.time()
        video_path = None
        audio_path = None
        
        try:
            # Step 1: Save uploaded video
            logger.info(f"Step 1/5: Saving video upload")
            video_path = await self.video_upload.save_upload(video_file)
            logger.info(f"Video saved: {video_path.name}")
            
            # Step 2: Extract audio (compressed by default for efficiency)
            logger.info("Step 2/5: Extracting audio")
            audio_path = self.audio_extraction.extract_audio(video_path, compress=True)
            logger.info(f"Audio extracted: {audio_path.name}")
            
            # Step 3: Transcribe audio
            logger.info("Step 3/5: Transcribing audio")
            transcript_result = self.transcription.transcribe(audio_path)
            logger.info(f"Transcription complete: {transcript_result.word_count} words")
            
            # Step 4: Fetch trends (optional)
            trends: list[TrendData] = []
            if not skip_trends:
                logger.info("Step 4/5: Fetching trends")
                trends = self.trend_intelligence.fetch_all_trends()
                logger.info(f"Fetched trends from {len(trends)} sources")
            else:
                logger.info("Step 4/5: Skipping trends (as requested)")
            
            # Step 5: Generate titles
            logger.info("Step 5/5: Generating titles")
            title_response = self.title_generation.generate_titles(
                transcript=transcript_result.text,
                trends=trends,
                platform=platform,
                num_titles=num_titles
            )
            logger.info(f"Generated {len(title_response.titles)} titles")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            return VideoProcessingResponse(
                success=True,
                video_filename=video_path.name,
                transcript=transcript_result,
                trends=trends,
                generated_titles=title_response.titles,
                transcript_summary=title_response.transcript_summary,
                processing_time_seconds=round(processing_time, 2)
            )
            
        except (AudioExtractionError, TranscriptionError, TitleGenerationError) as e:
            logger.error(f"Processing failed: {e}")
            raise OrchestrationError(str(e))
        
        except Exception as e:
            logger.exception(f"Unexpected error during processing")
            raise OrchestrationError(f"Unexpected error: {str(e)}")
        
        finally:
            # Cleanup temporary files
            if audio_path:
                self.audio_extraction.cleanup(audio_path)
            if video_path:
                await self.video_upload.cleanup(video_path)
    
    async def transcribe_only(self, video_file: UploadFile) -> TranscriptResult:
        """
        Only transcribe a video without generating titles.
        Useful for testing transcription or getting transcript for other uses.
        """
        video_path = None
        audio_path = None
        
        try:
            video_path = await self.video_upload.save_upload(video_file)
            audio_path = self.audio_extraction.extract_audio(video_path, compress=True)
            return self.transcription.transcribe(audio_path)
            
        finally:
            if audio_path:
                self.audio_extraction.cleanup(audio_path)
            if video_path:
                await self.video_upload.cleanup(video_path)
    
    def generate_titles_from_text(
        self,
        transcript: str,
        platform: Platform = Platform.GENERAL,
        num_titles: int = 5,
        include_trends: bool = True
    ) -> dict:
        """
        Generate titles from a provided transcript (no video upload needed).
        Useful for testing or when transcript is already available.
        """
        trends = []
        if include_trends:
            trends = self.trend_intelligence.fetch_all_trends()
        
        result = self.title_generation.generate_titles(
            transcript=transcript,
            trends=trends,
            platform=platform,
            num_titles=num_titles
        )
        
        return {
            "titles": [t.model_dump() for t in result.titles],
            "transcript_summary": result.transcript_summary,
            "trends_used": result.trends_used
        }
    
    def get_system_status(self) -> dict:
        """Get status of all modules."""
        return {
            "transcription": self.transcription.get_model_info(),
            "trends": self.trend_intelligence.get_status(),
            "title_generation": self.title_generation.get_status(),
            "upload_config": {
                "max_size_mb": self.settings.max_upload_size_mb,
                "allowed_formats": self.settings.allowed_extensions_list
            }
        }
