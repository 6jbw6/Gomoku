"""数据访问仓储模块（Repository Pattern）。

遵循依赖倒置原则（DIP）：定义 IUserRepository 抽象接口，UserRepository 提供具体持久化实现。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from abc import ABC, abstractmethod
from typing import Optional, Sequence
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from gomoku.core.enums import RankTier
from gomoku.services.rank_service import RankState
from gomoku.storage.models import MatchRecordModel, UserModel


class IUserRepository(ABC):
    """用户与排位仓储抽象接口。"""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[UserModel]:
        """根据系统唯一标识 user_id 查询用户。"""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """根据用户名查询用户。"""
        pass

    @abstractmethod
    async def create_guest_user(self, nickname: Optional[str] = None) -> UserModel:
        """创建免密游客用户。"""
        pass

    @abstractmethod
    async def create_user(self, username: str, hashed_password: str) -> UserModel:
        """注册正式账户。"""
        pass

    @abstractmethod
    async def update_user_rank(self, user_id: str, new_state: RankState) -> Optional[UserModel]:
        """更新玩家天梯排位状态。"""
        pass

    @abstractmethod
    async def get_leaderboard(self, limit: int = 50) -> Sequence[UserModel]:
        """获取全服天梯排行榜。"""
        pass

    @abstractmethod
    async def record_match(
        self,
        match_id: str,
        mode: str,
        black_user_id: str,
        white_user_id: str,
        winner_user_id: Optional[str],
        total_moves: int,
        win_reason: str,
    ) -> MatchRecordModel:
        """记录完赛历史战绩。"""
        pass


class UserRepository(IUserRepository):
    """基于 SQLAlchemy Async 的用户与战绩数据访问仓储实现。"""

    def __init__(self, session: AsyncSession) -> None:
        """注入异步数据库会话。"""
        self._session: AsyncSession = session

    async def get_by_user_id(self, user_id: str) -> Optional[UserModel]:
        """根据用户ID查询。"""
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """根据用户名查询。"""
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_guest_user(self, nickname: Optional[str] = None) -> UserModel:
        """创建免密游客用户（支持重名智能防护与账号复用）。"""
        if nickname:
            existing = await self.get_by_username(nickname)
            if existing and existing.is_guest:
                return existing
            elif existing:
                name = f"{nickname}_{uuid.uuid4().hex[:4]}"
            else:
                name = nickname
        else:
            name = f"棋客_{uuid.uuid4().hex[:4]}"

        uid = f"guest_{uuid.uuid4().hex[:8]}"
        user = UserModel(
            user_id=uid,
            username=name,
            hashed_password=None,
            is_guest=True,
            tier=RankTier.BRONZE.value,
            sub_tier=3,
            stars=0,
            brave_points=0,
            winning_streak=0,
            total_matches=0,
            win_matches=0,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def create_user(self, username: str, hashed_password: str) -> UserModel:
        """注册正式账户。"""
        uid = f"user_{uuid.uuid4().hex[:10]}"
        user = UserModel(
            user_id=uid,
            username=username,
            hashed_password=hashed_password,
            is_guest=False,
            tier=RankTier.BRONZE.value,
            sub_tier=3,
            stars=0,
            brave_points=0,
            winning_streak=0,
            total_matches=0,
            win_matches=0,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_user_rank(self, user_id: str, new_state: RankState) -> Optional[UserModel]:
        """同步更新天梯段位数据。"""
        user = await self.get_by_user_id(user_id)
        if not user:
            return None

        user.tier = new_state.tier.value
        user.sub_tier = new_state.sub_tier
        user.stars = new_state.stars
        user.brave_points = new_state.brave_points
        user.winning_streak = new_state.winning_streak
        user.total_matches = new_state.total_matches
        user.win_matches = new_state.win_matches

        await self._session.flush()
        return user

    async def get_leaderboard(self, limit: int = 50) -> Sequence[UserModel]:
        """按总胜场与段位排序获取天梯排行榜。"""
        stmt = (
            select(UserModel)
            .order_by(
                desc(UserModel.total_matches),
                desc(UserModel.win_matches),
                desc(UserModel.stars),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def record_match(
        self,
        match_id: str,
        mode: str,
        black_user_id: str,
        white_user_id: str,
        winner_user_id: Optional[str],
        total_moves: int,
        win_reason: str,
    ) -> MatchRecordModel:
        """记录完赛历史。"""
        record = MatchRecordModel(
            match_id=match_id,
            mode=mode,
            black_user_id=black_user_id,
            white_user_id=white_user_id,
            winner_user_id=winner_user_id,
            total_moves=total_moves,
            win_reason=win_reason,
        )
        self._session.add(record)
        await self._session.flush()
        return record
