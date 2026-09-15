"""五子棋桌面端棋盘视口与落子渲染器。

负责 15x15 沉香金木棋盘绘制、墨玉/白玉拟真立体棋子渲染、天元星位与五子连珠高光。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from typing import List, Optional, Tuple
import pygame
from gomoku.core.board import Board
from gomoku.core.constants import BOARD_SIZE
from gomoku.core.enums import PieceColor
from gomoku.gui.components import get_font
from gomoku.gui.constants import (
    COLOR_BOARD_BG,
    COLOR_BOARD_BORDER,
    COLOR_BOARD_LINE,
    COLOR_GOLD_HOVER,
    COLOR_GOLD_PRIMARY,
    COLOR_RED_CRIMSON,
    COLOR_STAR_POINT,
    COLOR_STONE_BLACK,
    COLOR_STONE_WHITE,
)

# 棋盘星位坐标 (天元 + 四隅星，格式 (x, y) 即 (col, row))
STAR_POINTS: List[Tuple[int, int]] = [
    (3, 3), (3, 11), (7, 7), (11, 3), (11, 11)
]
COORD_LETTERS: List[str] = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "O", "P"
]


class BoardView:
    """棋盘视图渲染器，管理像素坐标换算与棋子动画效果。"""

    def __init__(self, rect: Tuple[int, int, int, int]) -> None:
        """根据给定的屏幕矩形区域初始化网格规格。"""
        self.rect = pygame.Rect(rect)
        self.margin: int = 36
        self.grid_width: int = self.rect.width - 2 * self.margin
        self.cell_size: float = self.grid_width / (BOARD_SIZE - 1)
        self.stone_radius: int = int(self.cell_size * 0.44)

    def to_pixel(self, x: int, y: int) -> Tuple[int, int]:
        """将棋盘逻辑坐标 (x, y) 换算为屏幕像素 (px, py)。"""
        px = int(self.rect.x + self.margin + x * self.cell_size)
        py = int(self.rect.y + self.margin + y * self.cell_size)
        return (px, py)

    def to_grid(self, px: int, py: int) -> Optional[Tuple[int, int]]:
        """将鼠标像素坐标转换为最近的合法网格交叉点 (x, y)。"""
        if not self.rect.collidepoint(px, py):
            return None

        rel_x = px - (self.rect.x + self.margin)
        rel_y = py - (self.rect.y + self.margin)

        col = round(rel_x / self.cell_size)
        row = round(rel_y / self.cell_size)

        if 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE:
            center_x, center_y = self.to_pixel(col, row)
            dist_sq = (px - center_x) ** 2 + (py - center_y) ** 2
            if dist_sq <= (self.cell_size * 0.52) ** 2:
                return (col, row)
        return None

    def draw(
        self,
        surface: pygame.Surface,
        board: Board,
        last_move: Optional[Tuple[int, int]] = None,
        hover_pos: Optional[Tuple[int, int]] = None,
        current_turn: PieceColor = PieceColor.BLACK,
        winning_line: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        """绘制整张棋盘，包括木纹底盘、经纬墨线、星位、坐标及所有棋子。"""
        # 1. 绘制沉香木质棋盘底盘与外框阴影
        shadow_rect = self.rect.copy()
        shadow_rect.x += 6
        shadow_rect.y += 8
        pygame.draw.rect(surface, (14, 12, 10), shadow_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_BOARD_BG, self.rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_BOARD_BORDER, self.rect, width=3, border_radius=12)

        # 2. 绘制 15x15 经纬古铜墨线
        font_coord = get_font(12)
        for i in range(BOARD_SIZE):
            p1 = self.to_pixel(i, 0)
            p2 = self.to_pixel(i, BOARD_SIZE - 1)
            pygame.draw.line(surface, COLOR_BOARD_LINE, p1, p2, 1)

            q1 = self.to_pixel(0, i)
            q2 = self.to_pixel(BOARD_SIZE - 1, i)
            pygame.draw.line(surface, COLOR_BOARD_LINE, q1, q2, 1)

            # 绘制坐标标识（横轴 A-O，纵轴 15-1）
            letter_surf = font_coord.render(COORD_LETTERS[i], True, (90, 65, 30))
            surface.blit(letter_surf, (p1[0] - 5, self.rect.y + 12))
            surface.blit(letter_surf, (p2[0] - 5, self.rect.bottom - 24))

            num_str = str(BOARD_SIZE - i)
            num_surf = font_coord.render(num_str, True, (90, 65, 30))
            surface.blit(num_surf, (self.rect.x + 12, q1[1] - 8))
            surface.blit(num_surf, (self.rect.right - 24, q2[1] - 8))

        # 3. 绘制天元与四隅星位圆点
        for sx, sy in STAR_POINTS:
            sp_x, sp_y = self.to_pixel(sx, sy)
            pygame.draw.circle(surface, COLOR_STAR_POINT, (sp_x, sp_y), 4)

        # 4. 绘制已落子实体（带立体光影与材质渐变）
        for x in range(BOARD_SIZE):
            for y in range(BOARD_SIZE):
                color = board.get_piece(x, y)
                if color != PieceColor.EMPTY:
                    px, py = self.to_pixel(x, y)
                    self._draw_stone(surface, px, py, color)

        # 5. 绘制最后手红印章指示标记
        if last_move is not None:
            lx, ly = self.to_pixel(last_move[0], last_move[1])
            pygame.draw.circle(surface, COLOR_RED_CRIMSON, (lx, ly), 4)
            pygame.draw.circle(surface, (255, 255, 255), (lx, ly), 5, width=1)

        # 6. 绘制获胜五子连珠高光连线与金环
        if winning_line and len(winning_line) >= 5:
            start_px = self.to_pixel(winning_line[0][0], winning_line[0][1])
            end_px = self.to_pixel(winning_line[-1][0], winning_line[-1][1])
            pygame.draw.line(surface, COLOR_GOLD_HOVER, start_px, end_px, 4)
            for wx, wy in winning_line:
                wpx, wpy = self.to_pixel(wx, wy)
                pygame.draw.circle(
                    surface, COLOR_GOLD_PRIMARY, (wpx, wpy), self.stone_radius + 3, 2
                )

        # 7. 鼠标悬停半透明预览落子
        if hover_pos and board.is_empty(hover_pos[0], hover_pos[1]):
            hx, hy = self.to_pixel(hover_pos[0], hover_pos[1])
            self._draw_hover_stone(surface, hx, hy, current_turn)

    def _draw_stone(self, surface: pygame.Surface, x: int, y: int, color: PieceColor) -> None:
        """绘制拟真立体质感棋子（墨玉曜黑 / 羊脂温润白玉）。"""
        r = self.stone_radius
        # 底部接触面投影
        pygame.draw.circle(surface, (18, 15, 12), (x + 2, y + 3), r)

        if color == PieceColor.BLACK:
            # 墨玉黑曜石主体
            pygame.draw.circle(surface, COLOR_STONE_BLACK, (x, y), r)
            # 左上方高光渐变弧光
            highlight_pos = (x - int(r * 0.32), y - int(r * 0.32))
            pygame.draw.circle(surface, (68, 62, 56), highlight_pos, int(r * 0.42))
            pygame.draw.circle(surface, (120, 110, 100), highlight_pos, int(r * 0.18))
        else:
            # 羊脂温润白玉主体
            pygame.draw.circle(surface, (208, 198, 184), (x, y), r)
            pygame.draw.circle(surface, COLOR_STONE_WHITE, (x - 1, y - 1), r - 1)
            # 顶部温润白玉漫反射高光
            highlight_pos = (x - int(r * 0.30), y - int(r * 0.30))
            pygame.draw.circle(surface, (255, 255, 255), highlight_pos, int(r * 0.38))

    def _draw_hover_stone(
        self, surface: pygame.Surface, x: int, y: int, color: PieceColor
    ) -> None:
        """绘制鼠标悬停处的轻微半透明投影。"""
        r = self.stone_radius
        hover_surf = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
        center = (r + 2, r + 2)
        if color == PieceColor.BLACK:
            pygame.draw.circle(hover_surf, (20, 18, 16, 120), center, r)
        else:
            pygame.draw.circle(hover_surf, (255, 255, 255, 150), center, r)
        surface.blit(hover_surf, (x - r - 2, y - r - 2))
