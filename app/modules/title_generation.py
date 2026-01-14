import json
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.schemas import (
    TrendData, 
    GeneratedTitle, 
    TitleGenerationResponse,
    Platform
)

logger = logging.getLogger(__name__)


class TitleGenerationError(Exception):
    """Raised when title generation fails."""
    pass


class AITitleGenerationModule:
    """
    Generates optimized video titles using Groq API.
    
    Responsibilities:
    - Create effective prompts combining transcript and trends
    - Generate multiple distinct title variations
    - Optimize for click-through rate while maintaining accuracy
    - Handle API errors gracefully
    """
    
    # Platform-specific guidance
    PLATFORM_GUIDANCE = {
        Platform.YOUTUBE: {
            "max_length": 70,
            "style": "Use curiosity gaps, numbers, and emotional triggers. YouTube rewards clear, searchable titles.",
        },
        Platform.INSTAGRAM: {
            "max_length": 60,
            "style": "Short, punchy, emoji-friendly. Focus on visual appeal and relatability.",
        },
        Platform.TIKTOK: {
            "max_length": 50,
            "style": "Ultra-short, trendy, use Gen-Z language. Hook in first 3 words.",
        },
        Platform.TWITTER: {
            "max_length": 60,
            "style": "Concise, shareable, conversation-starting. Leave room for retweet comments.",
        },
        Platform.GENERAL: {
            "max_length": 70,
            "style": "Balanced approach: clear, engaging, and platform-agnostic.",
        },
    }
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self._client = None
        
        if not self.api_key:
            logger.warning("Groq API key not configured")
    
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
                raise TitleGenerationError("groq package not installed. Run: pip install groq")
        return self._client
    
    def _create_system_prompt(self, platform: Platform) -> str:
        """Create the system prompt for title generation."""
        guidance = self.PLATFORM_GUIDANCE.get(platform, self.PLATFORM_GUIDANCE[Platform.GENERAL])
        
        return f"""You are an expert video title strategist specializing in viral content optimization.

Your task is to generate highly engaging, click-worthy video titles that:
1. Accurately represent the video content (no misleading clickbait)
2. Incorporate current trending topics when relevant
3. Maximize click-through rate (CTR)
4. Are optimized for {platform.value}

Platform Guidelines:
- Maximum length: {guidance['max_length']} characters
- Style: {guidance['style']}

Title Styles to Use:
- "How-to": Educational, clear benefit (e.g., "How I Learned X in 30 Days")
- "Curiosity Gap": Create intrigue without revealing everything (e.g., "The One Thing Nobody Tells You About...")
- "Listicle": Numbers work (e.g., "5 Ways to...", "Top 10...")
- "Challenge/Story": Personal narrative (e.g., "I Tried X for a Week...")
- "Contrarian": Challenge assumptions (e.g., "Why Everyone Is Wrong About...")

You MUST respond with valid JSON only. No markdown, no explanation outside the JSON."""

    def _create_user_prompt(
        self, 
        transcript: str, 
        trends: list[TrendData],
        num_titles: int
    ) -> str:
        """Create the user prompt with transcript and trends."""
        
        # Summarize transcript if too long (keep under ~2000 chars for prompt efficiency)
        if len(transcript) > 2000:
            transcript_text = transcript[:1000] + "\n...[middle truncated]...\n" + transcript[-1000:]
        else:
            transcript_text = transcript
        
        # Aggregate trend keywords
        trend_keywords = []
        for trend in trends:
            trend_keywords.extend(trend.keywords[:5])
        trend_keywords = list(dict.fromkeys(trend_keywords))[:15]  # Dedupe, limit to 15
        
        trends_text = ", ".join(trend_keywords) if trend_keywords else "No specific trends available"
        
        return f"""Generate {num_titles} unique video titles based on the following:

VIDEO TRANSCRIPT:
{transcript_text}

CURRENT TRENDING TOPICS:
{trends_text}

REQUIREMENTS:
1. Each title must be distinct in style and approach
2. Titles should be accurate to the video content
3. Incorporate trends ONLY if naturally relevant
4. Vary between different title styles (how-to, curiosity, listicle, etc.)

Respond with this exact JSON structure:
{{
    "transcript_summary": "2-3 sentence summary of the video content",
    "titles": [
        {{
            "title": "The actual title text",
            "style": "curiosity|how-to|listicle|story|contrarian",
            "reasoning": "Brief explanation of why this title works"
        }}
    ],
    "trends_used": ["list", "of", "trends", "incorporated"]
}}"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_groq_api(self, system_prompt: str, user_prompt: str) -> str:
        """Make API call to Groq with retry logic."""
        client = self._get_client()
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,  # Higher for creative titles
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content
    
    def _parse_response(self, response_text: str) -> TitleGenerationResponse:
        """Parse and validate the API response."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise TitleGenerationError(f"Invalid JSON response from API: {e}")
        
        # Extract titles
        titles = []
        for item in data.get("titles", []):
            titles.append(GeneratedTitle(
                title=item.get("title", ""),
                style=item.get("style", "general"),
                reasoning=item.get("reasoning")
            ))
        
        if not titles:
            raise TitleGenerationError("No titles generated")
        
        return TitleGenerationResponse(
            titles=titles,
            transcript_summary=data.get("transcript_summary", ""),
            trends_used=data.get("trends_used", [])
        )
    
    def generate_titles(
        self,
        transcript: str,
        trends: list[TrendData],
        platform: Platform = Platform.GENERAL,
        num_titles: int = 5
    ) -> TitleGenerationResponse:
        """
        Generate optimized video titles.
        
        Args:
            transcript: The video transcript
            trends: List of trend data from various sources
            platform: Target platform for optimization
            num_titles: Number of titles to generate (1-10)
            
        Returns:
            TitleGenerationResponse with generated titles
            
        Raises:
            TitleGenerationError: If generation fails
        """
        if not self.is_configured():
            raise TitleGenerationError(
                "Groq API key not configured. Set GROQ_API_KEY in .env"
            )
        
        if not transcript or len(transcript.strip()) < 50:
            raise TitleGenerationError(
                "Transcript too short for meaningful title generation"
            )
        
        num_titles = max(1, min(10, num_titles))
        
        logger.info(f"Generating {num_titles} titles for platform: {platform.value}")
        
        try:
            system_prompt = self._create_system_prompt(platform)
            user_prompt = self._create_user_prompt(transcript, trends, num_titles)
            
            response_text = self._call_groq_api(system_prompt, user_prompt)
            result = self._parse_response(response_text)
            
            logger.info(f"Successfully generated {len(result.titles)} titles")
            return result
            
        except TitleGenerationError:
            raise
        except Exception as e:
            raise TitleGenerationError(f"Title generation failed: {str(e)}")
    
    def get_status(self) -> dict:
        """Get module status."""
        return {
            "configured": self.is_configured(),
            "model": self.model,
            "supported_platforms": [p.value for p in Platform]
        }
