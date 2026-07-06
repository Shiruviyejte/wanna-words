from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from api.deps import require_user
from models.user import User
from service.translate import build_youdao_sentence_voice_url, build_youdao_word_voice_url
from utils.response import error_response, success_response

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    model: str | None = None

@router.get("/voice/word")
async def word_voice(text: str = Query(..., min_length=1, max_length=200), _user: User = Depends(require_user)):
    """获取单词发音 URL（有道）"""
    url = build_youdao_word_voice_url(text=text)
    return success_response({"url": url, "text": text})


@router.get("/voice/sentence")
async def sentence_voice(
    text: str = Query(..., min_length=1, max_length=500),
    rate: int = Query(4, ge=1, le=10),
    lang: str = Query("eng", max_length=10),
    voice_type: str = Query("2", max_length=10),
    _user: User = Depends(require_user),
):
    """获取句子发音 URL（有道）"""
    url = build_youdao_sentence_voice_url(text=text, rate=rate, lang=lang, voice_type=voice_type)
    return success_response({"url": url, "text": text})
