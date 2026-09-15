"""WebSocket 实时双向帧同步分发中心。

包含连接会话管理、落子广播、匹配通知与天梯排位实时结算。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from gomoku.api.deps import decode_access_token
from gomoku.core.enums import GameMode, PieceColor, RankTier
from gomoku.services.match_service import matchmaking_service
from gomoku.services.rank_service import RankService, RankState
from gomoku.services.room_service import GameRoom, room_manager
from gomoku.storage.database import AsyncSessionLocal
from gomoku.storage.repositories import UserRepository

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """全局 WebSocket 连接调度池。"""

    def __init__(self) -> None:
        """初始化活跃连接与房间订阅映射。"""
        # user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # room_id -> Set[user_id]
        self.room_subscribers: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """注册并接受全新 WebSocket 接入。"""
        await websocket.accept()
        async with self._lock:
            self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str) -> None:
        """注销断开的客户端连接。"""
        async with self._lock:
            self.active_connections.pop(user_id, None)
            for subscribers in self.room_subscribers.values():
                subscribers.discard(user_id)

    async def subscribe_room(self, room_id: str, user_id: str) -> None:
        """将用户订阅至指定房间。"""
        async with self._lock:
            if room_id not in self.room_subscribers:
                self.room_subscribers[room_id] = set()
            self.room_subscribers[room_id].add(user_id)

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """向指定单一用户推送消息。"""
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                pass

    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any]) -> None:
        """向房间内所有对弈者与观战者广播消息。"""
        subscribers = self.room_subscribers.get(room_id, set())
        text_data = json.dumps(message, ensure_ascii=False)
        for uid in list(subscribers):
            ws = self.active_connections.get(uid)
            if ws:
                try:
                    await ws.send_text(text_data)
                except Exception:
                    pass


# 全局连接管理器单例
ws_manager = ConnectionManager()


async def settle_ranked_game(room: GameRoom) -> None:
    """天梯排位赛对局终局异步结算。"""
    if room.mode != GameMode.RANKED or not room.winner:
        return

    # 提取黑白两方玩家 ID
    black_id = room.black_player.player_id if room.black_player else None
    white_id = room.white_player.player_id if room.white_player else None
    if not black_id or not white_id:
        return

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        black_user = await repo.get_by_user_id(black_id)
        white_user = await repo.get_by_user_id(white_id)

        if not black_user or not white_user:
            return

        is_black_win = room.winner == PieceColor.BLACK
        is_white_win = room.winner == PieceColor.WHITE

        # 结算黑方
        black_state = RankState(
            tier=RankTier(black_user.tier),
            sub_tier=black_user.sub_tier,
            stars=black_user.stars,
            brave_points=black_user.brave_points,
            winning_streak=black_user.winning_streak,
            total_matches=black_user.total_matches,
            win_matches=black_user.win_matches,
        )
        new_black_state, black_settlement = RankService.settle_match(
            current_state=black_state,
            is_win=is_black_win,
            total_moves=room.board.total_moves,
        )
        await repo.update_user_rank(black_id, new_black_state)

        # 结算白方
        white_state = RankState(
            tier=RankTier(white_user.tier),
            sub_tier=white_user.sub_tier,
            stars=white_user.stars,
            brave_points=white_user.brave_points,
            winning_streak=white_user.winning_streak,
            total_matches=white_user.total_matches,
            win_matches=white_user.win_matches,
        )
        new_white_state, white_settlement = RankService.settle_match(
            current_state=white_state,
            is_win=is_white_win,
            total_moves=room.board.total_moves,
        )
        await repo.update_user_rank(white_id, new_white_state)

        # 记录战绩
        await repo.record_match(
            match_id=room.room_id,
            mode=room.mode.value,
            black_user_id=black_id,
            white_user_id=white_id,
            winner_user_id=black_id if is_black_win else white_id,
            total_moves=room.board.total_moves,
            win_reason=room.win_reason.value if room.win_reason else "unknown",
        )
        await session.commit()

        # 分别向双方推送结算数据卡片
        await ws_manager.send_personal_message(
            black_id,
            {
                "action": "rank_settled",
                "payload": {
                    "is_win": black_settlement.is_win,
                    "old_rank": black_settlement.old_rank,
                    "new_rank": black_settlement.new_rank,
                    "stars_delta": black_settlement.stars_delta,
                    "brave_points_gained": black_settlement.brave_points_gained,
                    "current_brave_points": black_settlement.current_brave_points,
                    "protection_triggered": black_settlement.protection_triggered,
                    "bonus_star_triggered": black_settlement.bonus_star_triggered,
                },
            },
        )
        await ws_manager.send_personal_message(
            white_id,
            {
                "action": "rank_settled",
                "payload": {
                    "is_win": white_settlement.is_win,
                    "old_rank": white_settlement.old_rank,
                    "new_rank": white_settlement.new_rank,
                    "stars_delta": white_settlement.stars_delta,
                    "brave_points_gained": white_settlement.brave_points_gained,
                    "current_brave_points": white_settlement.current_brave_points,
                    "protection_triggered": white_settlement.protection_triggered,
                    "bonus_star_triggered": white_settlement.bonus_star_triggered,
                },
            },
        )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None) -> None:
    """WebSocket 核心双向通道长连接。"""
    user_id = f"anonymous_{id(websocket)}"
    username = "神秘棋客"

    # 解析 Token 获取身份
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub", user_id)
            username = payload.get("name", username)

    await ws_manager.connect(user_id, websocket)

    try:
        # 发送建立连接问候响应
        await ws_manager.send_personal_message(
            user_id,
            {
                "action": "connected",
                "payload": {"user_id": user_id, "username": username},
            },
        )

        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            room_id = msg.get("room_id")
            payload = msg.get("payload", {})

            # 1. 心跳 Ping-Pong
            if action == "ping":
                await ws_manager.send_personal_message(user_id, {"action": "pong"})
                continue

            # 2. 加入房间
            if action == "join_room":
                target_room_id = room_id or payload.get("room_id")
                if not target_room_id:
                    await ws_manager.send_personal_message(
                        user_id, {"action": "error", "payload": {"message": "缺少房间号"}}
                    )
                    continue

                room = await room_manager.get_room(target_room_id)
                if not room:
                    # 好友房间不存在则自动创建
                    room = await room_manager.create_room(
                        mode=GameMode.FRIEND,
                        turn_timeout=payload.get("turn_timeout", 30),
                        room_id=target_room_id,
                    )

                rank_display = payload.get("rank_display", "倔强青铜 III")
                pref = payload.get("preferred_color", 0)
                pref_color = PieceColor(pref) if pref in (1, 2) else None

                ok, join_msg, assigned_color = room.add_player(
                    player_id=user_id,
                    username=username,
                    rank_display=rank_display,
                    preferred_color=pref_color,
                )

                await ws_manager.subscribe_room(room.room_id, user_id)
                await ws_manager.broadcast_to_room(
                    room.room_id,
                    {
                        "action": "room_state",
                        "payload": room.to_dict(),
                    },
                )
                continue

            # 3. 准备就绪
            if action == "ready":
                if not room_id:
                    continue
                room = await room_manager.get_room(room_id)
                if room:
                    room.set_player_ready(user_id, True)
                    await ws_manager.broadcast_to_room(
                        room.room_id,
                        {
                            "action": "room_state",
                            "payload": room.to_dict(),
                        },
                    )
                continue

            # 4. 落子动作
            if action == "move":
                if not room_id:
                    continue
                room = await room_manager.get_room(room_id)
                if not room:
                    continue

                x = payload.get("x")
                y = payload.get("y")
                if x is None or y is None:
                    continue

                success, move_msg, win_result = room.make_move(user_id, int(x), int(y))
                if not success:
                    await ws_manager.send_personal_message(
                        user_id,
                        {"action": "error", "payload": {"message": move_msg}},
                    )
                    continue

                # 广播最新棋盘状态
                await ws_manager.broadcast_to_room(
                    room.room_id,
                    {
                        "action": "room_state",
                        "payload": room.to_dict(),
                    },
                )

                if win_result and win_result.is_game_over:
                    # 广播胜负终局
                    await ws_manager.broadcast_to_room(
                        room.room_id,
                        {
                            "action": "game_over",
                            "payload": {
                                "winner": room.winner.value if room.winner else 0,
                                "win_reason": room.win_reason.value if room.win_reason else None,
                                "winning_line": room.winning_line,
                            },
                        },
                    )
                    # 触发排位天梯结算
                    await settle_ranked_game(room)
                continue

            # 5. 玩家主动认输
            if action == "resign":
                if not room_id:
                    continue
                room = await room_manager.get_room(room_id)
                if room:
                    ok, r_msg = room.resign(user_id)
                    if ok:
                        # 先行广播终局后的最新房间状态（status 为 finished）
                        await ws_manager.broadcast_to_room(
                            room.room_id,
                            {
                                "action": "room_state",
                                "payload": room.to_dict(),
                            },
                        )
                        await ws_manager.broadcast_to_room(
                            room.room_id,
                            {
                                "action": "game_over",
                                "payload": {
                                    "winner": room.winner.value if room.winner else 0,
                                    "win_reason": (
                                        room.win_reason.value if room.win_reason else None
                                    ),
                                    "winning_line": [],
                                },
                            },
                        )
                        await settle_ranked_game(room)
                continue

            # 6. 单人或排位天梯在线匹配
            if action == "match_queue":
                mode_str = payload.get("mode", "casual")
                mode = GameMode.RANKED if mode_str == "ranked" else GameMode.CASUAL
                tier_str = payload.get("tier", "倔强青铜")
                stars = payload.get("stars", 0)
                try:
                    tier = RankTier(tier_str)
                except ValueError:
                    tier = RankTier.BRONZE

                await ws_manager.send_personal_message(
                    user_id,
                    {
                        "action": "match_status",
                        "payload": {"status": "searching", "mode": mode.value},
                    },
                )

                # 提交异步匹配
                async def _wait_match():
                    try:
                        matched_room: GameRoom = await matchmaking_service.enqueue(
                            player_id=user_id,
                            username=username,
                            mode=mode,
                            tier=tier,
                            stars=stars,
                        )
                        # 匹配成功，自动关联订阅
                        await ws_manager.subscribe_room(matched_room.room_id, user_id)
                        await ws_manager.send_personal_message(
                            user_id,
                            {
                                "action": "match_success",
                                "payload": {
                                    "room_id": matched_room.room_id,
                                    "room_state": matched_room.to_dict(),
                                },
                            },
                        )
                    except asyncio.CancelledError:
                        pass
                    except Exception as err:
                        logger.exception("匹配处理异常: %s", err)

                asyncio.create_task(_wait_match())
                continue

            # 7. 取消匹配
            if action == "match_cancel":
                await matchmaking_service.cancel(user_id)
                await ws_manager.send_personal_message(
                    user_id,
                    {"action": "match_status", "payload": {"status": "cancelled"}},
                )
                continue

            # 8. 房间内文字互动聊天
            if action == "chat":
                if not room_id:
                    continue
                content = payload.get("content", "").strip()
                if content:
                    await ws_manager.broadcast_to_room(
                        room_id,
                        {
                            "action": "chat_message",
                            "payload": {
                                "sender_id": user_id,
                                "sender_name": username,
                                "content": content[:100],  # 限长 100 字
                            },
                        },
                    )
                continue

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
        await matchmaking_service.cancel(user_id)
    except Exception as exc:
        logger.exception("WebSocket 处理异常: %s", exc)
        await ws_manager.disconnect(user_id)
