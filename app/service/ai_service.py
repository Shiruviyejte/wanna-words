import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.ai_config import UserAIConfig
from utils.response import BizException

STORY_PROMPT = """
You are writing bilingual stories for English learners.
Always return valid JSON only.
The JSON schema must be:
{"title_en":"...", "title_zh":"...", "content_en":"...", "content_zh":"..."}

Rules:
- content_en must be natural English.
- content_zh must be a faithful Simplified Chinese translation.
- The story should be clear, practical, warm, and easy to follow.
- Match the requested difficulty.
- If target words are provided, use them naturally in realistic daily situations.
- The total number of words in content_en should be approximately <total_words>. (This is an external input.)
- Format the story into multiple paragraphs. Each paragraph must not exceed 500 characters (letters, not words). Count includes spaces and punctuation.
- Ensure both content_en and content_zh follow the same paragraph structure and length limit.
- Do not output markdown fences or any extra commentary.
""".strip()

WORD_PROMPT = """
You are an English dictionary assistant. For the given word, return detailed bilingual information.
Always return valid JSON only. The JSON schema must be:

{
  "word": "...",
  "phonetic0": "...",
  "phonetic1": "...",
  "trans": [{"pos": "n.", "cn": "含义"}],
  "synos": [{"pos": "n.", "cn": "含义", "ws": ["synonym1", "synonym2"]}],
  "etymology": [{"d": "etymological description", "t": "title"}],
  "sentences": [{"c": "English sentence", "cn": "Chinese translation"}],
  "phrases": [{"c": "English phrase", "cn": "Chinese translation"}]
}

Rules:
- phonetic0 is UK pronunciation (IPA), phonetic1 is US pronunciation (IPA).
- trans: list all common parts of speech with clear Chinese translations.
- synos: provide 2-3 synonym groups with related words.
- etymology: provide 1-2 entries about word origin.
- sentences: provide 3-5 example sentences with Chinese translations.
- phrases: provide 2-4 common phrases/collocations with Chinese translations.
- All Chinese must be Simplified Chinese.
- Do not output markdown fences or any extra commentary.
""".strip()


async def _get_default_config(db: AsyncSession) -> UserAIConfig:
    result = await db.execute(
        select(UserAIConfig).where(UserAIConfig.is_default_mode == True)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise BizException(400, "没有默认 AI 配置，请先在 AI 配置页设置一个默认模型。")
    if not config.api_key:
        raise BizException(400, "默认 AI 配置未设置 API Key，请在 AI 配置页补充。")
    return config


async def _call_ai(
        config: UserAIConfig,
        system_prompt: str,
        user_prompt: str,
) -> dict:
    base_url = (config.base_url or settings.deepseek_base_url).rstrip("/")
    async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
        response = await client.post(
            "/chat/completions",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


async def generate_story(
        db: AsyncSession,
        *,
        gen_type: str,
        topic: str | None = None,
        words: list[str] | None = None,
        difficulty: str = "medium",
        word_count: int = 200
) -> dict:
    """Generate a bilingual story and return {title_en, title_zh, content_en, content_zh, gen_input}. """
    config = await _get_default_config(db)

    if gen_type == "topic":
        user_prompt = f"Theme: {topic}. Difficulty: {difficulty}."
        gen_input = {"topic": topic, "difficulty": difficulty}
    else:
        user_prompt = f"Use these words naturally in a story: {', '.join(words)}. Difficulty: {difficulty}."
        gen_input = {"words": words, "difficulty": difficulty}

    final_prompt = STORY_PROMPT.replace("<total_words>", str(word_count))
    ai_response = await _call_ai(config, final_prompt, user_prompt)

    return {
        "title_en": ai_response["title_en"].strip(),
        "title_zh": ai_response["title_zh"].strip(),
        "content_en": ai_response["content_en"].strip(),
        "content_zh": ai_response["content_zh"].strip(),
        "gen_input": gen_input,
        "ai_response": ai_response,
        "model": config.model,
    }


async def generate_word(db: AsyncSession, *, word: str) -> dict:
    """Generate word dictionary info via AI and return dict matching WordEntry fields. """
    config = await _get_default_config(db)

    user_prompt = f"Word: {word}"
    ai_response = await _call_ai(config, WORD_PROMPT, user_prompt)

    return {
        "word": ai_response.get("word", word),
        "phonetic0": ai_response.get("phonetic0", ""),
        "phonetic1": ai_response.get("phonetic1", ""),
        "trans": ai_response.get("trans", []),
        "synos": ai_response.get("synos", []),
        "etymology": ai_response.get("etymology", []),
        "sentences": ai_response.get("sentences", []),
        "phrases": ai_response.get("phrases", []),
        "ai_response": ai_response,
    }
