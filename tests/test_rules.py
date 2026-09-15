"""五子棋规则引擎与棋盘核心单元测试模块。

严格遵循 PEP 8 规范，所有注释采用中文。
"""

import pytest
from gomoku.core.board import Board
from gomoku.core.constants import BOARD_SIZE
from gomoku.core.enums import PieceColor, WinReason
from gomoku.core.rules import StandardRuleEngine


class TestBoard:
    """棋盘基础功能与边界校验测试。"""

    def test_board_initialization(self) -> None:
        """测试棋盘初始化状态。"""
        board = Board()
        assert board.size == BOARD_SIZE
        assert board.total_moves == 0
        assert board.last_move is None
        assert not board.is_full()

    def test_valid_and_invalid_moves(self) -> None:
        """测试正常落子与边界非法落子防御。"""
        board = Board()
        move1 = board.place_piece(7, 7, PieceColor.BLACK)
        assert move1.x == 7
        assert move1.y == 7
        assert move1.color == PieceColor.BLACK
        assert move1.step_index == 1
        assert board.get_piece(7, 7) == PieceColor.BLACK

        # 重复在已有棋子的位置落子应抛出异常
        with pytest.raises(ValueError, match="不可重复落子"):
            board.place_piece(7, 7, PieceColor.WHITE)

        # 越界坐标落子应抛出异常
        with pytest.raises(ValueError, match="坐标越界"):
            board.place_piece(15, 0, PieceColor.WHITE)


class TestRuleEngine:
    """规则引擎胜负判定测试。"""

    def setup_method(self) -> None:
        """每个测试用例初始化全新的棋盘与规则引擎。"""
        self.board = Board()
        self.rule_engine = StandardRuleEngine()

    def test_horizontal_five_in_a_row_win(self) -> None:
        """测试水平方向五子连珠获胜。"""
        # 黑: (7,7), (8,7), (9,7), (10,7), (11,7) 连五获胜
        # 白: (0,0), (0,1), (0,2), (0,3) 走散点
        moves = [
            (7, 7, PieceColor.BLACK),
            (0, 0, PieceColor.WHITE),
            (8, 7, PieceColor.BLACK),
            (0, 1, PieceColor.WHITE),
            (9, 7, PieceColor.BLACK),
            (0, 2, PieceColor.WHITE),
            (10, 7, PieceColor.BLACK),
            (0, 3, PieceColor.WHITE),
            (11, 7, PieceColor.BLACK),
        ]
        for x, y, color in moves:
            valid, msg = self.rule_engine.validate_move(self.board, x, y, color)
            assert valid, f"合法走子被误判: {msg}"
            self.board.place_piece(x, y, color)

        result = self.rule_engine.check_game_over(self.board)
        assert result.is_game_over is True
        assert result.winner == PieceColor.BLACK
        assert result.reason == WinReason.FIVE_IN_ROW
        assert len(result.winning_line) == 5
        assert (7, 7) in result.winning_line
        assert (11, 7) in result.winning_line

    def test_diagonal_five_in_a_row_win(self) -> None:
        """测试对角线方向五子连珠获胜。"""
        moves = [
            (2, 2, PieceColor.BLACK),
            (0, 1, PieceColor.WHITE),
            (3, 3, PieceColor.BLACK),
            (0, 2, PieceColor.WHITE),
            (4, 4, PieceColor.BLACK),
            (0, 3, PieceColor.WHITE),
            (5, 5, PieceColor.BLACK),
            (0, 4, PieceColor.WHITE),
            (6, 6, PieceColor.BLACK),
        ]
        for x, y, color in moves:
            self.board.place_piece(x, y, color)

        result = self.rule_engine.check_game_over(self.board)
        assert result.is_game_over is True
        assert result.winner == PieceColor.BLACK
        assert len(result.winning_line) == 5

    def test_consecutive_turn_enforcement(self) -> None:
        """测试同一玩家连续落子拦截机制。"""
        self.board.place_piece(7, 7, PieceColor.BLACK)
        valid, msg = self.rule_engine.validate_move(self.board, 8, 8, PieceColor.BLACK)
        assert not valid
        assert "不可连续落子" in msg
