"""Gomoku core domain package.

Contains board data structures, mathematical rules, and game state enumerations.
Zero dependencies on web or database frameworks (Clean Architecture).
"""

from gomoku.core.constants import BOARD_SIZE, DIRECTIONS, WIN_COUNT
from gomoku.core.enums import GameMode, GameStatus, PieceColor, RankTier
from gomoku.core.board import Board, Move
from gomoku.core.rules import IRuleEngine, StandardRuleEngine

__all__ = [
    "BOARD_SIZE",
    "DIRECTIONS",
    "WIN_COUNT",
    "GameMode",
    "GameStatus",
    "PieceColor",
    "RankTier",
    "Board",
    "Move",
    "IRuleEngine",
    "StandardRuleEngine",
]
