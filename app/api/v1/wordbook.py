import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_admin, require_user
from models.word_book import WordBook
from models.word_entry import WordEntry
from schemas.word import WordEntryOut
from schemas.wordbook import WordBookCreate, WordBookOut, WordBookTreeNode, WordBookUpdate
from utils.response import error_response, paginate, success_response
from models.user import User

router = APIRouter()


def _to_node(book: WordBook) -> dict:
    return {
        "id": book.id,
        "parent_id": book.parent_id,
        "type": book.type,
        "name": book.name,
        "created_at": book.created_at,
        "updated_at": book.updated_at,
        "children": [],
    }


@router.get("/tree")
async def get_tree(db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    rows = (await db.execute(select(WordBook).order_by(WordBook.type.asc(), WordBook.name.asc()))).scalars().all()
    nodes = {b.id: _to_node(b) for b in rows}
    roots: list[dict] = []
    for b in rows:
        node = nodes[b.id]
        if b.parent_id and b.parent_id in nodes:
            nodes[b.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return success_response(roots)


@router.get("")
async def list_wordbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None),
    parent_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_user),
):
    stmt = select(WordBook).where(WordBook.type == 1)
    count_stmt = select(func.count(WordBook.id)).where(WordBook.type ==1)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(WordBook.name.like(like))
        count_stmt = count_stmt.where(WordBook.name.like(like))
    if parent_id is not None:
        stmt = stmt.where(WordBook.parent_id == parent_id)
        count_stmt = count_stmt.where(WordBook.parent_id == parent_id)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(WordBook.type.asc(), WordBook.name.asc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    items = [WordBookOut.model_validate(b, from_attributes=True).model_dump(mode="json") for b in rows]
    return success_response(paginate(items, total, page, page_size))


@router.post("")
async def create_wordbook(payload: WordBookCreate, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    if payload.parent_id:
        parent = await db.get(WordBook, payload.parent_id)
        if not parent:
            return error_response(code=400, message="父级词库不存在")
    book = WordBook(name=payload.name, parent_id=payload.parent_id, type=payload.type)
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return success_response(WordBookOut.model_validate(book, from_attributes=True).model_dump(mode="json"))


@router.get("/{book_id}")
async def get_wordbook(book_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    book = await db.get(WordBook, book_id)
    if not book:
        return error_response(code=404, message="词库不存在")
    return success_response(WordBookOut.model_validate(book, from_attributes=True).model_dump(mode="json"))


@router.put("/{book_id}")
async def update_wordbook(
    book_id: int,
    payload: WordBookUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    book = await db.get(WordBook, book_id)
    if not book:
        return error_response(code=404, message="词库不存在")
    data = payload.model_dump(exclude_unset=True, mode="json")
    if "parent_id" in data and data["parent_id"] == book_id:
        return error_response(code=400, message="不能将自身设为父级")
    for k, v in data.items():
        setattr(book, k, v)
    await db.commit()
    await db.refresh(book)
    return success_response(WordBookOut.model_validate(book, from_attributes=True).model_dump(mode="json"))


@router.delete("/{book_id}")
async def delete_wordbook(book_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    book = await db.get(WordBook, book_id)
    if not book:
        return error_response(code=404, message="词库不存在")
    await db.delete(book)
    await db.commit()
    return success_response(message="已删除")


@router.get("/{book_id}/words")
async def list_words_in_book(
    book_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_user),
):
    book = await db.get(WordBook, book_id)
    if not book:
        return error_response(code=404, message="词库不存在")
    stmt = select(WordEntry).where(WordEntry.book_id == book_id)
    count_stmt = select(func.count(WordEntry.id)).where(WordEntry.book_id == book_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(WordEntry.word.like(like))
        count_stmt = count_stmt.where(WordEntry.word.like(like))
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(WordEntry.sequence.asc(), WordEntry.id.asc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    items = [WordEntryOut.model_validate(w, from_attributes=True).model_dump(mode="json") for w in rows]
    return success_response(paginate(items, total, page, page_size))


def _normalize_word_payload(item: dict, book_id: int, sequence: int) -> dict:
    """将上传 JSON 中的驼峰键映射为模型字段。"""

    def _list(v: Any) -> list:
        return v if isinstance(v, list) else []

    return {
        "book_id": book_id,
        "source_entry_id": item.get("id"),
        "word": item.get("word", ""),
        "phonetic0": item.get("phonetic0"),
        "phonetic1": item.get("phonetic1"),
        "synos": _list(item.get("synos")),
        "etymology": _list(item.get("etymology")),
        "inflections": item.get("inflections"),
        "e2e": item.get("e2e"),
        "exams_src": item.get("examsSrc"),
        "rel_words": item.get("relWords"),
        "lang_type": item.get("langType", "en"),
        "trans": _list(item.get("trans")),
        "sentences": _list(item.get("sentences")),
        "phrases": _list(item.get("phrases")),
        "entry_type": item.get("entryType", "word"),
        "sequence": sequence,
    }


@router.post("/{book_id}/upload")
async def upload_words(
    book_id: int,
    file: UploadFile = File(...),
    replace: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    parent = await db.get(WordBook, book_id)
    if not parent:
        return error_response(code=404, message="词库不存在")

    # 以文件名为名称创建子词库(type=1 文件)
    filename = file.filename or "unknown"
    child_name = filename.rsplit(".", 1)[0] if "." in filename else filename

    # 检查是否已存在同名子词库,有则替换
    existing = (
        await db.execute(
            select(WordBook).where(
                WordBook.parent_id == book_id,
                WordBook.name == child_name,
            )
        )
    ).scalar_one_or_none()
    if existing:
        child_book = existing
        await db.execute(
            WordEntry.__table__.delete().where(WordEntry.book_id == child_book.id)
        )
    else:
        child_book = WordBook(name=child_name, parent_id=book_id, type=1)
        db.add(child_book)
        await db.flush()

    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return error_response(code=400, message="文件内容不是合法 JSON")
    if not isinstance(data, list):
        return error_response(code=400, message="JSON 顶层必须是数组")

    if replace:
        await db.execute(
            WordEntry.__table__.delete().where(WordEntry.book_id == child_book.id)
        )

    inserted = 0
    sequence = 1
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict) or not item.get("word"):
            continue
        payload = _normalize_word_payload(item, child_book.id, sequence)
        db.add(WordEntry(**payload))
        sequence += 1
        inserted += 1
    await db.commit()
    return success_response({"inserted": inserted, "total": len(data), "book_id": child_book.id, "book_name": child_name})
