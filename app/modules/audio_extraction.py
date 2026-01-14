import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AudioExtractionError(Exception):
    """Raised when audio extraction fails."""
    pass


class AudioExtractionModule:
    """
    Extracts audio from video files optimized for Whisper transcription.
    
    Features:
    - Handles videos of ANY size (tested up to 10GB)
    - Direct extraction to compressed OGG (saves disk space)
    - Whisper-optimal format: 16kHz mono
    - Proper timeout scaling for large files
    
    Output options:
    - WAV: Uncompressed, larger, best quality
    - OGG: Compressed, much smaller, excellent for speech
    """
    
    # Whisper expects 16kHz sample rate
    SAMPLE_RATE = 16000
    CHANNELS = 1  # Mono
    
    # Timeout scales with expected duration
    BASE_TIMEOUT_SECONDS = 300  # 5 minutes minimum
    TIMEOUT_PER_GB = 180  # Additional 3 minutes per GB
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify FFmpeg is available
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> None:
        """Check if FFmpeg is installed and accessible."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise AudioExtractionError("FFmpeg not working properly")
            
            # Check for opus encoder (needed for OGG compression)
            result = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "libopus" not in result.stdout:
                logger.warning(
                    "libopus encoder not found. "
                    "Install with: apt install libopus-dev"
                )
            
        except FileNotFoundError:
            raise AudioExtractionError(
                "FFmpeg not found. Please install FFmpeg: "
                "sudo apt install ffmpeg (Ubuntu) or brew install ffmpeg (Mac)"
            )
        except subprocess.TimeoutExpired:
            raise AudioExtractionError("FFmpeg check timed out")
    
    def _get_file_size_gb(self, file_path: Path) -> float:
        """Get file size in GB."""
        return file_path.stat().st_size / (1024 * 1024 * 1024)
    
    def _calculate_timeout(self, video_path: Path) -> int:
        """Calculate appropriate timeout based on file size."""
        size_gb = self._get_file_size_gb(video_path)
        timeout = self.BASE_TIMEOUT_SECONDS + int(size_gb * self.TIMEOUT_PER_GB)
        return min(timeout, 3600)  # Cap at 1 hour
    
    def extract_audio(
        self, 
        video_path: Path, 
        output_path: Optional[Path] = None,
        compress: bool = True
    ) -> Path:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to the input video file
            output_path: Optional path for output audio file
            compress: If True, output compressed OGG; if False, output WAV
            
        Returns:
            Path to the extracted audio file
            
        Raises:
            AudioExtractionError: If extraction fails
        """
        if not video_path.exists():
            raise AudioExtractionError(f"Video file not found: {video_path}")
        
        file_size_gb = self._get_file_size_gb(video_path)
        timeout = self._calculate_timeout(video_path)
        
        # Determine output format and path
        if compress:
            extension = ".ogg"
            codec_args = [
                "-c:a", "libopus",
                "-b:a", "32k",           # 32kbps is enough for speech
                "-application", "voip",  # Optimize for speech
            ]
        else:
            extension = ".wav"
            codec_args = ["-acodec", "pcm_s16le"]
        
        if output_path is None:
            output_path = self.output_dir / f"{video_path.stem}_audio{extension}"
        
        # FFmpeg command
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",                       # No video
            *codec_args,
            "-ar", str(self.SAMPLE_RATE),  # Sample rate
            "-ac", str(self.CHANNELS),     # Channels
            "-y",                          # Overwrite
            str(output_path)
        ]
        
        logger.info(
            f"Extracting audio from {video_path.name} "
            f"({file_size_gb:.2f}GB) → {extension} "
            f"(timeout: {timeout}s)"
        )
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
                raise AudioExtractionError(f"FFmpeg failed: {error_msg}")
            
            if not output_path.exists():
                raise AudioExtractionError("Output audio file was not created")
            
            output_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"Audio extracted: {output_path.name} ({output_size_mb:.2f}MB)"
            )
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise AudioExtractionError(
                f"Audio extraction timed out after {timeout}s. "
                f"Video may be too large or corrupted."
            )
        except AudioExtractionError:
            raise
        except Exception as e:
            raise AudioExtractionError(f"Unexpected error: {str(e)}")
    
    def get_video_duration(self, video_path: Path) -> float:
        """
        Get the duration of a video file in seconds.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            return 0.0
            
        except (subprocess.TimeoutExpired, ValueError):
            return 0.0
    
    def get_video_info(self, video_path: Path) -> dict:
        """Get detailed information about a video file."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate",
            "-show_entries", "stream=codec_type,codec_name,width,height",
            "-of", "json",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            return {}
            
        except:
            return {}
    
    def cleanup(self, audio_path: Path) -> None:
        """Remove extracted audio file."""
        try:
            if audio_path.exists():
                audio_path.unlink()
                logger.debug(f"Cleaned up: {audio_path.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {audio_path}: {e}")
