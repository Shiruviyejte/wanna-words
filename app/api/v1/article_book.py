from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_admin, require_user
from models.article_book import ArticleBook
from models.article import Article
from models.user import User
from schemas.article import ArticleBookCreate, ArticleBookOut, ArticleBookTreeNode, ArticleBookUpdate
from utils.response import error_response, paginate, success_response
import json

router = APIRouter()


def _to_node(book: ArticleBook) -> dict:
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
    rows = (
        await db.execute(select(ArticleBook).order_by(ArticleBook.type.asc(), ArticleBook.name.asc()))
    ).scalars().all()
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
async def list_article_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None),
    parent_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_user),
):
    stmt = select(ArticleBook)
    count_stmt = select(func.count(ArticleBook.id))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(ArticleBook.name.like(like))
        count_stmt = count_stmt.where(ArticleBook.name.like(like))
    if parent_id is not None:
        stmt = stmt.where(ArticleBook.parent_id == parent_id)
        count_stmt = count_stmt.where(ArticleBook.parent_id == parent_id)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(ArticleBook.type.asc(), ArticleBook.name.asc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    items = [ArticleBookOut.model_validate(b, from_attributes=True).model_dump(mode="json") for b in rows]
    return success_response(paginate(items, total, page, page_size))


@router.post("")
async def create_article_book(
    payload: ArticleBookCreate, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)
):
    if payload.parent_id:
        parent = await db.get(ArticleBook, payload.parent_id)
        if not parent:
            return error_response(code=400, message="父级文章本不存在")
    book = ArticleBook(name=payload.name, parent_id=payload.parent_id, type=payload.type)
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return success_response(ArticleBookOut.model_validate(book, from_attributes=True).model_dump(mode="json"))


@router.get("/{book_id}")
async def get_article_book(book_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    book = await db.get(ArticleBook, book_id)
    if not book:
        return error_response(code=404, message="文章本不存在")
    return success_response(ArticleBookOut.model_validate(book, from_attributes=True).model_dump(mode="json"))


@router.put("/{book_id}")
async def update_article_book(
    book_id: int,
    payload: ArticleBookUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    book = await db.get(ArticleBook, book_id)
    if not book:
        return error_response(code=404, message="文章本不存在")
    data = payload.model_dump(exclude_unset=True, mode="json")
    if "parent_id" in data and data["parent_id"] == book_id:
        return error_response(code=400, message="不能将自身设为父级")
    for k, v in data.items():
        setattr(book, k, v)
    await db.commit()
    await db.refresh(book)
    return success_response(ArticleBookOut.model_validate(book, from_attributes=True).model_dump(mode="json"))


@router.post("/{book_id}/upload")
async def upload_articles(
    book_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """上传 JSON 文件：以文件名为名称创建子文章本(type=1)，导入文章。"""
    parent = await db.get(ArticleBook, book_id)
    if not parent:
        return error_response(code=404, message="文章本不存在")
    if parent.type != 0:
        return error_response(code=400, message="只能在目录类型的文章本下导入")

    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return error_response(code=400, message="文件内容不是合法 JSON")
    if not isinstance(data, list):
        return error_response(code=400, message="JSON 顶层必须是数组")

    # 文件名去掉扩展名作为文章本名称
    import os
    book_name = os.path.splitext(file.filename or "导入文章")[0]

    # 检查是否已有同名子文章本
    existing = (
        await db.execute(
            select(ArticleBook).where(
                ArticleBook.parent_id == book_id,
                ArticleBook.name == book_name,
                ArticleBook.type == 1,
            )
        )
    ).scalar_one_or_none()

    if existing:
        child_book = existing
        # 清空旧文章
        from sqlalchemy import delete
        await db.execute(delete(Article).where(Article.parent_id == child_book.id))
    else:
        child_book = ArticleBook(name=book_name, parent_id=book_id, type=1)
        db.add(child_book)
        await db.flush()

    inserted = 0
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        title_en = str(item.get("title") or "")
        title_zh = str(item.get("titleTranslate") or "")
        content_en = str(item.get("text") or "")
        content_zh = str(item.get("textTranslate") or "")
        audio_src = str(item.get("audioSrc") or "")
        if not title_en and not content_en:
            continue
        article = Article(
            parent_id=child_book.id,
            type="story",
            title_en=title_en,
            title_zh=title_zh,
            content_en=content_en,
            content_zh=content_zh,
            audio_src=audio_src,
            lrc_position=item.get("lrcPosition"),
            question=item.get("question"),
            name_list=item.get("nameList"),
            quote=item.get("quote"),
            model="",
        )
        db.add(article)
        inserted += 1
    await db.commit()
    return success_response({"inserted": inserted, "total": len(data), "book_name": book_name, "book_id": child_book.id})


@router.delete("/{book_id}")
async def delete_article_book(book_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    book = await db.get(ArticleBook, book_id)
    if not book:
        return error_response(code=404, message="文章本不存在")
    await db.delete(book)
    await db.commit()
    return success_response(message="已删除")
