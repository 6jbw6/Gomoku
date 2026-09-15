"""五子棋桌面端全局常量与色彩规范。

视觉规范：东方金石雅韵与温润沉香木（严禁任何蓝紫色系）。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from typing import Tuple

# 窗口与帧率规格
WINDOW_WIDTH: int = 1200
WINDOW_HEIGHT: int = 800
FPS: int = 60
TITLE: str = "五子棋天梯竞技平台 (Gomoku Arena)"

# 色彩规范（严格杜绝蓝紫色系，采用东方暖金石、沉香木与玄武炭黑）
COLOR_BG_DARK: Tuple[int, int, int] = (22, 20, 18)             # 玄武岩暖炭黑
COLOR_CARD_BG: Tuple[int, int, int, int] = (35, 31, 28, 225)   # 沉檀木深褐半透
COLOR_CARD_HOVER: Tuple[int, int, int, int] = (48, 42, 37, 240)
COLOR_PANEL_BG: Tuple[int, int, int] = (28, 24, 21)           # 实体面板底色

COLOR_GOLD_PRIMARY: Tuple[int, int, int] = (212, 175, 55)   # 帝王琥珀金
COLOR_GOLD_HOVER: Tuple[int, int, int] = (245, 158, 11)     # 明亮琥珀金
COLOR_GOLD_BORDER: Tuple[int, int, int] = (140, 109, 55)    # 金石古铜边框
COLOR_BORDER_DIM: Tuple[int, int, int] = (61, 53, 46)       # 暗木质边框

COLOR_TEXT_MAIN: Tuple[int, int, int] = (250, 247, 238)     # 羊脂玉白主文字
COLOR_TEXT_MUTED: Tuple[int, int, int] = (168, 160, 150)    # 沉檀灰辅助文字
COLOR_RED_CRIMSON: Tuple[int, int, int] = (220, 38, 38)     # 朱砂印章红（最后手/警示）
COLOR_GREEN_JADE: Tuple[int, int, int] = (22, 163, 74)      # 竹青翡翠绿（就绪/胜利）

# 棋盘与棋子色彩
COLOR_BOARD_BG: Tuple[int, int, int] = (221, 178, 111)      # 沉香金木棋盘底色
COLOR_BOARD_BORDER: Tuple[int, int, int] = (130, 88, 38)    # 棋盘外框深檀木色
COLOR_BOARD_LINE: Tuple[int, int, int] = (84, 57, 22)       # 棋盘经纬古铜墨线
COLOR_STAR_POINT: Tuple[int, int, int] = (70, 48, 18)       # 天元与星位圆点

COLOR_STONE_BLACK: Tuple[int, int, int] = (26, 24, 22)      # 墨玉黑曜石
COLOR_STONE_WHITE: Tuple[int, int, int] = (248, 246, 240)   # 羊脂温润白玉

# 棋盘网格规格
BOARD_GRID_SIZE: int = 15
BOARD_SIZE_PX: int = 660                                    # 棋盘总渲染像素宽度
CELL_SIZE_PX: int = BOARD_SIZE_PX // (BOARD_GRID_SIZE + 1)  # 网格单元像素间距
STONE_RADIUS: int = int(CELL_SIZE_PX * 0.44)                # 棋子半径
