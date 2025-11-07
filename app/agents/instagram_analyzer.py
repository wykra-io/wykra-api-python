import logging
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from app.core.config import get_settings
from app.models.instagram import InstagramProfile, InstagramAnalysis

logger = logging.getLogger(__name__)
settings = get_settings()

if not settings.openrouter_api_key:
    raise ValueError(
        "OPENROUTER_API_KEY environment variable is required. "
        "Please set it in your .env file or environment."
    )

openrouter_provider = OpenRouterProvider(api_key=settings.openrouter_api_key)

model = OpenAIChatModel(
    settings.openrouter_model,
    provider=openrouter_provider,
)

instagram_agent = Agent(
    model=model,
    output_type=InstagramAnalysis,
    system_prompt=(
        "You are Wykra, an analytical, skeptical influencer research assistant. "
        "You receive structured JSON about a single Instagram profile. "
        "Return a JSON object matching the InstagramAnalysis schema:\n"
        "- handle: the instagram @handle (without @)\n"
        "- profile_url: url if available\n"
        "- summary: concise overview of the creator\n"
        "- topics: main content themes as short strings\n"
        "- audience: who follows them / geo / interests (inferred)\n"
        "- strengths: bullet-style strengths (credibility, content quality, metrics)\n"
        "- risks: bullet-style risks (fake followers, low engagement, misalignment, controversies)\n"
        "- fit_score: 0-100, higher = better collab potential; be conservative.\n"
        "If data is missing or uncertain, explicitly say so instead of hallucinating."
    ),
)


async def analyze_profile(profile: InstagramProfile) -> InstagramAnalysis:
    logger.info(f"Analyzing profile: {profile.username}")
    result = await instagram_agent.run(
        {
            "username": profile.username,
            "full_name": profile.full_name,
            "bio": profile.bio,
            "followers": profile.followers,
            "following": profile.following,
            "posts_count": profile.posts_count,
            "is_verified": profile.is_verified,
            "is_business": profile.is_business,
            "profile_url": str(profile.profile_url) if profile.profile_url else None,
            "raw": profile.raw,
        }
    )

    analysis: InstagramAnalysis = result.output

    if not analysis.handle:
        analysis.handle = profile.username
    if not analysis.profile_url and profile.profile_url:
        analysis.profile_url = profile.profile_url

    logger.info(f"Analysis complete for {profile.username}")
    return analysis
