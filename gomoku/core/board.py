"""五子棋棋盘与落子领域模型模块。

遵循 SOLID 原则中的单一职责原则（SRP）：
Board 类专注于维护 15x15 棋盘矩阵状态、落子历史与坐标边界校验。
所有注释与文档字符串均采用中文。
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence
from gomoku.core.constants import BOARD_SIZE
from gomoku.core.enums import PieceColor


@dataclass(frozen=True)
class Move:
    """落子动作不可变值对象。

    Attributes:
        x: 横坐标（0 到 BOARD_SIZE - 1）
        y: 纵坐标（0 到 BOARD_SIZE - 1）
        color: 所落棋子颜色（BLACK 或 WHITE）
        step_index: 第几手（从 1 开始累加）
    """
    x: int
    y: int
    color: PieceColor
    step_index: int


class Board:
    """五子棋棋盘模型。

    维护二维网格状态、已落棋子历史，提供快速坐标查询与克隆。
    """

    def __init__(self, size: int = BOARD_SIZE) -> None:
        """初始化指定尺寸的空棋盘。

        Args:
            size: 棋盘单边交点数，默认标准 15
        """
        self.size: int = size
        # 初始化 15x15 二维矩阵，0 代表空
        self._grid: List[List[int]] = [
            [PieceColor.EMPTY.value for _ in range(self.size)]
            for _ in range(self.size)
        ]
        # 记录每一步落子的历史流水，便于悔棋、复盘与最后手光晕高亮
        self._history: List[Move] = []

    @classmethod
    def is_within_bounds(cls, x: int, y: int, size: int = BOARD_SIZE) -> bool:
        """检查坐标是否在棋盘合法边界内（纯函数）。

        Args:
            x: 横坐标
            y: 纵坐标
            size: 棋盘尺寸

        Returns:
            若在 [0, size-1] 范围内返回 True，否则返回 False
        """
        return 0 <= x < size and 0 <= y < size

    def get_piece(self, x: int, y: int) -> PieceColor:
        """获取指定坐标处的棋子颜色。

        Args:
            x: 横坐标
            y: 纵坐标

        Returns:
            PieceColor 枚举值
        """
        if not self.is_within_bounds(x, y, self.size):
            return PieceColor.EMPTY
        return PieceColor(self._grid[y][x])

    def is_empty(self, x: int, y: int) -> bool:
        """判断指定坐标是否为空位。

        Args:
            x: 横坐标
            y: 纵坐标

        Returns:
            若在棋盘内且尚未落子返回 True，否则返回 False
        """
        return self.is_within_bounds(x, y, self.size) and self._grid[y][x] == PieceColor.EMPTY.value

    def place_piece(self, x: int, y: int, color: PieceColor) -> Move:
        """在棋盘指定坐标落子。

        Args:
            x: 横坐标
            y: 纵坐标
            color: 落子颜色

        Returns:
            生成的 Move 落子对象

        Raises:
            ValueError: 坐标越界、非空位置落子或非法棋子颜色时抛出
        """
        if not self.is_within_bounds(x, y, self.size):
            raise ValueError(f"落子坐标越界: ({x}, {y})，棋盘规格为 {self.size}x{self.size}")
        if self._grid[y][x] != PieceColor.EMPTY.value:
            raise ValueError(f"坐标 ({x}, {y}) 已有棋子，不可重复落子")
        if color not in (PieceColor.BLACK, PieceColor.WHITE):
            raise ValueError(f"非法落子颜色: {color}")

        step_index = len(self._history) + 1
        move = Move(x=x, y=y, color=color, step_index=step_index)
        self._grid[y][x] = color.value
        self._history.append(move)
        return move

    def undo_last_move(self) -> Optional[Move]:
        """撤销最后一步落子（悔棋功能支撑）。

        Returns:
            被撤销的 Move 对象；若无棋子可撤销返回 None
        """
        if not self._history:
            return None
        last_move = self._history.pop()
        self._grid[last_move.y][last_move.x] = PieceColor.EMPTY.value
        return last_move

    @property
    def last_move(self) -> Optional[Move]:
        """获取最后一步落子信息。"""
        return self._history[-1] if self._history else None

    @property
    def history(self) -> Sequence[Move]:
        """获取落子历史记录（只读序列）。"""
        return tuple(self._history)

    @property
    def total_moves(self) -> int:
        """当前已落子总手数。"""
        return len(self._history)

    def is_full(self) -> bool:
        """检查棋盘是否已填满（用于判定和棋）。"""
        return self.total_moves >= self.size * self.size

    def get_grid_snapshot(self) -> List[List[int]]:
        """获取当前棋盘矩阵的深拷贝快照（防止外部意外篡改内部状态）。

        Returns:
            15x15 的二维整型列表
        """
        return [row[:] for row in self._grid]

    def clear(self) -> None:
        """重置棋盘为空状态。"""
        self._grid = [
            [PieceColor.EMPTY.value for _ in range(self.size)]
            for _ in range(self.size)
        ]
        self._history.clear()

    def clone(self) -> "Board":
        """深度克隆当前棋盘实例（常用于 AI 模拟搜索与前瞻预判）。

        Returns:
            全新的 Board 独立克隆副本
        """
        new_board = Board(size=self.size)
        new_board._grid = [row[:] for row in self._grid]
        new_board._history = list(self._history)
        return new_board
