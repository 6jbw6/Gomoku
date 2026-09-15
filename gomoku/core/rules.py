"""五子棋规则引擎与胜负判定模块。

遵循 SOLID 原则：
1. 开闭原则（OCP）：定义抽象基类 IRuleEngine，StandardRuleEngine 实现标准五子棋规则。
2. 接口隔离原则（ISP）：分离落子合法性校验与连珠胜负判定。
3. 函数式编程思想：连珠向量扫描均为无副作用的无状态纯函数（Pure Functions）。
所有注释与文档字符串均采用中文。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple
from gomoku.core.board import Board, Move
from gomoku.core.constants import BOARD_SIZE, DIRECTIONS, WIN_COUNT
from gomoku.core.enums import PieceColor, WinReason


@dataclass(frozen=True)
class WinResult:
    """胜负判定结果值对象。

    Attributes:
        is_game_over: 对局是否已分出胜负或终局
        winner: 胜方棋子颜色（平局或未结束时为 EMPTY）
        winning_line: 达成五子连珠的坐标坐标列表 [(x, y), ...]
        reason: 胜负终局原因
    """
    is_game_over: bool
    winner: PieceColor = PieceColor.EMPTY
    winning_line: List[Tuple[int, int]] = field(default_factory=list)
    reason: Optional[WinReason] = None


def count_consecutive(
    grid: Sequence[Sequence[int]],
    x: int,
    y: int,
    dx: int,
    dy: int,
    target_color_val: int,
    board_size: int = BOARD_SIZE,
) -> List[Tuple[int, int]]:
    """在指定方向上扫描与目标颜色相同的连续棋子坐标（纯函数）。

    沿着 (dx, dy) 步进，直至出界或遇到不同颜色棋子即刻停止。

    Args:
        grid: 棋盘二维数值快照
        x: 起始横坐标（不包含此起始点）
        y: 起始纵坐标（不包含此起始点）
        dx: 横向步进向量（-1, 0, 1）
        dy: 纵向步进向量（-1, 0, 1）
        target_color_val: 目标棋子的整型值
        board_size: 棋盘边界大小

    Returns:
        在该方向连续匹配到的坐标列表 [(x1, y1), (x2, y2), ...]
    """
    coords: List[Tuple[int, int]] = []
    curr_x = x + dx
    curr_y = y + dy

    while 0 <= curr_x < board_size and 0 <= curr_y < board_size:
        if grid[curr_y][curr_x] == target_color_val:
            coords.append((curr_x, curr_y))
            curr_x += dx
            curr_y += dy
        else:
            break

    return coords


def evaluate_five_in_a_row(
    grid: Sequence[Sequence[int]],
    last_move: Move,
    win_count: int = WIN_COUNT,
    board_size: int = BOARD_SIZE,
) -> Optional[List[Tuple[int, int]]]:
    """判定最后一步落子是否在其经过的四个方向中达成五子连珠（纯函数）。

    Args:
        grid: 当前棋盘矩阵快照
        last_move: 最后一步落子
        win_count: 达成胜利所需连续子数（默认5）
        board_size: 棋盘规格

    Returns:
        若达成连续五子及以上，返回整条五子连线的所有坐标列表；否则返回 None
    """
    x, y = last_move.x, last_move.y
    target_val = last_move.color.value

    # 遍历四个轴向向量：水平、垂直、主对角线、副对角线
    for dx, dy in DIRECTIONS:
        # 正向探索
        forward_line = count_consecutive(grid, x, y, dx, dy, target_val, board_size)
        # 反向探索
        backward_line = count_consecutive(grid, x, y, -dx, -dy, target_val, board_size)

        # 连续连线总长度 = 正向数量 + 反向数量 + 自身 1 颗
        total_count = len(forward_line) + len(backward_line) + 1

        if total_count >= win_count:
            # 组合按序排列的整条胜利线（从负方向端点到正方向端点）
            full_line: List[Tuple[int, int]] = []
            full_line.extend(reversed(backward_line))
            full_line.append((x, y))
            full_line.extend(forward_line)
            return full_line

    return None


class IRuleEngine(ABC):
    """五子棋规则引擎抽象基类（依赖倒置与开闭原则）。"""

    @abstractmethod
    def validate_move(self, board: Board, x: int, y: int, color: PieceColor) -> Tuple[bool, str]:
        """验证落子是否符合当前规则。

        Args:
            board: 棋盘实例
            x: 横坐标
            y: 纵坐标
            color: 拟落子颜色

        Returns:
            (是否合法, 错误描述原因)
        """
        pass

    @abstractmethod
    def check_game_over(self, board: Board) -> WinResult:
        """检查棋盘当前状态是否达成终局。

        Args:
            board: 棋盘实例

        Returns:
            WinResult 结构体
        """
        pass


class StandardRuleEngine(IRuleEngine):
    """标准自由五子棋规则引擎实现。

    规则说明：无禁手规则，黑白双方任一方形成同色五连即获胜；
    若落满 225 格仍无人五连，则判定为和棋。
    """

    def validate_move(self, board: Board, x: int, y: int, color: PieceColor) -> Tuple[bool, str]:
        """校验落子坐标是否有效。

        Args:
            board: 棋盘实例
            x: 横坐标
            y: 纵坐标
            color: 落子颜色

        Returns:
            (是否合法, 提示文本)
        """
        if not board.is_within_bounds(x, y, board.size):
            return False, f"坐标 ({x}, {y}) 越界，有效范围为 0 到 {board.size - 1}"

        if not board.is_empty(x, y):
            return False, f"坐标 ({x}, {y}) 已经有棋子，不可重复落子"

        # 校验回合执子顺序（先手必须为黑子，后续轮流交替）
        last_move = board.last_move
        if last_move is None:
            if color != PieceColor.BLACK:
                return False, "五子棋对局首手必须由执黑方落子"
        else:
            if color == last_move.color:
                return False, f"不可连续落子，当前轮到 {last_move.color.opponent.display_name} 走棋"

        return True, "落子有效"

    def check_game_over(self, board: Board) -> WinResult:
        """根据最后一步落子判定胜负或和棋。

        Args:
            board: 棋盘实例

        Returns:
            终局判定结果 WinResult
        """
        last_move = board.last_move
        if last_move is None:
            return WinResult(is_game_over=False)

        # 提取快照调用纯函数进行五连扫描
        grid_snapshot = board.get_grid_snapshot()
        winning_line = evaluate_five_in_a_row(
            grid=grid_snapshot,
            last_move=last_move,
            win_count=WIN_COUNT,
            board_size=board.size,
        )

        if winning_line is not None:
            return WinResult(
                is_game_over=True,
                winner=last_move.color,
                winning_line=winning_line,
                reason=WinReason.FIVE_IN_ROW,
            )

        # 检查是否全盘满盘和棋
        if board.is_full():
            return WinResult(
                is_game_over=True,
                winner=PieceColor.EMPTY,
                winning_line=[],
                reason=WinReason.DRAW,
            )

        return WinResult(is_game_over=False)
