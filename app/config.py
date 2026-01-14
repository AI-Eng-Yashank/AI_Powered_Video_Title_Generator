from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="",
        description="PostgreSQL connection URL (Neon DB)"
    )
    
    # Groq API (used for both LLM and Whisper)
    groq_api_key: str = Field(default="", description="Groq API key for LLM and Whisper")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Groq LLM model")
    groq_whisper_model: str = Field(default="whisper-large-v3-turbo", description="Groq Whisper model")
    
    # YouTube API
    youtube_api_key: Optional[str] = Field(default=None, description="YouTube Data API v3 key")
    
    # Reddit API
    reddit_client_id: Optional[str] = Field(default=None)
    reddit_client_secret: Optional[str] = Field(default=None)
    reddit_user_agent: str = Field(default="VideoTitleGenerator/1.0")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=True)
    
    # Upload Settings
    max_upload_size_mb: int = Field(default=5000)
    allowed_extensions: str = Field(default="mp4,mov,avi,mkv,webm,flv,wmv")
    
    # Paths
    upload_dir: str = Field(default="uploads")
    output_dir: str = Field(default="outputs")
    
    # Cache
    trend_cache_ttl: int = Field(default=3600, description="Trend cache TTL in seconds")
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]
    
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
