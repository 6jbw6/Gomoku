"""天梯排行榜与房间管理路由模块。

包含天梯总榜查询与好友对战房间的创建。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from typing import List
from fastapi import APIRouter, Depends
from gomoku.api.deps import get_current_user_optional, get_user_repository
from gomoku.api.schemas import CreateRoomRequest, LeaderboardItem
from gomoku.core.enums import GameMode, RankTier
from gomoku.services.rank_service import RankState
from gomoku.services.room_service import room_manager
from gomoku.storage.models import UserModel
from gomoku.storage.repositories import IUserRepository

router = APIRouter(prefix="/api", tags=["天梯与房间"])


@router.get("/rank/leaderboard", response_model=List[LeaderboardItem], summary="查询全服天梯排行榜")
async def get_leaderboard(
    repo: IUserRepository = Depends(get_user_repository),
) -> List[LeaderboardItem]:
    """获取天梯排名前 50 位的大师级棋手列表。"""
    users = await repo.get_leaderboard(limit=50)
    items: List[LeaderboardItem] = []

    for index, u in enumerate(users, start=1):
        try:
            tier_enum = RankTier(u.tier)
        except ValueError:
            tier_enum = RankTier.BRONZE

        state = RankState(
            tier=tier_enum,
            sub_tier=u.sub_tier,
            stars=u.stars,
            brave_points=u.brave_points,
            winning_streak=u.winning_streak,
            total_matches=u.total_matches,
            win_matches=u.win_matches,
        )

        items.append(
            LeaderboardItem(
                rank=index,
                user_id=u.user_id,
                username=u.username,
                tier=u.tier,
                sub_tier=u.sub_tier,
                stars=u.stars,
                display_rank=state.display_rank,
                total_matches=u.total_matches,
                win_matches=u.win_matches,
                win_rate=state.win_rate,
            )
        )

    return items


@router.post("/room/create", summary="创建好友对战房间")
async def create_friend_room(
    req: CreateRoomRequest,
    current_user: UserModel = Depends(get_current_user_optional),
) -> dict:
    """创建好友对战房间并生成专属邀请码。"""
    room = await room_manager.create_room(
        mode=GameMode.FRIEND,
        turn_timeout=req.turn_timeout,
    )
    return {
        "room_id": room.room_id,
        "mode": room.mode.value,
        "turn_timeout": room.turn_timeout,
    }
