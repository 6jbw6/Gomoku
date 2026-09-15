"""对局房间与生命周期管理服务模块。

包含房间创建、玩家进出、准备状态机、执子分配、落子调度、超时控制、认输与和棋协商。
遵循 SOLID 原则：
- 单一职责：GameRoom 仅负责单个房间局内状态同步；RoomManager 负责多房间的池化调度。
- 开闭原则：规则引擎与机器人玩家多态注入。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from gomoku.core.board import Board
from gomoku.core.enums import GameMode, GameStatus, PieceColor, WinReason
from gomoku.core.rules import IRuleEngine, StandardRuleEngine, WinResult


@dataclass
class PlayerSession:
    """局内玩家会话信息。

    Attributes:
        player_id: 用户唯一标识
        username: 用户昵称
        color: 分配的棋子颜色（EMPTY 表示观战或尚未分配）
        is_ready: 是否已准备就绪
        rank_display: 当前段位名称
    """
    player_id: str
    username: str
    color: PieceColor = PieceColor.EMPTY
    is_ready: bool = False
    rank_display: str = "倔强青铜 III"


class GameRoom:
    """对弈房间实体。

    维护当局棋盘、双方玩家信息、局内倒计时及胜负判定。
    """

    def __init__(
        self,
        room_id: str,
        mode: GameMode,
        turn_timeout: int = 30,
        rule_engine: Optional[IRuleEngine] = None,
    ) -> None:
        """初始化游戏房间。

        Args:
            room_id: 唯一房间编号（6 位字母数字码或标识串）
            mode: 游戏模式（好友/休闲/排位）
            turn_timeout: 每步棋落子超时时间（秒，0表示不限时）
            rule_engine: 规则引擎实例，默认 StandardRuleEngine
        """
        self.room_id: str = room_id
        self.mode: GameMode = mode
        self.turn_timeout: int = turn_timeout
        self.rule_engine: IRuleEngine = rule_engine or StandardRuleEngine()

        self.board: Board = Board()
        self.status: GameStatus = GameStatus.WAITING
        self.current_turn: PieceColor = PieceColor.BLACK

        # 玩家会话槽位
        self.black_player: Optional[PlayerSession] = None
        self.white_player: Optional[PlayerSession] = None
        self.spectators: List[PlayerSession] = []

        # 时间与交互控制
        self.turn_start_time: float = 0.0
        self.winner: Optional[PieceColor] = None
        self.win_reason: Optional[WinReason] = None
        self.winning_line: List[Tuple[int, int]] = []

        # 局内协商标志
        self.draw_offered_by: Optional[PieceColor] = None
        self.undo_requested_by: Optional[PieceColor] = None

    def add_player(
        self,
        player_id: str,
        username: str,
        rank_display: str = "倔强青铜 III",
        preferred_color: Optional[PieceColor] = None,
    ) -> Tuple[bool, str, Optional[PieceColor]]:
        """玩家进入房间加入对局或观战。

        Returns:
            (是否成功, 提示消息, 玩家最终分配的 PieceColor)
        """
        # 已在对局中的玩家重连
        if self.black_player and self.black_player.player_id == player_id:
            return True, "已重新连接进入黑方槽位", PieceColor.BLACK
        if self.white_player and self.white_player.player_id == player_id:
            return True, "已重新连接进入白方槽位", PieceColor.WHITE

        # 游戏未开始时优先入座
        if self.status == GameStatus.WAITING:
            if preferred_color == PieceColor.BLACK:
                if self.black_player is None:
                    self.black_player = PlayerSession(
                        player_id, username, PieceColor.BLACK, False, rank_display
                    )
                    return True, "成功加入并执黑", PieceColor.BLACK
                elif self.white_player is None:
                    self.white_player = PlayerSession(
                        player_id, username, PieceColor.WHITE, False, rank_display
                    )
                    return True, "黑方已有人，自动分配执白", PieceColor.WHITE
            elif preferred_color == PieceColor.WHITE:
                if self.white_player is None:
                    self.white_player = PlayerSession(
                        player_id, username, PieceColor.WHITE, False, rank_display
                    )
                    return True, "成功加入并执白", PieceColor.WHITE
                elif self.black_player is None:
                    self.black_player = PlayerSession(
                        player_id, username, PieceColor.BLACK, False, rank_display
                    )
                    return True, "白方已有人，自动分配执黑", PieceColor.BLACK
            else:
                # 随机或顺延入座
                if self.black_player is None:
                    self.black_player = PlayerSession(
                        player_id, username, PieceColor.BLACK, False, rank_display
                    )
                    return True, "成功加入并执黑", PieceColor.BLACK
                elif self.white_player is None:
                    self.white_player = PlayerSession(
                        player_id, username, PieceColor.WHITE, False, rank_display
                    )
                    return True, "成功加入并执白", PieceColor.WHITE

        # 双方已满或正在对局，作为观战者加入
        spec_session = PlayerSession(
            player_id, username, PieceColor.EMPTY, False, rank_display
        )
        self.spectators.append(spec_session)
        return True, "房间玩家已满，作为观战者进入", PieceColor.EMPTY

    def remove_player(self, player_id: str) -> Optional[PieceColor]:
        """移除离开房间的玩家。若在对局中离线，记录其原执子颜色。"""
        if self.black_player and self.black_player.player_id == player_id:
            color = PieceColor.BLACK
            if self.status == GameStatus.WAITING:
                self.black_player = None
            return color

        if self.white_player and self.white_player.player_id == player_id:
            color = PieceColor.WHITE
            if self.status == GameStatus.WAITING:
                self.white_player = None
            return color

        self.spectators = [s for s in self.spectators if s.player_id != player_id]
        return None

    def set_player_ready(self, player_id: str, ready: bool = True) -> bool:
        """切换玩家准备状态，若双方皆准备则自动开局。"""
        if self.status != GameStatus.WAITING:
            return False

        if self.black_player and self.black_player.player_id == player_id:
            self.black_player.is_ready = ready
        elif self.white_player and self.white_player.player_id == player_id:
            self.white_player.is_ready = ready
        else:
            return False

        # 如果双方均已就绪，自动开启对局
        if (
            self.black_player
            and self.white_player
            and self.black_player.is_ready
            and self.white_player.is_ready
        ):
            self.start_game()

        return True

    def start_game(self) -> None:
        """正式开启对弈。"""
        self.board.clear()
        self.status = GameStatus.PLAYING
        self.current_turn = PieceColor.BLACK
        self.turn_start_time = time.time()
        self.winner = None
        self.win_reason = None
        self.winning_line = []
        self.draw_offered_by = None
        self.undo_requested_by = None

    def make_move(self, player_id: str, x: int, y: int) -> Tuple[bool, str, Optional[WinResult]]:
        """执行落子动作。

        Returns:
            (是否成功落子, 提示消息, 终局判定 WinResult)
        """
        if self.status != GameStatus.PLAYING:
            return False, "对局尚未开始或已结束", None

        # 判定玩家执子身份
        player_color = self.get_player_color(player_id)
        if player_color == PieceColor.EMPTY:
            return False, "观战者不能落子", None

        if player_color != self.current_turn:
            return False, f"未到您的出子回合，当前轮到 {self.current_turn.display_name}", None

        # 规则引擎校验
        valid, msg = self.rule_engine.validate_move(self.board, x, y, player_color)
        if not valid:
            return False, msg, None

        # 棋盘落子
        self.board.place_piece(x, y, player_color)

        # 终局胜负检测
        win_result = self.rule_engine.check_game_over(self.board)
        if win_result.is_game_over:
            self.status = GameStatus.FINISHED
            self.winner = win_result.winner
            self.win_reason = win_result.reason
            self.winning_line = win_result.winning_line
        else:
            # 轮换回合与刷新步时
            self.current_turn = self.current_turn.opponent
            self.turn_start_time = time.time()

        return True, "落子成功", win_result

    def resign(self, player_id: str) -> Tuple[bool, str]:
        """玩家主动认输。"""
        if self.status != GameStatus.PLAYING:
            return False, "对局未处于进行中"

        player_color = self.get_player_color(player_id)
        if player_color not in (PieceColor.BLACK, PieceColor.WHITE):
            return False, "非对弈选手无法认输"

        self.status = GameStatus.FINISHED
        self.winner = player_color.opponent
        self.win_reason = WinReason.RESIGN
        return True, f"{player_color.display_name} 认输，{self.winner.display_name} 获胜！"

    def handle_timeout(self) -> Tuple[bool, str]:
        """处理超时判负。"""
        if self.status != GameStatus.PLAYING or self.turn_timeout <= 0:
            return False, "未超时或无步时限制"

        elapsed = time.time() - self.turn_start_time
        if elapsed >= self.turn_timeout:
            self.status = GameStatus.FINISHED
            self.winner = self.current_turn.opponent
            self.win_reason = WinReason.TIMEOUT
            return True, f"{self.current_turn.display_name} 步时耗尽超时判负！"

        return False, "尚未超时"

    def get_player_color(self, player_id: str) -> PieceColor:
        """根据玩家 ID 获取其执子颜色。"""
        if self.black_player and self.black_player.player_id == player_id:
            return PieceColor.BLACK
        if self.white_player and self.white_player.player_id == player_id:
            return PieceColor.WHITE
        return PieceColor.EMPTY

    def get_remaining_seconds(self) -> int:
        """计算当前回合剩余秒数。"""
        if self.turn_timeout <= 0 or self.status != GameStatus.PLAYING:
            return 0
        elapsed = time.time() - self.turn_start_time
        return max(0, int(self.turn_timeout - elapsed))

    def to_dict(self) -> Dict[str, Any]:
        """将当前房间全量对局状态序列化为 JSON 字典。"""
        last = self.board.last_move
        return {
            "room_id": self.room_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "turn_timeout": self.turn_timeout,
            "remaining_seconds": self.get_remaining_seconds(),
            "current_turn": self.current_turn.value,
            "total_moves": self.board.total_moves,
            "last_move": {"x": last.x, "y": last.y, "color": last.color.value} if last else None,
            "winner": self.winner.value if self.winner else 0,
            "win_reason": self.win_reason.value if self.win_reason else None,
            "winning_line": self.winning_line,
            "black_player": {
                "player_id": self.black_player.player_id,
                "username": self.black_player.username,
                "is_ready": self.black_player.is_ready,
                "rank_display": self.black_player.rank_display,
            } if self.black_player else None,
            "white_player": {
                "player_id": self.white_player.player_id,
                "username": self.white_player.username,
                "is_ready": self.white_player.is_ready,
                "rank_display": self.white_player.rank_display,
            } if self.white_player else None,
            "spectator_count": len(self.spectators),
            "board": self.board.get_grid_snapshot(),
        }


class RoomManager:
    """全局房间调度管理器（单例容器模式）。"""

    def __init__(self) -> None:
        """初始化房间集合与异步锁。"""
        self._rooms: Dict[str, GameRoom] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    def generate_room_code(self, length: int = 6) -> str:
        """生成 6 位不含易混淆字符的数字字母房间短码。"""
        # 排除 0, O, 1, I 等易混淆字符
        charset = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        while True:
            code = "".join(random.choices(charset, k=length))
            if code not in self._rooms:
                return code

    async def create_room(
        self,
        mode: GameMode,
        turn_timeout: int = 30,
        room_id: Optional[str] = None,
    ) -> GameRoom:
        """创建全新房间并加入全局注册表。"""
        async with self._lock:
            code = room_id or self.generate_room_code()
            room = GameRoom(room_id=code, mode=mode, turn_timeout=turn_timeout)
            self._rooms[code] = room
            return room

    async def get_room(self, room_id: str) -> Optional[GameRoom]:
        """获取指定 ID 的房间。"""
        async with self._lock:
            return self._rooms.get(room_id)

    async def find_room_by_player(self, player_id: str) -> Optional[GameRoom]:
        """查找指定玩家所在的活跃房间。"""
        async with self._lock:
            for room in self._rooms.values():
                if (room.black_player and room.black_player.player_id == player_id) or (
                    room.white_player and room.white_player.player_id == player_id
                ):
                    return room
            return None

    async def remove_room(self, room_id: str) -> None:
        """解散并注销指定房间。"""
        async with self._lock:
            self._rooms.pop(room_id, None)

    async def get_active_room_count(self) -> int:
        """获取当前正在进行的对局房间总数。"""
        async with self._lock:
            return len(self._rooms)


# 全局房间管理器单例
room_manager = RoomManager()
