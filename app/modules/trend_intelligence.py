import logging
from typing import Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from cachetools import TTLCache

from app.config import get_settings
from app.schemas import TrendData

logger = logging.getLogger(__name__)


class TrendSourceError(Exception):
    """Raised when a trend source fails."""
    pass


class BaseTrendSource(ABC):
    """Abstract base class for trend sources."""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this trend source."""
        pass
    
    @abstractmethod
    def fetch_trends(self, category: Optional[str] = None) -> TrendData:
        """Fetch trends from this source."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this source is properly configured."""
        pass


class GoogleTrendsSource(BaseTrendSource):
    """Fetches trending topics from Google Trends via pytrends."""
    
    source_name = "google_trends"
    
    def __init__(self):
        self._pytrends = None
    
    def is_configured(self) -> bool:
        """Google Trends doesn't require API key."""
        return True
    
    def _get_client(self):
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                self._pytrends = TrendReq(hl='en-US', tz=360)
            except ImportError:
                raise TrendSourceError("pytrends not installed")
        return self._pytrends
    
    def fetch_trends(self, category: Optional[str] = None) -> TrendData:
        """Fetch trending searches from Google Trends."""
        try:
            pytrends = self._get_client()
            
            # Get trending searches for US (most comprehensive)
            trending_df = pytrends.trending_searches(pn='united_states')
            
            keywords = trending_df[0].tolist()[:15] if not trending_df.empty else []
            
            logger.info(f"Google Trends: fetched {len(keywords)} trending topics")
            
            return TrendData(
                source=self.source_name,
                keywords=keywords,
                topics=keywords[:10],
                hashtags=[]
            )
            
        except Exception as e:
            logger.warning(f"Google Trends fetch failed: {e}")
            return TrendData(source=self.source_name, keywords=[], topics=[], hashtags=[])


class YouTubeTrendsSource(BaseTrendSource):
    """Fetches trending videos from YouTube Data API."""
    
    source_name = "youtube"
    
    def __init__(self):
        self.settings = get_settings()
        self._service = None
    
    def is_configured(self) -> bool:
        return bool(self.settings.youtube_api_key)
    
    def _get_service(self):
        if self._service is None:
            try:
                from googleapiclient.discovery import build
                self._service = build(
                    'youtube', 'v3',
                    developerKey=self.settings.youtube_api_key
                )
            except ImportError:
                raise TrendSourceError("google-api-python-client not installed")
        return self._service
    
    def fetch_trends(self, category: Optional[str] = None) -> TrendData:
        """Fetch trending video titles and extract keywords."""
        if not self.is_configured():
            logger.warning("YouTube API key not configured")
            return TrendData(source=self.source_name, keywords=[], topics=[], hashtags=[])
        
        try:
            service = self._get_service()
            
            # Fetch most popular videos
            request = service.videos().list(
                part="snippet",
                chart="mostPopular",
                regionCode="US",
                maxResults=20
            )
            response = request.execute()
            
            keywords = []
            topics = []
            hashtags = []
            
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                title = snippet.get('title', '')
                tags = snippet.get('tags', [])
                
                # Extract topics from titles
                topics.append(title)
                
                # Collect tags as keywords
                keywords.extend(tags[:5])
                
                # Extract hashtags from description
                desc = snippet.get('description', '')
                hashtags.extend([
                    word for word in desc.split() 
                    if word.startswith('#')
                ][:3])
            
            # Deduplicate and limit
            keywords = list(dict.fromkeys(keywords))[:20]
            hashtags = list(dict.fromkeys(hashtags))[:15]
            
            logger.info(f"YouTube: fetched {len(topics)} trending videos, {len(keywords)} keywords")
            
            return TrendData(
                source=self.source_name,
                keywords=keywords,
                topics=topics[:10],
                hashtags=hashtags
            )
            
        except Exception as e:
            logger.warning(f"YouTube trends fetch failed: {e}")
            return TrendData(source=self.source_name, keywords=[], topics=[], hashtags=[])


class RedditTrendsSource(BaseTrendSource):
    """Fetches trending topics from Reddit."""
    
    source_name = "reddit"
    
    # Subreddits to monitor for general trends
    DEFAULT_SUBREDDITS = ["all", "popular", "news", "technology", "videos"]
    
    def __init__(self):
        self.settings = get_settings()
        self._reddit = None
    
    def is_configured(self) -> bool:
        return bool(
            self.settings.reddit_client_id and 
            self.settings.reddit_client_secret
        )
    
    def _get_client(self):
        if self._reddit is None:
            try:
                import praw
                self._reddit = praw.Reddit(
                    client_id=self.settings.reddit_client_id,
                    client_secret=self.settings.reddit_client_secret,
                    user_agent=self.settings.reddit_user_agent
                )
            except ImportError:
                raise TrendSourceError("praw not installed")
        return self._reddit
    
    def fetch_trends(self, category: Optional[str] = None) -> TrendData:
        """Fetch trending posts from Reddit."""
        if not self.is_configured():
            logger.warning("Reddit API credentials not configured")
            return TrendData(source=self.source_name, keywords=[], topics=[], hashtags=[])
        
        try:
            reddit = self._get_client()
            
            keywords = []
            topics = []
            
            # Get hot posts from r/all
            for post in reddit.subreddit("all").hot(limit=25):
                topics.append(post.title)
                
                # Extract significant words from title
                words = [
                    word.lower() for word in post.title.split()
                    if len(word) > 4 and word.isalpha()
                ]
                keywords.extend(words[:3])
            
            # Also get rising posts for emerging trends
            for post in reddit.subreddit("all").rising(limit=10):
                words = [
                    word.lower() for word in post.title.split()
                    if len(word) > 4 and word.isalpha()
                ]
                keywords.extend(words[:2])
            
            # Deduplicate
            keywords = list(dict.fromkeys(keywords))[:25]
            
            logger.info(f"Reddit: fetched {len(topics)} trending posts, {len(keywords)} keywords")
            
            return TrendData(
                source=self.source_name,
                keywords=keywords,
                topics=topics[:10],
                hashtags=[]
            )
            
        except Exception as e:
            logger.warning(f"Reddit trends fetch failed: {e}")
            return TrendData(source=self.source_name, keywords=[], topics=[], hashtags=[])


class TrendIntelligenceModule:
    """
    Aggregates trend data from multiple sources.
    
    Responsibilities:
    - Manage multiple trend sources
    - Cache trend data to reduce API calls
    - Normalize and deduplicate trends
    - Provide fallback when sources fail
    """
    
    def __init__(self, cache_ttl: Optional[int] = None):
        settings = get_settings()
        cache_ttl = cache_ttl or settings.trend_cache_ttl
        
        # Initialize cache
        self._cache = TTLCache(maxsize=100, ttl=cache_ttl)
        
        # Initialize trend sources
        self.sources: list[BaseTrendSource] = [
            GoogleTrendsSource(),
            YouTubeTrendsSource(),
            RedditTrendsSource(),
        ]
        
        logger.info(f"Trend Intelligence initialized with {len(self.sources)} sources")
    
    def get_configured_sources(self) -> list[str]:
        """Return list of properly configured sources."""
        return [s.source_name for s in self.sources if s.is_configured()]
    
    def fetch_all_trends(self, use_cache: bool = True) -> list[TrendData]:
        """
        Fetch trends from all configured sources.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            List of TrendData from all sources
        """
        cache_key = "all_trends"
        
        if use_cache and cache_key in self._cache:
            logger.info("Returning cached trend data")
            return self._cache[cache_key]
        
        results = []
        
        for source in self.sources:
            if not source.is_configured():
                logger.debug(f"Skipping unconfigured source: {source.source_name}")
                continue
            
            try:
                trend_data = source.fetch_trends()
                if trend_data.keywords or trend_data.topics:
                    results.append(trend_data)
            except Exception as e:
                logger.error(f"Error fetching from {source.source_name}: {e}")
        
        # Cache results
        if results:
            self._cache[cache_key] = results
        
        logger.info(f"Fetched trends from {len(results)} sources")
        return results
    
    def get_aggregated_keywords(self, limit: int = 30) -> list[str]:
        """Get deduplicated keywords from all sources."""
        all_keywords = []
        
        for trend_data in self.fetch_all_trends():
            all_keywords.extend(trend_data.keywords)
        
        # Deduplicate while preserving order (most common sources first)
        seen = set()
        unique = []
        for kw in all_keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique.append(kw)
        
        return unique[:limit]
    
    def get_status(self) -> dict:
        """Get status of all trend sources."""
        return {
            "sources": [
                {
                    "name": s.source_name,
                    "configured": s.is_configured()
                }
                for s in self.sources
            ],
            "cache_size": len(self._cache),
            "cache_ttl": self._cache.ttl
        }
