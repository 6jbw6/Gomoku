"""异步数据库引擎与会话管理模块。

使用 SQLAlchemy 2.0 Async 与 aiosqlite 构建轻量高效的嵌入式存储。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from gomoku.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类。"""
    pass


# 创建异步数据库引擎
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """初始化数据库表结构（创建所有已注册的模型表）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入使用的异步数据库会话生成器。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
