from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_admin, require_user
from models.ai_config import UserAIConfig
from models.user import User
from schemas.ai_config import AIConfigCreate, AIConfigOut, AIConfigUpdate
from utils.response import error_response, paginate, success_response

router = APIRouter()


@router.get("")
async def list_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_user),
):
    stmt = select(UserAIConfig)
    count_stmt = select(func.count(UserAIConfig.id))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(UserAIConfig.group_name.like(like) | UserAIConfig.model.like(like))
        count_stmt = count_stmt.where(UserAIConfig.group_name.like(like) | UserAIConfig.model.like(like))
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(UserAIConfig.id.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    items = [AIConfigOut.model_validate(c, from_attributes=True).model_dump(mode="json") for c in rows]
    return success_response(paginate(items, total, page, page_size))


@router.post("")
async def create_config(
    payload: AIConfigCreate, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)
):
    config = UserAIConfig(**payload.model_dump())
    if config.is_default_mode:
        await db.execute(
            UserAIConfig.__table__.update().where(UserAIConfig.is_default_mode.is_(True)).values(is_default_mode=False)
        )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return success_response(AIConfigOut.model_validate(config, from_attributes=True).model_dump(mode="json"))


@router.put("/{config_id}")
async def update_config(
    config_id: int,
    payload: AIConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    config = await db.get(UserAIConfig, config_id)
    if not config:
        return error_response(code=404, message="配置不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default_mode") is True:
        await db.execute(
            UserAIConfig.__table__.update()
            .where(UserAIConfig.is_default_mode.is_(True))
            .where(UserAIConfig.id != config_id)
            .values(is_default_mode=False)
        )
    for k, v in data.items():
        setattr(config, k, v)
    await db.commit()
    await db.refresh(config)
    return success_response(AIConfigOut.model_validate(config, from_attributes=True).model_dump(mode="json"))


@router.delete("/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    config = await db.get(UserAIConfig, config_id)
    if not config:
        return error_response(code=404, message="配置不存在")
    await db.delete(config)
    await db.commit()
    return success_response(message="已删除")
