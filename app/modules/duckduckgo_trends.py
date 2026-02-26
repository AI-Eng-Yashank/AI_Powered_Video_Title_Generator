import logging
from typing import Optional

from app.config import get_settings
from app.schemas import TrendData

logger = logging.getLogger(__name__)


class DuckDuckGoTrendsSource:
    """
    Fetches trending topics from DuckDuckGo news search.
    
    Uses the `duckduckgo-search` (ddgs) package which requires NO API key.
    Extracts keywords from current trending news headlines.
    """
    
    source_name = "duckduckgo"
    
    # Search categories to pull diverse trends from
    SEARCH_CATEGORIES = [
        "trending today",
        "viral news",
        "breaking news technology",
        "trending social media",
    ]
    
    def __init__(self):
        self._ddgs = None
    
    def is_configured(self) -> bool:
        """DuckDuckGo doesn't require any API key."""
        try:
            from duckduckgo_search import DDGS
            return True
        except ImportError:
            logger.warning(
                "duckduckgo-search package not installed. "
                "Install with: pip install duckduckgo-search"
            )
            return False
    
    def _get_client(self):
        """Get or create DDGS client."""
        if self._ddgs is None:
            from duckduckgo_search import DDGS
            self._ddgs = DDGS()
        return self._ddgs
    
    def fetch_trends(self, category: Optional[str] = None) -> TrendData:
        """
        Fetch trending topics from DuckDuckGo news.
        
        Strategy:
        1. Fetch recent news headlines across multiple categories
        2. Extract keywords from headlines
        3. Return aggregated trend data
        """
        if not self.is_configured():
            return TrendData(source=self.source_name)
        
        try:
            client = self._get_client()
            
            all_keywords = []
            all_topics = []
            all_hashtags = []
            
            # Fetch news for each category
            for search_query in self.SEARCH_CATEGORIES:
                try:
                    results = client.news(
                        keywords=search_query,
                        region="wt-wt",  # Worldwide
                        safesearch="moderate",
                        timelimit="d",  # Last 24 hours
                        max_results=5,
                    )
                    
                    for result in results:
                        title = result.get("title", "")
                        if title:
                            # Extract meaningful words from headlines
                            words = self._extract_keywords(title)
                            all_keywords.extend(words)
                            all_topics.append(title)
                            
                            # Generate hashtags from keywords
                            for word in words[:2]:
                                hashtag = f"#{word.replace(' ', '')}"
                                if hashtag not in all_hashtags:
                                    all_hashtags.append(hashtag)
                    
                except Exception as e:
                    logger.debug(f"DuckDuckGo search failed for '{search_query}': {e}")
                    continue
            
            # Also fetch general text search for trending topics
            try:
                text_results = client.text(
                    keywords="trending topics today",
                    region="wt-wt",
                    safesearch="moderate",
                    timelimit="d",
                    max_results=5,
                )
                
                for result in text_results:
                    title = result.get("title", "")
                    if title:
                        words = self._extract_keywords(title)
                        all_keywords.extend(words)
                        
            except Exception as e:
                logger.debug(f"DuckDuckGo text search failed: {e}")
            
            # Deduplicate and limit
            keywords = list(dict.fromkeys(all_keywords))[:20]
            topics = all_topics[:10]
            hashtags = list(dict.fromkeys(all_hashtags))[:15]
            
            logger.info(
                f"DuckDuckGo: fetched {len(keywords)} keywords, "
                f"{len(topics)} topics, {len(hashtags)} hashtags"
            )
            
            return TrendData(
                source=self.source_name,
                keywords=keywords,
                topics=topics,
                hashtags=hashtags,
            )
            
        except Exception as e:
            logger.error(f"DuckDuckGo trends fetch failed: {e}")
            return TrendData(source=self.source_name)
    
    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extract meaningful keywords from a headline.
        
        Filters out common stop words and short words to get
        only the meaningful trending terms.
        """
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "it", "its", "this",
            "that", "are", "was", "were", "be", "been", "has", "have", "had",
            "do", "does", "did", "will", "would", "could", "should", "may",
            "can", "not", "no", "so", "if", "then", "than", "too", "very",
            "just", "about", "up", "out", "how", "what", "when", "where",
            "who", "why", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "only", "own", "same", "as",
            "into", "over", "after", "before", "between", "under", "again",
            "new", "says", "said", "also", "now", "get", "here", "our",
            "one", "two", "first", "last", "being", "his", "her", "their",
            "your", "there", "them", "they", "we", "us", "he", "she",
        }
        
        # Clean and split
        import re
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        
        # Filter stop words and capitalize properly
        meaningful = []
        for word in words:
            if word.lower() not in stop_words and len(word) >= 3:
                meaningful.append(word.capitalize())
        
        return meaningful[:5]  # Top 5 keywords per headline
