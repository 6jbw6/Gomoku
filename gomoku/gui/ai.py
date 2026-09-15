"""五子棋单机与人机切磋启发式评估引擎。

采用经典格局启发式评分（连五、活四、冲四、活三、眠三、活二），提供灵动的对弈体验。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import random
from typing import List, Tuple
from gomoku.core.board import Board
from gomoku.core.constants import BOARD_SIZE, DIRECTIONS
from gomoku.core.enums import PieceColor

# 棋型分值常量
SCORE_FIVE: int = 1000000       # 连五必胜
SCORE_FOUR_OPEN: int = 50000    # 活四
SCORE_FOUR_BLOCKED: int = 8000  # 冲四
SCORE_THREE_OPEN: int = 5000    # 活三
SCORE_THREE_BLOCKED: int = 800  # 眠三
SCORE_TWO_OPEN: int = 300       # 活二
SCORE_TWO_BLOCKED: int = 50     # 眠二


class GomokuAI:
    """启发式五子棋评估引擎。"""

    def __init__(self, ai_color: PieceColor = PieceColor.WHITE) -> None:
        """初始化 AI 执子色彩。"""
        self.ai_color = ai_color
        self.opponent_color = ai_color.opponent

    def select_best_move(self, board: Board) -> Tuple[int, int]:
        """评估当前局面，计算并选出最佳落子坐标 (x, y)。"""
        empty_spots: List[Tuple[int, int]] = []
        is_empty = True

        for x in range(BOARD_SIZE):
            for y in range(BOARD_SIZE):
                if board.is_empty(x, y):
                    empty_spots.append((x, y))
                else:
                    is_empty = False

        # 若棋盘全空，首选天元中心点 (7, 7)
        if is_empty:
            return (7, 7)

        # 仅搜索已有棋子周围 2 格以内的邻近空点以大幅提升搜索效率
        candidates: List[Tuple[int, int]] = []
        for x, y in empty_spots:
            if self._has_neighbor(board, x, y, distance=2):
                candidates.append((x, y))

        if not candidates:
            return empty_spots[0] if empty_spots else (7, 7)

        best_score = -1
        best_moves: List[Tuple[int, int]] = []

        for x, y in candidates:
            # 综合进攻分（己方成型）与防守分（遏制敌方）
            attack_score = self._evaluate_point(board, x, y, self.ai_color)
            defense_score = self._evaluate_point(board, x, y, self.opponent_color)

            # 权重平衡：当敌方有强杀招时优先防守
            total_score = int(attack_score * 1.1) + defense_score

            if total_score > best_score:
                best_score = total_score
                best_moves = [(x, y)]
            elif total_score == best_score:
                best_moves.append((x, y))

        return random.choice(best_moves)

    @staticmethod
    def _has_neighbor(board: Board, x: int, y: int, distance: int = 2) -> bool:
        """检查指定坐标周围 distance 范围内是否存在已有棋子。"""
        x_min = max(0, x - distance)
        x_max = min(BOARD_SIZE - 1, x + distance)
        y_min = max(0, y - distance)
        y_max = min(BOARD_SIZE - 1, y + distance)

        for cx in range(x_min, x_max + 1):
            for cy in range(y_min, y_max + 1):
                if not board.is_empty(cx, cy):
                    return True
        return False

    def _evaluate_point(
        self, board: Board, x: int, y: int, color: PieceColor
    ) -> int:
        """评估如果在 (x, y) 落下 color 棋子，在 4 个方向上形成的棋型分值。"""
        score = 0
        # 模拟落子
        board._grid[y][x] = color.value

        for dx, dy in DIRECTIONS:
            score += self._evaluate_line(board, x, y, dx, dy, color)

        # 恢复棋盘
        board._grid[y][x] = PieceColor.EMPTY.value
        return score

    @staticmethod
    def _evaluate_line(
        board: Board,
        x: int,
        y: int,
        dx: int,
        dy: int,
        color: PieceColor,
    ) -> int:
        """单方向沿线格局评分。"""
        count = 1
        open_ends = 0

        # 正向统计连续子数
        cx, cy = x + dx, y + dy
        while (
            0 <= cx < BOARD_SIZE
            and 0 <= cy < BOARD_SIZE
            and board.get_piece(cx, cy) == color
        ):
            count += 1
            cx += dx
            cy += dy
        if 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and board.is_empty(cx, cy):
            open_ends += 1

        # 反向统计连续子数
        cx, cy = x - dx, y - dy
        while (
            0 <= cx < BOARD_SIZE
            and 0 <= cy < BOARD_SIZE
            and board.get_piece(cx, cy) == color
        ):
            count += 1
            cx -= dx
            cy -= dy
        if 0 <= cx < BOARD_SIZE and 0 <= cy < BOARD_SIZE and board.is_empty(cx, cy):
            open_ends += 1

        if count >= 5:
            return SCORE_FIVE
        if count == 4:
            return SCORE_FOUR_OPEN if open_ends == 2 else SCORE_FOUR_BLOCKED
        if count == 3:
            return SCORE_THREE_OPEN if open_ends == 2 else SCORE_THREE_BLOCKED
        if count == 2:
            return SCORE_TWO_OPEN if open_ends == 2 else SCORE_TWO_BLOCKED
        return 0
