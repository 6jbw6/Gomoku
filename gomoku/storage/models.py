"""数据库实体 ORM 模型定义模块。

使用 SQLAlchemy 2.0 现代声明式语法（Mapped / mapped_column）。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from gomoku.core.enums import RankTier
from gomoku.storage.database import Base


def get_utc_now() -> datetime:
    """获取当前 UTC 时间戳纯函数。"""
    return datetime.now(timezone.utc)


class UserModel(Base):
    """用户账户与天梯段位数据模型。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 天梯段位数据
    tier: Mapped[str] = mapped_column(String(32), default=RankTier.BRONZE.value, nullable=False)
    sub_tier: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brave_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    winning_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False
    )


class MatchRecordModel(Base):
    """历史对局记录数据模型。"""

    __tablename__ = "match_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # friend, casual, ranked
    black_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    white_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    winner_user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    total_moves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_reason: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)
