import json
import random
from dataclasses import dataclass

import httpx

from core.config import settings
from utils.response import BizException

THEMES = ["daily life", "travel", "school", "science", "friendship", "adventure"]

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
- Do not output markdown fences or any extra commentary.
""".strip()


@dataclass
class StoryResult:
    title_en: str
    title_zh: str
    content_en: str
    content_zh: str


class StoryGeneratorService:
    async def generate_random_story(
        self, *, difficulty: str, api_key: str | None = None, model: str | None = None
    ) -> tuple[StoryResult, dict]:
        theme = random.choice(THEMES)
        story = await self._generate_story(theme=theme, difficulty=difficulty, words=None, api_key=api_key, model=model)
        return story, {"theme": theme, "difficulty": difficulty}

    async def generate_words_story(
        self, *, words: list[str], difficulty: str, api_key: str | None = None, model: str | None = None
    ) -> tuple[StoryResult, dict]:
        theme = "word practice"
        story = await self._generate_story(theme=theme, difficulty=difficulty, words=words, api_key=api_key, model=model)
        return story, {"words": words, "difficulty": difficulty}

    async def generate_theme_story(
        self, *, theme: str, difficulty: str, api_key: str | None = None, model: str | None = None
    ) -> tuple[StoryResult, dict]:
        story = await self._generate_story(theme=theme, difficulty=difficulty, words=None, api_key=api_key, model=model)
        return story, {"theme": theme, "difficulty": difficulty}

    async def _generate_story(
        self, *, theme: str, difficulty: str, words: list[str] | None, api_key: str | None, model: str | None
    ) -> StoryResult:
        resolved_api_key = api_key or settings.deepseek_api_key
        if not resolved_api_key:
            raise BizException(400, "DeepSeek API Key 未配置，无法生成故事。")
        return await self._call_remote(
            theme=theme,
            difficulty=difficulty,
            words=words,
            api_key=resolved_api_key,
            model=model or settings.deepseek_model,
        )

    async def _call_remote(
        self, *, theme: str, difficulty: str, words: list[str] | None, api_key: str, model: str
    ) -> StoryResult:
        words_prompt = ""
        if words:
            words_prompt = f"Use these words naturally in the story: {', '.join(words)}."

        prompt = (
            f"Theme: {theme}. "
            f"Difficulty: {difficulty}. "
            f"{words_prompt}"
        ).strip()

        async with httpx.AsyncClient(base_url=settings.deepseek_base_url, timeout=60.0) as client:
            response = await client.post(
                "/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": STORY_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return StoryResult(
            title_en=data["title_en"].strip(),
            title_zh=data["title_zh"].strip(),
            content_en=data["content_en"].strip(),
            content_zh=data["content_zh"].strip(),
        )


story_generator_service = StoryGeneratorService()
