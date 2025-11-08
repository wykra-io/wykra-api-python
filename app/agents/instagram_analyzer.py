import json
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

SYSTEM_PROMPT = (
    "You are Wykra, an analytical, skeptical influencer research assistant. "
    "You receive structured JSON about a single Instagram profile and must respond ONLY with JSON "
    "matching the InstagramAnalysis schema:\n"
    "- handle: instagram handle (without @)\n"
    "- profile_url: profile URL if available\n"
    "- summary: concise overview of the creator\n"
    "- topics: main content themes as short strings\n"
    "- audience: who follows them / geo / interests (inferred from data)\n"
    "- strengths: bullet-style strengths\n"
    "- risks: bullet-style risks\n"
    "- fit_score: 0-100, higher = better collab potential; be conservative.\n"
    "Use only the provided data. If something is missing or uncertain, say so explicitly."
)

instagram_agent = Agent(
    model=model,
    output_type=InstagramAnalysis,
    system_prompt=SYSTEM_PROMPT,
)


async def analyze_profile(profile: InstagramProfile) -> InstagramAnalysis:
    logger.info("Analyzing profile: %s", profile.username)

    payload = {
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

    user_prompt = (
        "Analyze the following Instagram profile data and produce an InstagramAnalysis JSON.\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    result = await instagram_agent.run(user_prompt)
    base = result.output

    final = InstagramAnalysis(
        handle=base.handle or profile.username,
        profile_url=base.profile_url or profile.profile_url,
        summary=base.summary,
        topics=base.topics,
        audience=base.audience,
        strengths=base.strengths,
        risks=base.risks,
        fit_score=base.fit_score,
    )

    logger.info("Analysis complete for %s", profile.username)
    return final
