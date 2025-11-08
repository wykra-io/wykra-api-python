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
    "You are Wykra, an analytical influencer research agent. "
    "Your task is to evaluate an Instagram profile based solely on the provided JSON data. "
    "Please analyze the profile and provide a comprehensive assessment covering:\n\n"
    "1. Topic/Niche: What is the influencer's main topic or niche?\n"
    "2. Sponsored Content: Are they sponsored frequently? How often do you see sponsored content?\n"
    "3. Content Authenticity: Is the content authentic or does it seem AI-generated/artificial?\n"
    "4. Follower Authenticity: Are their followers likely real or do you see signs of fake/bought followers?\n"
    "5. Visible Brands: What brands are visible in their content or collaborations?\n"
    "6. Engagement Strength: How strong is the engagement? Is it consistent and genuine?\n"
    "7. Posts Analysis: Analyze the posting patterns, content quality, and consistency.\n"
    "8. Hashtags Statistics: What hashtags do they use most? Are they relevant to their niche?\n\n"
    "Return your analysis as a JSON object with the following structure:\n"
    "{\n"
    '  "summary": "A comprehensive 2-3 paragraph summary of the profile analysis",\n'
    '  "qualityScore": <number from 1 to 5>,\n'
    '  "topic": "<main topic/niche>",\n'
    '  "niche": "<specific niche if applicable>",\n'
    '  "sponsoredFrequency": "<low/medium/high>",\n'
    '  "contentAuthenticity": "<authentic/artificial/mixed>",\n'
    '  "followerAuthenticity": "<likely real/likely fake/mixed>",\n'
    '  "visibleBrands": ["<brand1>", "<brand2>", ...],\n'
    '  "engagementStrength": "<weak/moderate/strong>",\n'
    '  "postsAnalysis": "<detailed analysis of posts>",\n'
    '  "hashtagsStatistics": "<analysis of hashtag usage>"\n'
    "}\n\n"
    "Quality Score Guidelines:\n"
    "- 1: Very poor quality, likely fake, low engagement, spam-like content\n"
    "- 2: Poor quality, suspicious activity, low authenticity\n"
    "- 3: Average quality, some concerns but generally acceptable\n"
    "- 4: Good quality, authentic content, strong engagement\n"
    "- 5: Excellent quality, highly authentic, strong engagement, established presence\n\n"
    "Use only the provided data. If something is missing, say so explicitly.\n"
    "Return ONLY the JSON object, with no additional text or markdown formatting."
)

instagram_agent = Agent(
    model=model,
    output_type=InstagramAnalysis,
    system_prompt=SYSTEM_PROMPT,
)


async def analyze_profile(profile: InstagramProfile) -> InstagramAnalysis:
    """Run the Instagram analysis agent for a given profile.

    Args:
        profile: The normalized Instagram profile data to analyze.

    Returns:
        An :class:`InstagramAnalysis` containing the agent's findings.
    """
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
        "profile_url": profile.profile_url,
        "raw": profile.raw,
    }

    user_prompt = json.dumps(payload, ensure_ascii=False)

    result = await instagram_agent.run(user_prompt)

    analysis = result.output
    logger.info("Analysis complete for %s", profile.username)
    return analysis
