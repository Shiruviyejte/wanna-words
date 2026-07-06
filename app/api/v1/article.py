from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_admin, require_user
from models.article import Article
from models.user import User
from schemas.article import ArticleBatchUpdate, ArticleCreate, ArticleGenerateRequest, ArticleOut, ArticleUpdate
from utils.response import error_response, paginate, success_response

router = APIRouter()


@router.get("")
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None),
    title_keyword: str | None = Query(None),
    content_keyword: str | None = Query(None),
    book_id: int | None = Query(None),
    type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_user),
):
    stmt = select(Article)
    count_stmt = select(func.count(Article.id))
    if title_keyword:
        like = f"%{title_keyword}%"
        stmt = stmt.where(Article.title_en.like(like) | Article.title_zh.like(like))
        count_stmt = count_stmt.where(Article.title_en.like(like) | Article.title_zh.like(like))
    if content_keyword:
        like = f"%{content_keyword}%"
        stmt = stmt.where(Article.content_en.like(like) | Article.content_zh.like(like))
        count_stmt = count_stmt.where(Article.content_en.like(like) | Article.content_zh.like(like))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            Article.title_en.like(like) | Article.title_zh.like(like) | Article.content_en.like(like) | Article.content_zh.like(like)
        )
        count_stmt = count_stmt.where(
            Article.title_en.like(like) | Article.title_zh.like(like) | Article.content_en.like(like) | Article.content_zh.like(like)
        )
    if book_id:
        stmt = stmt.where(Article.parent_id == book_id)
        count_stmt = count_stmt.where(Article.parent_id == book_id)
    if type:
        stmt = stmt.where(Article.type == type)
        count_stmt = count_stmt.where(Article.type == type)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Article.id.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    items = [ArticleOut.model_validate(a, from_attributes=True).model_dump(mode="json") for a in rows]
    return success_response(paginate(items, total, page, page_size))


@router.post("")
async def create_article(payload: ArticleCreate, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    article = Article(**payload.model_dump())
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return success_response(ArticleOut.model_validate(article, from_attributes=True).model_dump(mode="json"))


@router.get("/by-book/{book_id}")
async def list_articles_by_book(book_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    """根据文章本ID拉取所有文章（不含创建/更新时间）。"""
    stmt = select(Article).where(Article.parent_id == book_id).order_by(Article.id)
    rows = (await db.execute(stmt)).scalars().all()
    return success_response([
        {k: v for k, v in ArticleOut.model_validate(r, from_attributes=True).model_dump(mode="json").items() if k not in ("created_at", "updated_at")}
        for r in rows
    ])


@router.get("/{article_id}")
async def get_article(article_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_user)):
    article = await db.get(Article, article_id)
    if not article:
        return error_response(code=404, message="文章不存在")
    return success_response(ArticleOut.model_validate(article, from_attributes=True).model_dump(mode="json"))


@router.put("/{article_id}")
async def update_article(
    article_id: int,
    payload: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    article = await db.get(Article, article_id)
    if not article:
        return error_response(code=404, message="文章不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(article, k, v)
    await db.commit()
    await db.refresh(article)
    return success_response(ArticleOut.model_validate(article, from_attributes=True).model_dump(mode="json"))


@router.post("/batch-update")
async def batch_update_articles(
    payload: ArticleBatchUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    stmt = select(Article).where(Article.parent_id == payload.book_id)
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return error_response(code=404, message="该文章本下没有文章")
    updated = 0
    for a in rows:
        if payload.type is not None:
            a.type = payload.type
        if payload.audio_find is not None:
            find = payload.audio_find or ""
            replace = payload.audio_replace or ""
            old = a.audio_src or ""
            if find and old:
                a.audio_src = old.replace(find, replace)
        if payload.audio_prefix is not None:
            prefix = payload.audio_prefix or ""
            old = a.audio_src or ""
            if old and not old.startswith(prefix):
                a.audio_src = prefix + old
        updated += 1
    await db.commit()
    return success_response({"updated": updated, "total": len(rows)})


@router.post("/generate")
async def generate_article(
    payload: ArticleGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """AI 生成文章：按主题或指定单词生成双语故事。"""
    from service.ai_service import generate_story

    if payload.gen_type == "topic" and not payload.topic:
        return error_response(code=400, message="主题模式下 topic 不能为空")
    if payload.gen_type == "words" and (not payload.words or not len(payload.words)):
        return error_response(code=400, message="单词模式下 words 不能为空")

    result = await generate_story(
        db,
        gen_type=payload.gen_type,
        topic=payload.topic,
        words=payload.words,
        difficulty=payload.difficulty,
        word_count=payload.word_count,
    )

    article = Article(
        parent_id=payload.book_id,
        type="story",
        title_en=result["title_en"],
        title_zh=result["title_zh"],
        content_en=result["content_en"],
        content_zh=result["content_zh"],
        model=result["model"],
        gen_type=payload.gen_type,
        gen_input=result["gen_input"],
        ai_response=result["ai_response"],
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return success_response(ArticleOut.model_validate(article, from_attributes=True).model_dump(mode="json"))


@router.delete("/{article_id}")
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    article = await db.get(Article, article_id)
    if not article:
        return error_response(code=404, message="文章不存在")
    await db.delete(article)
    await db.commit()
    return success_response(message="已删除")
