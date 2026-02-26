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
            "style": "AGGRESSIVE curiosity gaps, power words, CAPS for emphasis. Use !! and ? to create urgency. YouTube rewards bold, searchable titles that STOP the scroll.",
        },
        Platform.INSTAGRAM: {
            "max_length": 60,
            "style": "Short, PUNCHY, emoji-heavy 🔥💀⚠️. Make it feel urgent and unmissable. Relatability + shock value.",
        },
        Platform.TIKTOK: {
            "max_length": 50,
            "style": "Ultra-short, VIRAL energy, Gen-Z language. Hook in first 3 words. Use !! and emojis aggressively.",
        },
        Platform.TWITTER: {
            "max_length": 60,
            "style": "Hot-take energy, conversation-starting, PROVOCATIVE. Use ? and !! to drive engagement.",
        },
        Platform.GENERAL: {
            "max_length": 70,
            "style": "Bold, high-energy, attention-grabbing. Use power words and special characters to stand out.",
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
        
        return f"""You are an AGGRESSIVE viral video title strategist. You create titles that STOP the scroll and make people NEED to click.

Your task is to generate BOLD, high-energy, attention-grabbing video titles that:
1. Use special characters strategically: !! ? 🔥 ⚠️ 💀 to amplify urgency and emotion
2. Include at least one CAPITALIZED power word per title (e.g., INSANE, BRUTAL, SHOCKING, NOBODY, EVERYTHING)
3. Create a sense of urgency — boring titles get ZERO clicks
4. Incorporate current trending topics when relevant
5. Are optimized for {platform.value}

Platform Guidelines:
- Maximum length: {guidance['max_length']} characters
- Style: {guidance['style']}

Title Styles to Use (be AGGRESSIVE with each):
- "how-to": Bold educational hook (e.g., "I Mastered X in 24 Hours — Here's EXACTLY How!!!")
- "curiosity": Shock/urgency gap (e.g., "This Changes EVERYTHING About X?! (Nobody Saw This Coming)")
- "listicle": Power number-based (e.g., "7 BRUTAL Truths About X That Will Blow Your Mind 🔥")
- "story": Dramatic personal narrative (e.g., "I Tried X and What Happened Next Was INSANE!!!")
- "contrarian": Provocative hot-take (e.g., "STOP Doing X Right Now!! Here's Why Everyone Is WRONG 💀")

RULES:
- EVERY title MUST contain at least one special character (!! or ? or 🔥 or ⚠️ or 💀)
- EVERY title MUST have at least one word in ALL CAPS for emphasis
- NO generic, safe, boring titles — if it doesn't create urgency, rewrite it
- Generate 3-5 relevant hashtags per title for discoverability

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
        
        return f"""Generate {num_titles} unique AGGRESSIVE video titles based on the following:

VIDEO TRANSCRIPT:
{transcript_text}

CURRENT TRENDING TOPICS:
{trends_text}

REQUIREMENTS:
1. Each title MUST use special characters (!! ? 🔥 ⚠️ 💀) for emphasis
2. Each title MUST have at least one CAPITALIZED power word
3. Titles should feel URGENT, bold, and unmissable
4. Incorporate trends when naturally relevant
5. NO boring, generic, or "safe" titles — every title must STOP the scroll
6. Each title must be distinct in style and approach
7. Generate 3-5 relevant hashtags per title (with # prefix) for trending discoverability

Respond with this exact JSON structure:
{{
    "transcript_summary": "2-3 sentence summary of the video content",
    "titles": [
        {{
            "title": "The actual AGGRESSIVE title text with special characters!!",
            "style": "curiosity|how-to|listicle|story|contrarian",
            "reasoning": "Brief explanation of why this title works",
            "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
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
                reasoning=item.get("reasoning"),
                hashtags=item.get("hashtags", [])
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
