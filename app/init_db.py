"""数据库初始化脚本：建表并创建默认管理员账号。

运行方式：
    cd learn-service
    python -m app.init_db
"""

import asyncio

from sqlalchemy import select

from core.auth import hash_password
from core.config import settings
from core.database import Base, SessionLocal, engine
from models.ai_config import UserAIConfig
from models.article import Article
from models.article_book import ArticleBook
from models.user import User
from models.word_book import WordBook
from models.word_entry import WordEntry


async def init_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_admin() -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("管理员账号已存在，跳过创建")
            return
        admin = User(
            username="admin",
            nick_name="管理员",
            role="admin",
            password_hash=hash_password("admin123"),
        )
        session.add(admin)
        await session.commit()
        print("已创建默认管理员账号: admin / admin123")


async def ensure_default_ai_config() -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(UserAIConfig).where(UserAIConfig.is_default_mode.is_(True)))
        if result.scalar_one_or_none():
            return
        config = UserAIConfig(
            group="deepseek",
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            is_default_mode=True,
        )
        session.add(config)
        await session.commit()
        print("已创建默认 AI 配置: deepseek")


async def main() -> None:
    print(f"连接数据库: {settings.database_url}")
    await init_schema()
    print("数据表已就绪")
    await ensure_admin()
    await ensure_default_ai_config()
    print("初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
