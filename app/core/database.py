from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from core.config import settings


class Base(DeclarativeBase):
    pass


def normalize_asyncpg_connection(raw_url: str) -> tuple[str, dict[str, str]]:
    url = make_url(raw_url)
    query = dict(url.query)
    connect_args: dict[str, str] = {}
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode:
        connect_args["ssl"] = sslmode
    normalized_url = url.set(query=query).render_as_string(hide_password=False)
    return normalized_url, connect_args


normalized_database_url, connect_args = normalize_asyncpg_connection(settings.database_url)
engine = create_async_engine(
    normalized_database_url,
    connect_args=connect_args,
    echo=settings.debug,
    future=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
