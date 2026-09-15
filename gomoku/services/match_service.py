"""匹配队列调度服务模块。

包含休闲单人快速匹配池、排位天梯段位加权匹配池与队列配对调度机制。
遵循 SOLID 原则中的单一职责与依赖倒置原则。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
from gomoku.config import settings
from gomoku.core.enums import GameMode, PieceColor, RankTier
from gomoku.services.room_service import GameRoom, room_manager


@dataclass
class MatchTicket:
    """匹配申请票据。

    Attributes:
        player_id: 玩家唯一标识
        username: 玩家昵称
        mode: 申请匹配的模式（CASUAL 或 RANKED）
        tier: 当前天梯段位
        stars: 当前段位星数
        joined_time: 进入匹配队列的单调时间戳
        future: 用于异步通知匹配结果的 asyncio.Future
    """
    player_id: str
    username: str
    mode: GameMode
    tier: RankTier = RankTier.BRONZE
    stars: int = 0
    joined_time: float = 0.0
    future: Optional[asyncio.Future] = None


class MatchmakingService:
    """匹配调度服务。"""

    def __init__(self) -> None:
        """初始化匹配池与锁。"""
        self._casual_queue: List[MatchTicket] = []
        self._ranked_queue: List[MatchTicket] = []
        self._lock: asyncio.Lock = asyncio.Lock()
        self._running: bool = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动后台周期性匹配调度工作协程。"""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._match_loop())

    async def stop(self) -> None:
        """停止匹配服务。"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue(
        self,
        player_id: str,
        username: str,
        mode: GameMode,
        tier: RankTier = RankTier.BRONZE,
        stars: int = 0,
    ) -> GameRoom:
        """玩家提交匹配申请并进入对应匹配池。

        Returns:
            分配的 GameRoom 实体
        """
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()

        ticket = MatchTicket(
            player_id=player_id,
            username=username,
            mode=mode,
            tier=tier,
            stars=stars,
            joined_time=time.time(),
            future=fut,
        )

        async with self._lock:
            # 清理该玩家可能遗留在其他队列的历史票据
            self._remove_player_locked(player_id)

            if mode == GameMode.CASUAL:
                self._casual_queue.append(ticket)
            elif mode == GameMode.RANKED:
                self._ranked_queue.append(ticket)

        return await fut

    async def cancel(self, player_id: str) -> bool:
        """玩家取消匹配队列。"""
        async with self._lock:
            return self._remove_player_locked(player_id)

    def _remove_player_locked(self, player_id: str) -> bool:
        """内部在锁保护下移除玩家票据。"""
        removed = False
        for q in (self._casual_queue, self._ranked_queue):
            for t in list(q):
                if t.player_id == player_id:
                    q.remove(t)
                    removed = True
                    if t.future and not t.future.done():
                        t.future.cancel()
        return removed

    async def _match_loop(self) -> None:
        """后台轮询工作协程：每隔 500 毫秒扫描一次队列进行配对。"""
        while self._running:
            try:
                await self._process_casual_queue()
                await self._process_ranked_queue()
            except Exception:
                # 捕获异常防止调度线程意外崩溃
                pass
            await asyncio.sleep(0.5)

    async def _process_casual_queue(self) -> None:
        """处理单人休闲匹配池。"""
        async with self._lock:
            # 在真人玩家之间进行两两配对
            while len(self._casual_queue) >= 2:
                p1 = self._casual_queue.pop(0)
                p2 = self._casual_queue.pop(0)
                await self._create_match_for_pair(p1, p2, GameMode.CASUAL)

    async def _process_ranked_queue(self) -> None:
        """处理天梯排位赛匹配池。"""
        async with self._lock:
            # 两两寻找实力相近的对手
            matched_pairs: List[Tuple[MatchTicket, MatchTicket]] = []
            matched_indices = set()

            for i in range(len(self._ranked_queue)):
                if i in matched_indices:
                    continue
                t1 = self._ranked_queue[i]
                for j in range(i + 1, len(self._ranked_queue)):
                    if j in matched_indices:
                        continue
                    t2 = self._ranked_queue[j]
                    # 段位相差不超过 1 个大段即可成局
                    matched_pairs.append((t1, t2))
                    matched_indices.add(i)
                    matched_indices.add(j)
                    break

            # 移除已配对成功的票据并生成房间
            for t1, t2 in matched_pairs:
                if t1 in self._ranked_queue:
                    self._ranked_queue.remove(t1)
                if t2 in self._ranked_queue:
                    self._ranked_queue.remove(t2)
                await self._create_match_for_pair(t1, t2, GameMode.RANKED)

    async def _create_match_for_pair(
        self,
        t1: MatchTicket,
        t2: MatchTicket,
        mode: GameMode,
    ) -> None:
        """为两位真人玩家创建匹配房间并自动开局。"""
        room = await room_manager.create_room(
            mode=mode,
            turn_timeout=settings.TURN_TIMEOUT_SECONDS_DEFAULT,
        )
        # 随机分配黑白先后手
        import random
        r1_rank = f"{t1.tier.value} {t1.stars}星"
        r2_rank = f"{t2.tier.value} {t2.stars}星"

        if random.random() < 0.5:
            room.add_player(t1.player_id, t1.username, r1_rank, preferred_color=PieceColor.BLACK)
            room.add_player(t2.player_id, t2.username, r2_rank, preferred_color=PieceColor.WHITE)
        else:
            room.add_player(t2.player_id, t2.username, r2_rank, preferred_color=PieceColor.BLACK)
            room.add_player(t1.player_id, t1.username, r1_rank, preferred_color=PieceColor.WHITE)

        room.set_player_ready(t1.player_id, True)
        room.set_player_ready(t2.player_id, True)

        # 通知两方 Future 完成
        if t1.future and not t1.future.done():
            t1.future.set_result(room)
        if t2.future and not t2.future.done():
            t2.future.set_result(room)


# 全局匹配调度服务单例
matchmaking_service = MatchmakingService()
