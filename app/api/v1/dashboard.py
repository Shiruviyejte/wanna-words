import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_user
from models.article import Article
from models.user import User
from models.word_book import WordBook
from models.word_entry import WordEntry
from utils.response import success_response

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    results = await asyncio.gather(
        db.execute(select(func.count(User.id))),
        db.execute(select(func.count(WordBook.id))),
        db.execute(select(func.count(WordEntry.id))),
        db.execute(select(func.count(Article.id))),
    )
    return success_response({
        "users": results[0].scalar_one(),
        "wordbooks": results[1].scalar_one(),
        "words": results[2].scalar_one(),
        "articles": results[3].scalar_one(),
    })
