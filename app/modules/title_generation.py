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
        
        return f"""You are an expert viral video title strategist. You generate titles across 3 distinct tiers with different formatting styles.

You MUST generate exactly 10 titles split into 3 tiers:

=== TIER 1: AGGRESSIVE (5 titles) ===
- BOLD, high-energy, scroll-stopping titles
- MUST use emojis (🔥 ⚠️ 💀 etc.) AND special characters (!! ? —)
- MUST include at least one CAPITALIZED power word (INSANE, BRUTAL, SHOCKING, NOBODY, EVERYTHING)
- Use trending topics when relevant
- Can be normal length (up to {guidance['max_length']} chars)
- Examples:
  * "I Mastered X in 24 Hours — Here's EXACTLY How!!! 🔥"
  * "This Changes EVERYTHING About X?! (Nobody Saw This Coming) 💀"
  * "7 BRUTAL Truths About X That Will Blow Your Mind 🔥"
  * "I Tried X and What Happened Next Was INSANE!!! ⚠️"
  * "STOP Doing X Right Now!! Here's Why Everyone Is WRONG 💀"

=== TIER 2: PUNCHY (3 titles) ===
- Short, sharp, high-energy titles
- Use special characters (!! ? ... —) but NO emojis
- Can use CAPS for emphasis
- Use trending topics when relevant
- Keep titles SHORT and snappy
- Examples:
  * "I Built This in 24 Hours — NOBODY Believed It!!"
  * "Why EVERYTHING You Know About X Is Wrong?!"
  * "The SECRET Method That Changes Everything!!"

=== TIER 3: PLAIN (2 titles) ===
- Short, clean, professional titles
- NO emojis and NO special characters (no !! no ? no —)
- Based ONLY on the transcript content, IGNORE all trending topics
- Simple, clear, and direct
- Keep titles SHORT
- Examples:
  * "Building an AI Application from Scratch with Python"
  * "What I Learned After 30 Days of Machine Learning"

Platform: {platform.value}
Style: {guidance['style']}

RULES:
- Generate 3-5 relevant hashtags per title (ALL tiers get hashtags)
- Each title must be distinct in style (mix of how-to, curiosity, listicle, story, contrarian)
- Plain titles must ONLY use transcript content — no trends

You MUST respond with valid JSON only. No markdown, no explanation outside the JSON."""

    def _create_user_prompt(
        self, 
        transcript: str, 
        trends: list[TrendData]
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
        
        return f"""Generate exactly 10 video titles in 3 tiers based on the following:

VIDEO TRANSCRIPT:
{transcript_text}

CURRENT TRENDING TOPICS (use for Aggressive and Punchy tiers ONLY, NOT for Plain):
{trends_text}

GENERATE EXACTLY:
- 5 AGGRESSIVE titles (with emojis + special characters + trends)
- 3 PUNCHY titles (short, special characters only, NO emojis + trends)
- 2 PLAIN titles (short, clean, NO emojis, NO special characters, transcript-only, IGNORE trends)

Each title MUST have 3-5 hashtags with # prefix.
Each title must be distinct in style (vary between how-to, curiosity, listicle, story, contrarian).

Respond with this exact JSON structure:
{{
    "transcript_summary": "2-3 sentence summary of the video content",
    "titles": [
        {{
            "title": "The title text",
            "style": "curiosity|how-to|listicle|story|contrarian",
            "tier": "aggressive|punchy|plain",
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
            max_tokens=3000,  # Increased for 10 titles across 3 tiers
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
                tier=item.get("tier", "aggressive"),
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
        num_titles: int = 10
    ) -> TitleGenerationResponse:
        """
        Generate 10 optimized video titles across 3 tiers.
        
        Always generates exactly 10 titles:
        - 5 Aggressive (emojis + special chars + trends)
        - 3 Punchy (short, special chars only, no emojis + trends)
        - 2 Plain (short, clean, transcript-only, no trends)
        
        Args:
            transcript: The video transcript
            trends: List of trend data from various sources
            platform: Target platform for optimization
            num_titles: Ignored — always generates 10
            
        Returns:
            TitleGenerationResponse with 10 generated titles
            
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
        
        logger.info(f"Generating 10 titles (5 aggressive + 3 punchy + 2 plain) for platform: {platform.value}")
        
        try:
            system_prompt = self._create_system_prompt(platform)
            user_prompt = self._create_user_prompt(transcript, trends)
            
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
