import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, Text, 
    ForeignKey, DateTime, Numeric, Enum, Index, CheckConstraint,
    create_engine, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import expression

Base = declarative_base()


# ============================================================================
# ENUM DEFINITIONS
# ============================================================================

class PlatformType(PyEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    GENERAL = "general"


class ProcessingStatus(PyEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    TRANSCRIBING = "transcribing"
    FETCHING_TRENDS = "fetching_trends"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class TitleStyle(PyEnum):
    CURIOSITY = "curiosity"
    HOW_TO = "how_to"
    LISTICLE = "listicle"
    STORY = "story"
    CONTRARIAN = "contrarian"
    QUESTION = "question"
    NEWS = "news"
    EMOTIONAL = "emotional"


class TrendSource(PyEnum):
    GOOGLE_TRENDS = "google_trends"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    MANUAL = "manual"


# ============================================================================
# MODEL DEFINITIONS
# ============================================================================

class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    api_key = Column(String(64), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # Usage limits
    daily_video_limit = Column(Integer, default=10)
    monthly_video_limit = Column(Integer, default=100)
    max_video_size_mb = Column(Integer, default=500)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    videos = relationship("Video", back_populates="user")
    api_usage_logs = relationship("ApiUsageLog", back_populates="user")
    feedback = relationship("UserFeedback", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Video(Base):
    """Uploaded video model."""
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # File information
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_format = Column(String(20), nullable=False)
    mime_type = Column(String(100))
    
    # Video metadata
    duration_seconds = Column(Numeric(10, 2))
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    fps = Column(Numeric(5, 2))
    video_codec = Column(String(50))
    audio_codec = Column(String(50))
    bitrate_kbps = Column(Integer)
    
    # Storage paths
    storage_path = Column(String(500))
    thumbnail_path = Column(String(500))
    
    # Processing info
    status = Column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.PENDING
    )
    target_platform = Column(
        Enum(PlatformType, name="platform_type"),
        default=PlatformType.GENERAL
    )
    requested_titles_count = Column(Integer, default=5)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False)
    generated_titles = relationship("GeneratedTitle", back_populates="video")
    processing_job = relationship("ProcessingJob", back_populates="video", uselist=False)
    trends_used = relationship("VideoTrendsUsed", back_populates="video")
    feedback = relationship("UserFeedback", back_populates="video")
    
    # Indexes
    __table_args__ = (
        Index("idx_videos_user_id", user_id),
        Index("idx_videos_status", status),
        Index("idx_videos_created_at", created_at.desc()),
    )
    
    def __repr__(self):
        return f"<Video(id={self.id}, filename={self.original_filename})>"
    
    @property
    def file_size_mb(self) -> float:
        return self.file_size_bytes / (1024 * 1024) if self.file_size_bytes else 0


class Transcript(Base):
    """Video transcription model."""
    __tablename__ = "transcripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Transcript content
    full_text = Column(Text, nullable=False)
    summary = Column(Text)
    word_count = Column(Integer, nullable=False)
    
    # Language detection
    detected_language = Column(String(10), nullable=False)
    language_confidence = Column(Numeric(3, 2))
    
    # Processing metadata
    transcription_model = Column(String(100))
    chunks_processed = Column(Integer, default=1)
    processing_time_seconds = Column(Numeric(10, 2))
    
    # Audio file info
    audio_file_size_mb = Column(Numeric(10, 2))
    audio_duration_seconds = Column(Numeric(10, 2))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="transcript")
    
    # Indexes
    __table_args__ = (
        Index("idx_transcripts_video_id", video_id),
        Index("idx_transcripts_language", detected_language),
    )
    
    def __repr__(self):
        return f"<Transcript(id={self.id}, words={self.word_count})>"


class GeneratedTitle(Base):
    """AI-generated title model."""
    __tablename__ = "generated_titles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Title content
    title_text = Column(String(500), nullable=False)
    title_style = Column(Enum(TitleStyle, name="title_style"))
    reasoning = Column(Text)
    
    # Ranking/ordering
    rank_position = Column(Integer, nullable=False)
    confidence_score = Column(Numeric(3, 2))
    
    # Platform optimization
    target_platform = Column(
        Enum(PlatformType, name="platform_type"),
        nullable=False
    )
    character_count = Column(Integer)
    
    # User feedback
    is_selected = Column(Boolean, default=False)
    user_rating = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="generated_titles")
    feedback = relationship("UserFeedback", back_populates="title")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("user_rating BETWEEN 1 AND 5", name="check_rating_range"),
        Index("idx_generated_titles_video_id", video_id),
        Index("idx_generated_titles_platform", target_platform),
    )
    
    def __repr__(self):
        return f"<GeneratedTitle(id={self.id}, title={self.title_text[:50]})>"


class TrendsCache(Base):
    """Cached trending topics model."""
    __tablename__ = "trends_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Trend data
    source = Column(Enum(TrendSource, name="trend_source"), nullable=False)
    keyword = Column(String(255), nullable=False)
    topic = Column(String(500))
    hashtag = Column(String(255))
    
    # Metrics
    popularity_score = Column(Integer)
    search_volume = Column(Integer)
    growth_percentage = Column(Numeric(5, 2))
    
    # Geographic/category info
    region = Column(String(10), default="US")
    category = Column(String(100))
    
    # Cache management
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    videos_used = relationship("VideoTrendsUsed", back_populates="trend")
    
    # Indexes
    __table_args__ = (
        Index("idx_trends_source", source),
        Index("idx_trends_keyword", keyword),
        Index("idx_trends_expires", expires_at),
    )
    
    def __repr__(self):
        return f"<TrendsCache(source={self.source}, keyword={self.keyword})>"


class VideoTrendsUsed(Base):
    """Junction table linking videos to trends used."""
    __tablename__ = "video_trends_used"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    trend_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trends_cache.id", ondelete="SET NULL")
    )
    
    # Store keyword even if trend is deleted
    trend_keyword = Column(String(255), nullable=False)
    trend_source = Column(Enum(TrendSource, name="trend_source"))
    
    # Was this trend actually used?
    was_incorporated = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="trends_used")
    trend = relationship("TrendsCache", back_populates="videos_used")
    
    __table_args__ = (
        Index("idx_video_trends_video_id", video_id),
        Index("idx_video_trends_trend_id", trend_id),
    )


class ProcessingJob(Base):
    """Video processing job tracking model."""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Job status
    status = Column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.PENDING
    )
    current_step = Column(String(50))
    progress_percentage = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    total_processing_time_seconds = Column(Numeric(10, 2))
    
    # Step-by-step timing
    upload_time_seconds = Column(Numeric(10, 2))
    extraction_time_seconds = Column(Numeric(10, 2))
    transcription_time_seconds = Column(Numeric(10, 2))
    trend_fetch_time_seconds = Column(Numeric(10, 2))
    generation_time_seconds = Column(Numeric(10, 2))
    
    # Error handling
    error_message = Column(Text)
    error_code = Column(String(50))
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Worker info
    worker_id = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="processing_job")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "progress_percentage BETWEEN 0 AND 100",
            name="check_progress_range"
        ),
        Index("idx_processing_jobs_video_id", video_id),
        Index("idx_processing_jobs_status", status),
    )
    
    def __repr__(self):
        return f"<ProcessingJob(video_id={self.video_id}, status={self.status})>"


class ApiUsageLog(Base):
    """API usage logging model."""
    __tablename__ = "api_usage_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Request info
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    request_ip = Column(String(45))
    user_agent = Column(Text)
    
    # Video processing specific
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="SET NULL"))
    video_size_bytes = Column(BigInteger)
    processing_time_seconds = Column(Numeric(10, 2))
    
    # External API calls made
    groq_whisper_calls = Column(Integer, default=0)
    groq_llm_calls = Column(Integer, default=0)
    youtube_api_calls = Column(Integer, default=0)
    google_trends_calls = Column(Integer, default=0)
    reddit_api_calls = Column(Integer, default=0)
    
    # Response info
    response_status = Column(Integer)
    response_time_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_usage_logs")
    
    __table_args__ = (
        Index("idx_api_usage_user_id", user_id),
        Index("idx_api_usage_created", created_at.desc()),
        Index("idx_api_usage_endpoint", endpoint),
    )


class UserFeedback(Base):
    """User feedback on generated titles."""
    __tablename__ = "user_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE")
    )
    title_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generated_titles.id", ondelete="CASCADE")
    )
    
    # Feedback data
    feedback_type = Column(String(50), nullable=False)
    original_title = Column(String(500))
    edited_title = Column(String(500))
    rating = Column(Integer)
    comment = Column(Text)
    
    # Context
    selected_platform = Column(Enum(PlatformType, name="platform_type"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    video = relationship("Video", back_populates="feedback")
    title = relationship("GeneratedTitle", back_populates="feedback")
    
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="check_feedback_rating"),
        Index("idx_user_feedback_video_id", video_id),
        Index("idx_user_feedback_title_id", title_id),
    )


class SystemSettings(Base):
    """System-wide configuration settings."""
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="string")
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    def get_typed_value(self):
        """Return value converted to its proper type."""
        if self.value_type == "integer":
            return int(self.value)
        elif self.value_type == "boolean":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value


# ============================================================================
# DATABASE CONNECTION HELPER
# ============================================================================

def get_database_url(
    host: str,
    database: str,
    user: str,
    password: str,
    port: int = 5432,
    ssl: bool = True
) -> str:
    """
    Build Neon DB connection URL.
    
    Example:
        url = get_database_url(
            host="ep-xxx.region.aws.neon.tech",
            database="neondb",
            user="user",
            password="password"
        )
    """
    ssl_param = "?sslmode=require" if ssl else ""
    return f"postgresql://{user}:{password}@{host}:{port}/{database}{ssl_param}"


def create_db_engine(database_url: str, echo: bool = False):
    """Create SQLAlchemy engine for Neon DB."""
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10
    )


def create_session_factory(engine):
    """Create session factory."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example usage
    DATABASE_URL = "postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require"
    
    engine = create_db_engine(DATABASE_URL, echo=True)
    SessionLocal = create_session_factory(engine)
    
    # Create all tables (if not using schema.sql)
    # Base.metadata.create_all(bind=engine)
    
    # Example session usage
    with SessionLocal() as session:
        # Create a user
        user = User(email="test@example.com", name="Test User")
        session.add(user)
        session.commit()
        
        print(f"Created user: {user}")
