from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, func, select, String as SAString
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_admin, require_user
from models.user import User
from models.word_entry import WordEntry
from schemas.article import WordGenerateRequest
from schemas.word import WordEntryCreate, WordEntryOut, WordEntryUpdate
from utils.response import error_response, paginate, success_response

router = APIRouter()

@router.get("")
async def list_words(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None),
    word_keyword: str | None = Query(None),
    trans_keyword: str | None = Query(None),
    book_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_user),
):
    stmt = select(WordEntry)
    count_stmt = select(func.count(WordEntry.id))
    if word_keyword:
        like = f"%{word_keyword}%"
        stmt = stmt.where(WordEntry.word.like(like))
        count_stmt = count_stmt.where(WordEntry.word.like(like))
    if trans_keyword:
        like = f"%{trans_keyword}%"
        stmt = stmt.where(cast(WordEntry.trans, SAString).like(like))
        count_stmt = count_stmt.where(cast(WordEntry.trans, SAString).like(like))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            WordEntry.word.like(like) | cast(WordEntry.trans, SAString).like(like)
        )
        count_stmt = count_stmt.where(
            WordEntry.word.like(like) | cast(WordEntry.trans, SAString).like(like)
        )
    if book_id:
        stmt = stmt.where(WordEntry.book_id == book_id)
        count_stmt = count_stmt.where(WordEntry.book_id == book_id)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(WordEntry.id.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    items = [WordEntryOut.model_validate(w, from_attributes=True).model_dump(mode="json") for w in rows]
    return success_response(paginate(items, total, page, page_size))


@router.get("/simple")
async def list_words_simple(db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    """返回所有单词的精简信息：word + trans.cn，供前端搜索筛选使用。"""
    stmt = select(WordEntry.word, WordEntry.trans).order_by(WordEntry.word)
    rows = (await db.execute(stmt)).all()
    items = [
        {
            "word": row.word,
            "trans": row.trans,
        }
        for row in rows
    ]
    return success_response(items)


@router.post("")
async def create_word(payload: WordEntryCreate, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    entry = WordEntry(**payload.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return success_response(WordEntryOut.model_validate(entry, from_attributes=True).model_dump(mode="json"))


@router.get("/by-book/{book_id}")
async def list_words_by_book(book_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    """根据词库ID拉取所有单词（不含创建/更新时间）。"""
    stmt = select(WordEntry).where(WordEntry.book_id == book_id).order_by(WordEntry.word)
    rows = (await db.execute(stmt)).scalars().all()
    return success_response([
        {k: v for k, v in WordEntryOut.model_validate(r, from_attributes=True).model_dump(mode="json").items() if k not in ("created_at", "updated_at")}
        for r in rows
    ])


@router.get("/{word_id}")
async def get_word(word_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    entry = await db.get(WordEntry, word_id)
    if not entry:
        return error_response(code=404, message="单词不存在")
    return success_response(WordEntryOut.model_validate(entry, from_attributes=True).model_dump(mode="json"))


@router.put("/{word_id}")
async def update_word(
    word_id: int,
    payload: WordEntryUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    entry = await db.get(WordEntry, word_id)
    if not entry:
        return error_response(code=404, message="单词不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(entry, k, v)
    await db.commit()
    await db.refresh(entry)
    return success_response(WordEntryOut.model_validate(entry, from_attributes=True).model_dump(mode="json"))


@router.post("/generate")
async def generate_word(
    payload: WordGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """AI 生成单词信息：调用 AI 获取释义、例句、词源等。"""
    from service.ai_service import generate_word as ai_generate_word

    result = await ai_generate_word(db, word=payload.word)

    entry = WordEntry(
        book_id=payload.book_id,
        word=result["word"],
        phonetic0=result["phonetic0"],
        phonetic1=result["phonetic1"],
        trans=result["trans"],
        synos=result["synos"],
        etymology=result["etymology"],
        sentences=result["sentences"],
        phrases=result["phrases"],
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return success_response(WordEntryOut.model_validate(entry, from_attributes=True).model_dump(mode="json"))


@router.delete("/{word_id}")
async def delete_word(word_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    entry = await db.get(WordEntry, word_id)
    if not entry:
        return error_response(code=404, message="单词不存在")
    await db.delete(entry)
    await db.commit()
    return success_response(message="已删除")
