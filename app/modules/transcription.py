import os
import subprocess
import tempfile
import math
from pathlib import Path
from typing import Optional, List, Tuple
import logging
import time

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.schemas import TranscriptResult

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when transcription fails."""
    pass


class TranscriptionModule:
    """
    Converts audio to text using Groq's Whisper API.
    
    Features:
    - Handles videos of ANY size (even 3GB+)
    - Auto-compresses audio to reduce size
    - Chunks large audio into segments for API limits
    - Merges transcripts seamlessly
    - No local GPU required!
    
    Strategy for large files:
    1. Compress audio to OGG/Opus (reduces ~100MB WAV to ~5MB)
    2. If still >25MB, split into time-based chunks
    3. Transcribe each chunk via Groq API
    4. Merge transcripts with proper spacing
    """
    
    # Available Groq Whisper models
    MODELS = {
        "whisper-large-v3-turbo": {
            "description": "Fast and accurate, best for most use cases",
            "multilingual": True,
        },
        "whisper-large-v3": {
            "description": "Highest accuracy, slightly slower",
            "multilingual": True,
        },
        "distil-whisper-large-v3-en": {
            "description": "Fastest, English only",
            "multilingual": False,
        },
    }
    
    # Groq's file size limit
    MAX_FILE_SIZE_MB = 25
    
    # Target chunk size (with buffer for safety)
    TARGET_CHUNK_SIZE_MB = 20
    
    # Maximum chunk duration (10 minutes per chunk for safety)
    MAX_CHUNK_DURATION_SECONDS = 600
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_whisper_model
        self._client = None
        
        if not self.api_key:
            logger.warning("Groq API key not configured - transcription will fail")
        
        logger.info(f"Transcription module initialized with Groq Whisper: {self.model}")
    
    def is_configured(self) -> bool:
        """Check if Groq API is properly configured."""
        return bool(self.api_key)
    
    def _get_client(self):
        """Get or create Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise TranscriptionError(
                    "groq package not installed. Run: pip install groq"
                )
        return self._client
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except:
            pass
        return 0.0
    
    def _get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in MB."""
        return file_path.stat().st_size / (1024 * 1024)
    
    def _compress_audio(self, audio_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Compress audio to OGG/Opus format for optimal size.
        
        Opus codec at 32kbps provides:
        - Excellent speech quality
        - ~10x compression vs WAV
        - Perfect for Whisper transcription
        """
        if output_path is None:
            output_path = audio_path.with_suffix('.ogg')
        
        input_size = self._get_file_size_mb(audio_path)
        logger.info(f"Compressing audio: {input_size:.2f}MB → OGG")
        
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-vn",                  # No video
            "-c:a", "libopus",      # Opus codec (best for speech)
            "-b:a", "32k",          # 32kbps (sufficient for speech)
            "-ar", "16000",         # 16kHz (Whisper optimal)
            "-ac", "1",             # Mono
            "-application", "voip", # Optimize for speech
            "-y",                   # Overwrite
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout for large files
            )
            
            if result.returncode != 0:
                raise TranscriptionError(f"Audio compression failed: {result.stderr[:300]}")
            
            output_size = self._get_file_size_mb(output_path)
            compression_ratio = input_size / output_size if output_size > 0 else 0
            
            logger.info(
                f"Compression complete: {input_size:.2f}MB → {output_size:.2f}MB "
                f"({compression_ratio:.1f}x reduction)"
            )
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise TranscriptionError("Audio compression timed out")
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Compression failed: {str(e)}")
    
    def _calculate_chunks(self, audio_path: Path) -> List[Tuple[float, float]]:
        """
        Calculate time-based chunks for large audio files.
        
        Returns list of (start_time, duration) tuples.
        """
        total_duration = self._get_audio_duration(audio_path)
        file_size_mb = self._get_file_size_mb(audio_path)
        
        if file_size_mb <= self.TARGET_CHUNK_SIZE_MB:
            # No chunking needed
            return [(0, total_duration)]
        
        # Calculate how many chunks we need
        num_chunks = math.ceil(file_size_mb / self.TARGET_CHUNK_SIZE_MB)
        
        # Also consider max duration per chunk
        duration_based_chunks = math.ceil(total_duration / self.MAX_CHUNK_DURATION_SECONDS)
        num_chunks = max(num_chunks, duration_based_chunks)
        
        chunk_duration = total_duration / num_chunks
        
        chunks = []
        for i in range(num_chunks):
            start_time = i * chunk_duration
            # Last chunk gets remaining duration
            if i == num_chunks - 1:
                duration = total_duration - start_time
            else:
                duration = chunk_duration
            chunks.append((start_time, duration))
        
        logger.info(
            f"Splitting audio into {num_chunks} chunks "
            f"(~{chunk_duration:.1f}s each, total: {total_duration:.1f}s)"
        )
        
        return chunks
    
    def _extract_audio_chunk(
        self, 
        audio_path: Path, 
        start_time: float, 
        duration: float,
        chunk_index: int,
        output_dir: Path
    ) -> Path:
        """
        Extract a time-based chunk from audio file.
        
        Uses FFmpeg to extract and compress in one pass.
        """
        output_path = output_dir / f"chunk_{chunk_index:03d}.ogg"
        
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ss", str(start_time),     # Start time
            "-t", str(duration),         # Duration
            "-vn",                        # No video
            "-c:a", "libopus",           # Opus codec
            "-b:a", "32k",               # 32kbps
            "-ar", "16000",              # 16kHz
            "-ac", "1",                  # Mono
            "-application", "voip",
            "-y",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 min per chunk
            )
            
            if result.returncode != 0:
                raise TranscriptionError(
                    f"Chunk extraction failed: {result.stderr[:200]}"
                )
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise TranscriptionError(f"Chunk {chunk_index} extraction timed out")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_groq_whisper(
        self, 
        audio_path: Path, 
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """Make API call to Groq Whisper with retry logic."""
        client = self._get_client()
        
        file_size = self._get_file_size_mb(audio_path)
        logger.debug(f"Sending to Groq Whisper: {audio_path.name} ({file_size:.2f}MB)")
        
        with open(audio_path, "rb") as audio_file:
            kwargs = {
                "file": (audio_path.name, audio_file.read()),
                "model": self.model,
                "response_format": "verbose_json",
                "temperature": 0.0,
            }
            
            if language:
                kwargs["language"] = language
            
            # Use prompt for context continuity in chunks
            if prompt:
                kwargs["prompt"] = prompt
            
            transcription = client.audio.transcriptions.create(**kwargs)
        
        return transcription
    
    def _transcribe_single_file(
        self, 
        audio_path: Path, 
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """
        Transcribe a single audio file (must be <25MB).
        
        Returns: (transcript_text, detected_language, duration)
        """
        result = self._call_groq_whisper(audio_path, language, prompt)
        
        text = result.text.strip() if hasattr(result, 'text') else ""
        detected_lang = getattr(result, 'language', 'en') or 'en'
        duration = getattr(result, 'duration', 0) or 0
        
        return text, detected_lang, duration
    
    def _transcribe_with_chunking(
        self, 
        audio_path: Path, 
        language: Optional[str] = None
    ) -> TranscriptResult:
        """
        Transcribe large audio by splitting into chunks.
        
        Strategy:
        1. Calculate optimal chunk boundaries
        2. Extract each chunk as compressed OGG
        3. Transcribe chunks sequentially
        4. Merge transcripts with proper handling
        """
        chunks = self._calculate_chunks(audio_path)
        total_duration = self._get_audio_duration(audio_path)
        
        if len(chunks) == 1:
            # No chunking needed, but may need compression
            file_size = self._get_file_size_mb(audio_path)
            
            if file_size > self.MAX_FILE_SIZE_MB:
                # Compress the whole file
                compressed = self._compress_audio(audio_path)
                try:
                    text, lang, dur = self._transcribe_single_file(compressed, language)
                    return TranscriptResult(
                        text=text,
                        language=lang,
                        duration_seconds=dur or total_duration,
                        word_count=len(text.split())
                    )
                finally:
                    if compressed != audio_path and compressed.exists():
                        compressed.unlink()
            else:
                text, lang, dur = self._transcribe_single_file(audio_path, language)
                return TranscriptResult(
                    text=text,
                    language=lang,
                    duration_seconds=dur or total_duration,
                    word_count=len(text.split())
                )
        
        # Multiple chunks needed
        logger.info(f"Processing {len(chunks)} chunks for large audio file")
        
        transcripts = []
        detected_language = None
        chunk_files = []
        
        # Create temp directory for chunks
        temp_dir = Path(tempfile.mkdtemp(prefix="whisper_chunks_"))
        
        try:
            for i, (start_time, duration) in enumerate(chunks):
                logger.info(
                    f"Processing chunk {i+1}/{len(chunks)} "
                    f"({start_time:.1f}s - {start_time + duration:.1f}s)"
                )
                
                # Extract chunk
                chunk_path = self._extract_audio_chunk(
                    audio_path, start_time, duration, i, temp_dir
                )
                chunk_files.append(chunk_path)
                
                # Check chunk size
                chunk_size = self._get_file_size_mb(chunk_path)
                if chunk_size > self.MAX_FILE_SIZE_MB:
                    raise TranscriptionError(
                        f"Chunk {i+1} still too large ({chunk_size:.1f}MB). "
                        "Audio may have unusually high bitrate."
                    )
                
                # Use previous transcript ending as context for continuity
                prompt = None
                if transcripts and len(transcripts[-1]) > 50:
                    # Use last ~200 chars as context
                    prompt = transcripts[-1][-200:]
                
                # Transcribe chunk
                text, lang, _ = self._transcribe_single_file(
                    chunk_path, 
                    language or detected_language,
                    prompt
                )
                
                if text:
                    transcripts.append(text)
                
                if not detected_language and lang:
                    detected_language = lang
                
                # Small delay to respect rate limits
                if i < len(chunks) - 1:
                    time.sleep(0.5)
            
            # Merge transcripts
            full_transcript = " ".join(transcripts)
            
            # Clean up any double spaces from joining
            while "  " in full_transcript:
                full_transcript = full_transcript.replace("  ", " ")
            
            word_count = len(full_transcript.split())
            
            logger.info(
                f"Chunked transcription complete: {len(chunks)} chunks, "
                f"{word_count} words, {total_duration:.1f}s"
            )
            
            return TranscriptResult(
                text=full_transcript,
                language=detected_language or 'en',
                duration_seconds=total_duration,
                word_count=word_count
            )
            
        finally:
            # Cleanup chunk files
            for chunk_file in chunk_files:
                try:
                    if chunk_file.exists():
                        chunk_file.unlink()
                except:
                    pass
            
            # Remove temp directory
            try:
                temp_dir.rmdir()
            except:
                pass
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptResult:
        """
        Transcribe an audio file to text using Groq Whisper API.
        
        Handles files of ANY size by:
        1. Compressing audio (WAV → OGG)
        2. Chunking if still >25MB
        3. Merging chunk transcripts
        
        Args:
            audio_path: Path to the audio file
            language: Optional language code (auto-detected if None)
            
        Returns:
            TranscriptResult with full transcript and metadata
            
        Raises:
            TranscriptionError: If transcription fails
        """
        if not self.is_configured():
            raise TranscriptionError(
                "Groq API key not configured. Set GROQ_API_KEY in .env"
            )
        
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")
        
        file_size_mb = self._get_file_size_mb(audio_path)
        duration = self._get_audio_duration(audio_path)
        
        logger.info(
            f"Starting transcription: {audio_path.name} "
            f"({file_size_mb:.2f}MB, {duration:.1f}s)"
        )
        
        try:
            result = self._transcribe_with_chunking(audio_path, language)
            
            if not result.text.strip():
                raise TranscriptionError(
                    "Transcription produced empty result. "
                    "The audio may be silent, corrupted, or in an unsupported language."
                )
            
            return result
            
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        model_info = self.MODELS.get(self.model, {})
        return {
            "provider": "groq",
            "model": self.model,
            "configured": self.is_configured(),
            "max_file_size_mb": self.MAX_FILE_SIZE_MB,
            "max_chunk_duration_seconds": self.MAX_CHUNK_DURATION_SECONDS,
            "supports_large_files": True,
            "description": model_info.get("description", ""),
            "multilingual": model_info.get("multilingual", True),
            "available_models": list(self.MODELS.keys()),
        }
