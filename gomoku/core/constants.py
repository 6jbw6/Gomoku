"""五子棋领域核心常量定义模块。

严格遵循 PEP 8 规范，所有注释采用中文。
"""

from typing import Final, Tuple

# 标准五子棋棋盘交叉点规格 (15x15)
BOARD_SIZE: Final[int] = 15

# 达成胜负判定的连续棋子数量（五子连珠）
WIN_COUNT: Final[int] = 5

# 连珠扫描的四个基本方向向量：
# (dx, dy): (水平方向, 垂直方向, 正斜下对角线 \, 反斜上对角线 /)
DIRECTIONS: Final[Tuple[Tuple[int, int], ...]] = (
    (1, 0),   # 水平向右
    (0, 1),   # 垂直向下
    (1, 1),   # 正斜向右下 (\)
    (1, -1),  # 反斜向右上 (/)
)
