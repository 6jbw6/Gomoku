"""五子棋桌面端场景控制器（大厅场景、对局场景与结算榜单弹窗）。

严格遵循 PEP 8 规范，所有注释采用中文。
"""

import time
from typing import Any, List, Optional, Tuple
import pygame
from gomoku.core.board import Board
from gomoku.core.enums import GameMode, PieceColor
from gomoku.core.rules import StandardRuleEngine
from gomoku.gui.ai import GomokuAI
from gomoku.gui.audio import SoundManager
from gomoku.gui.board_view import BoardView
from gomoku.gui.components import Button, Card, ModalDialog, ProgressBar, get_font
from gomoku.gui.constants import (
    COLOR_GOLD_BORDER,
    COLOR_GOLD_PRIMARY,
    COLOR_GREEN_JADE,
    COLOR_STONE_BLACK,
    COLOR_STONE_WHITE,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from gomoku.gui.profile import UserProfileManager
from gomoku.services.rank_service import RankSettlementResult


class LobbyScene:
    """游戏主大厅场景，展示个人排位段位、大师榜入口与四类核心模式。"""

    def __init__(
        self,
        profile_mgr: UserProfileManager,
        sound_mgr: SoundManager,
        on_start_game: Any,
    ) -> None:
        """初始化大厅组件与卡片网格。"""
        self.profile = profile_mgr
        self.sound = sound_mgr
        self.on_start_game = on_start_game

        # 顶部导航栏按键
        self.btn_leaderboard = Button(
            (WINDOW_WIDTH - 240, 18, 100, 36),
            "🏆 天梯榜",
            style="secondary",
            on_click=self._open_leaderboard,
            font_size=15,
        )
        self.btn_sound = Button(
            (WINDOW_WIDTH - 128, 18, 108, 36),
            "🔊 音效: 开",
            style="secondary",
            on_click=self._toggle_sound,
            font_size=15,
        )

        # 个人排位卡片底盘
        self.profile_card = Card((60, 80, WINDOW_WIDTH - 120, 140), border_gold=True)
        self.brave_bar = ProgressBar((WINDOW_WIDTH - 300, 134, 200, 14))

        # 模式选择四宫格卡片 (两行两列)
        card_w, card_h = 510, 220
        start_y = 250
        gap_x, gap_y = 60, 30
        left_x = 60
        right_x = left_x + card_w + gap_x

        self.cards = [
            # 模式一：天梯排位赛
            Card(
                (left_x, start_y, card_w, card_h),
                border_gold=True,
                clickable=True,
                on_click=lambda: self._select_mode(GameMode.RANKED, "天梯排位赛"),
            ),
            # 模式二：单人休闲切磋
            Card(
                (right_x, start_y, card_w, card_h),
                border_gold=False,
                clickable=True,
                on_click=lambda: self._select_mode(GameMode.CASUAL, "单人休闲切磋"),
            ),
            # 模式三：双人同屏对弈
            Card(
                (left_x, start_y + card_h + gap_y, card_w, card_h),
                border_gold=False,
                clickable=True,
                on_click=lambda: self._select_mode(GameMode.FRIEND, "双人同屏对弈"),
            ),
            # 模式四：人机实战推演
            Card(
                (right_x, start_y + card_h + gap_y, card_w, card_h),
                border_gold=False,
                clickable=True,
                on_click=lambda: self._select_mode(GameMode.CASUAL, "人机实战推演", is_ai=True),
            ),
        ]

        # 模态大师榜弹窗
        self.leaderboard_dialog = ModalDialog(width=680, height=480)
        self.leaderboard_dialog.buttons.append(
            Button(
                (WINDOW_WIDTH // 2 - 80, WINDOW_HEIGHT // 2 + 180, 160, 42),
                "关闭返回",
                style="secondary",
                on_click=self.leaderboard_dialog.hide,
            )
        )

    def _toggle_sound(self) -> None:
        """切换音效并刷新按键文案。"""
        is_on = self.sound.toggle()
        self.btn_sound.text = "🔊 音效: 开" if is_on else "🔇 音效: 关"
        self.sound.play_click()

    def _open_leaderboard(self) -> None:
        """打开全服大师天梯榜。"""
        self.sound.play_click()
        self.leaderboard_dialog.show()

    def _select_mode(
        self, mode: GameMode, title: str, is_ai: bool = False
    ) -> None:
        """选择模式并触发启动回调。"""
        self.sound.play_click()
        self.on_start_game(mode, title, is_ai)

    def handle_event(self, event: pygame.event.Event) -> None:
        """分发大厅事件。"""
        if self.leaderboard_dialog.is_visible:
            self.leaderboard_dialog.handle_event(event)
            return

        self.btn_leaderboard.handle_event(event)
        self.btn_sound.handle_event(event)
        for card in self.cards:
            card.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        """绘制游戏大厅全景。"""
        # 1. 顶部标题栏
        font_brand = get_font(22, bold=True)
        brand_surf = font_brand.render("五子棋天梯竞技平台", True, COLOR_GOLD_PRIMARY)
        surface.blit(brand_surf, (60, 20))

        font_sub = get_font(14)
        sub_surf = font_sub.render("GOMOKU ARENA", True, COLOR_TEXT_MUTED)
        surface.blit(sub_surf, (260, 26))

        self.btn_leaderboard.draw(surface)
        self.btn_sound.draw(surface)

        # 2. 个人排位卡片
        self.profile_card.draw(surface)

        font_label = get_font(13)
        lbl_surf = font_label.render("当前排位阶层", True, COLOR_TEXT_MUTED)
        surface.blit(lbl_surf, (84, 98))

        font_rank = get_font(24, bold=True)
        rank_surf = font_rank.render(
            self.profile.display_rank, True, COLOR_GOLD_PRIMARY
        )
        surface.blit(rank_surf, (84, 122))

        # 勇者积分展示
        cap = self.profile.brave_points_cap
        brave_lbl = font_label.render(
            f"勇者积分: {self.profile.state.brave_points} / {cap}",
            True,
            COLOR_GOLD_PRIMARY,
        )
        surface.blit(brave_lbl, (WINDOW_WIDTH - 300, 108))
        self.brave_bar.draw(surface, self.profile.state.brave_points, cap)

        # 战绩胜率与连胜
        stats_text = (
            f"棋手代号: {self.profile.username}   |   "
            f"对局胜率: {self.profile.win_rate}% "
            f"({self.profile.state.win_matches}/{self.profile.state.total_matches}场)   |   "
            f"当前连胜: {self.profile.state.winning_streak}"
        )
        font_stats = get_font(14)
        stats_surf = font_stats.render(stats_text, True, COLOR_TEXT_MUTED)
        surface.blit(stats_surf, (84, 182))

        # 3. 模式卡片渲染
        mode_meta = [
            ("⚔️  天梯排位竞技", "天梯星级加权匹配，胜场升星败场扣星", "支持段位掉星保护与勇者积分抵扣"),
            ("🎯  单人休闲切磋", "快速寻找全网真实棋友切磋弈理", "纯粹技艺推演，不计排位星数"),
            ("🍵  双人同屏对弈", "好友面对面轮流执子切磋交流", "线下同机复刻沉香茶室博弈对决"),
            ("🤖  人机实战推演", "内置多格局启发式智能棋弈算法", "攻守兼备，磨砺定式与杀着招法"),
        ]

        for idx, card in enumerate(self.cards):
            card.draw(surface)
            title, desc1, desc2 = mode_meta[idx]

            font_mode_title = get_font(20, bold=True)
            t_surf = font_mode_title.render(title, True, COLOR_GOLD_PRIMARY)
            surface.blit(t_surf, (card.rect.x + 32, card.rect.y + 36))

            font_desc = get_font(14)
            d1_surf = font_desc.render(desc1, True, COLOR_TEXT_MAIN)
            d2_surf = font_desc.render(desc2, True, COLOR_TEXT_MUTED)
            surface.blit(d1_surf, (card.rect.x + 32, card.rect.y + 88))
            surface.blit(d2_surf, (card.rect.x + 32, card.rect.y + 118))

            # 卡片底部提示
            enter_lbl = font_desc.render(
                "▶ 点击开启对局", True, COLOR_GOLD_PRIMARY if card.is_hovered else COLOR_TEXT_MUTED
            )
            surface.blit(enter_lbl, (card.rect.x + 32, card.rect.y + 168))

        # 4. 模态大师榜弹窗
        if self.leaderboard_dialog.is_visible:
            box = self.leaderboard_dialog.draw_backdrop(surface)
            font_title = get_font(22, bold=True)
            t_surf = font_title.render("🏆 全服天梯大师榜 (棋客榜单)", True, COLOR_GOLD_PRIMARY)
            surface.blit(t_surf, t_surf.get_rect(center=(box.centerx, box.y + 36)))

            # 表头
            font_th = get_font(14, bold=True)
            headers = [("名次", 60), ("棋手昵称", 160), ("天梯段位", 180), ("胜率 (战绩)", 160)]
            hx = box.x + 40
            for h_text, h_w in headers:
                surface.blit(font_th.render(h_text, True, COLOR_TEXT_MUTED), (hx, box.y + 76))
                hx += h_w

            pygame.draw.line(
                surface, COLOR_GOLD_BORDER, (box.x + 30, box.y + 104),
                (box.right - 30, box.y + 104), 1
            )

            # 表格数据行
            lb_data = self.profile.get_leaderboard()
            font_td = get_font(14)
            for row_idx, player in enumerate(lb_data[:7]):
                ry = box.y + 120 + row_idx * 34
                rx = box.x + 40
                is_top3 = player["rank"] <= 3
                rank_str = f"★ {player['rank']}" if is_top3 else f"第 {player['rank']} 名"
                surface.blit(font_td.render(rank_str, True, COLOR_GOLD_PRIMARY), (rx, ry))
                rx += 60
                surface.blit(
                    font_td.render(player["username"], True, COLOR_TEXT_MAIN), (rx, ry)
                )
                rx += 160
                surface.blit(
                    font_td.render(player["tier_name"], True, COLOR_GOLD_PRIMARY), (rx, ry)
                )
                rx += 180
                surface.blit(
                    font_td.render(player["win_rate"], True, COLOR_TEXT_MUTED), (rx, ry)
                )

            # 绘制关闭按钮
            for btn in self.leaderboard_dialog.buttons:
                btn.draw(surface)


class GameScene:
    """核心棋弈对局场景，管理 15x15 棋盘、落子音效、步时倒计时与结算流程。"""

    def __init__(
        self,
        mode: GameMode,
        title: str,
        is_ai: bool,
        profile_mgr: UserProfileManager,
        sound_mgr: SoundManager,
        on_exit: Any,
    ) -> None:
        """初始化对弈场景。"""
        self.mode = mode
        self.title = title
        self.is_ai = is_ai
        self.profile = profile_mgr
        self.sound = sound_mgr
        self.on_exit = on_exit

        # 核心规则引擎与棋盘数据
        self.board = Board()
        self.rules = StandardRuleEngine()
        self.ai = GomokuAI(ai_color=PieceColor.WHITE) if is_ai else None

        # 棋盘视口
        self.board_view = BoardView((60, 60, 680, 680))
        self.hover_pos: Optional[Tuple[int, int]] = None

        # 对局状态变量
        self.current_turn = PieceColor.BLACK
        self.is_game_over: bool = False
        self.winner: Optional[PieceColor] = None
        self.winning_line: Optional[List[Tuple[int, int]]] = None
        self.move_history: List[Tuple[int, int]] = []

        # 倒计时
        self.step_limit_sec: int = 30
        self.turn_start_time = time.time()

        # 结算模态弹窗
        self.settlement_dialog = ModalDialog(width=480, height=360)
        self.settlement_result: Optional[RankSettlementResult] = None
        self.btn_confirm = Button(
            (WINDOW_WIDTH // 2 - 90, WINDOW_HEIGHT // 2 + 100, 180, 44),
            "确认并返回大厅",
            style="gold",
            on_click=self._finish_and_exit,
        )
        self.settlement_dialog.buttons.append(self.btn_confirm)

        # 操作按键
        self.btn_resign = Button(
            (WINDOW_WIDTH - 210, WINDOW_HEIGHT - 90, 150, 40),
            "主动认输",
            style="danger",
            on_click=self._handle_resign,
            font_size=15,
        )
        self.btn_back = Button(
            (WINDOW_WIDTH - 210, 20, 150, 36),
            "返回大厅",
            style="secondary",
            on_click=self._handle_resign,
            font_size=15,
        )

    def _handle_resign(self) -> None:
        """玩家主动认输处理。"""
        if not self.is_game_over:
            self._end_game(winner=PieceColor.WHITE)

    def _finish_and_exit(self) -> None:
        """确认结算并回到主大厅。"""
        self.sound.play_click()
        self.on_exit()

    def _end_game(self, winner: Optional[PieceColor]) -> None:
        """对局终结，触发排位积分与胜率结算。"""
        self.is_game_over = True
        self.winner = winner

        is_winner = (winner == PieceColor.BLACK)
        if is_winner:
            self.sound.play_win()
        else:
            self.sound.play_loss()

        if self.mode == GameMode.RANKED:
            _, self.settlement_result = self.profile.settle_match(
                is_winner=is_winner, moves_count=len(self.move_history)
            )
        else:
            self.profile.state.total_matches += 1
            if is_winner:
                self.profile.state.win_matches += 1
                self.profile.state.winning_streak += 1
            else:
                self.profile.state.winning_streak = 0
            self.profile.save()

        self.settlement_dialog.show()

    def update(self) -> None:
        """每帧更新逻辑，处理 AI 决策与倒计时。"""
        if self.is_game_over:
            return

        # AI 思考处理 (执白棋)
        if self.is_ai and self.current_turn == PieceColor.WHITE:
            time.sleep(0.3)  # 拟真对弈思考微小停顿
            best_x, best_y = self.ai.select_best_move(self.board)
            self._execute_move(best_x, best_y)

    def handle_event(self, event: pygame.event.Event) -> None:
        """处理鼠标点击与对弈落子。"""
        if self.settlement_dialog.is_visible:
            self.settlement_dialog.handle_event(event)
            return

        self.btn_resign.handle_event(event)
        self.btn_back.handle_event(event)

        if self.is_game_over:
            return

        if event.type == pygame.MOUSEMOTION:
            self.hover_pos = self.board_view.to_grid(event.pos[0], event.pos[1])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            grid_pos = self.board_view.to_grid(event.pos[0], event.pos[1])
            if grid_pos:
                x, y = grid_pos
                if self.is_ai and self.current_turn != PieceColor.BLACK:
                    return  # AI 执子回合不允许玩家落子
                self._execute_move(x, y)

    def _execute_move(self, x: int, y: int) -> None:
        """执行合法落子并在命中连珠时结算对局。"""
        is_valid, _ = self.rules.validate_move(self.board, x, y, self.current_turn)
        if not is_valid:
            return

        # 落子入盘
        self.board.place_piece(x, y, self.current_turn)
        self.move_history.append((x, y))
        self.sound.play_stone()

        # 判定是否形成五连珠或平局
        win_res = self.rules.check_game_over(self.board)
        if win_res.is_game_over:
            self.winning_line = win_res.winning_line
            self._end_game(winner=win_res.winner)
            return

        # 轮替执子权
        self.current_turn = self.current_turn.opponent
        self.turn_start_time = time.time()

    def draw(self, surface: pygame.Surface) -> None:
        """绘制对弈界面（棋盘、信息卡片、计时器与结算）。"""
        # 1. 顶部模式说明与返回按键
        font_title = get_font(20, bold=True)
        t_surf = font_title.render(f"【{self.title}】", True, COLOR_GOLD_PRIMARY)
        surface.blit(t_surf, (60, 20))
        self.btn_back.draw(surface)

        # 2. 棋盘绘制
        last_mv = self.move_history[-1] if self.move_history else None
        self.board_view.draw(
            surface,
            self.board,
            last_move=last_mv,
            hover_pos=self.hover_pos if not self.is_game_over else None,
            current_turn=self.current_turn,
            winning_line=self.winning_line,
        )

        # 3. 右侧对弈状态面板
        panel_x = 780
        panel_w = 360

        # 对手卡片 (白棋)
        opp_card = Card((panel_x, 80, panel_w, 140))
        opp_card.draw(surface)
        opp_name = "弈心棋友 (白方)" if not self.is_ai else "电脑棋弈助手 (白方)"
        opp_rank = "尊贵铂金 IV" if not self.is_ai else "启发式大师"

        pygame.draw.circle(surface, COLOR_STONE_WHITE, (panel_x + 36, 120), 16)
        pygame.draw.circle(surface, (180, 170, 160), (panel_x + 36, 120), 16, width=1)

        font_name = get_font(18, bold=True)
        surface.blit(font_name.render(opp_name, True, COLOR_TEXT_MAIN), (panel_x + 64, 108))
        font_tier = get_font(13)
        surface.blit(font_tier.render(opp_rank, True, COLOR_TEXT_MUTED), (panel_x + 64, 136))

        # 局势提示看板
        status_card = Card((panel_x, 240, panel_w, 100), border_gold=True)
        status_card.draw(surface)

        is_my_turn = (self.current_turn == PieceColor.BLACK)
        status_text = "轮到己方落子 (执黑)" if is_my_turn else "对手思考推演中..."
        status_color = COLOR_GREEN_JADE if is_my_turn else COLOR_GOLD_PRIMARY

        font_status = get_font(18, bold=True)
        st_surf = font_status.render(status_text, True, status_color)
        surface.blit(st_surf, (panel_x + 24, 260))

        font_moves = get_font(14)
        moves_msg = f"当前对局手数: 第 {len(self.move_history) + 1} 手"
        surface.blit(font_moves.render(moves_msg, True, COLOR_TEXT_MUTED), (panel_x + 24, 298))

        # 己方卡片 (黑棋)
        my_card = Card((panel_x, 360, panel_w, 140))
        my_card.draw(surface)

        pygame.draw.circle(surface, COLOR_STONE_BLACK, (panel_x + 36, 400), 16)
        pygame.draw.circle(surface, (80, 70, 60), (panel_x + 36, 400), 16, width=1)

        surface.blit(
            font_name.render(f"{self.profile.username} (黑方)", True, COLOR_TEXT_MAIN),
            (panel_x + 64, 388),
        )
        my_tier = self.profile.display_rank
        surface.blit(font_tier.render(my_tier, True, COLOR_GOLD_PRIMARY), (panel_x + 64, 416))

        # 认输按钮
        self.btn_resign.draw(surface)

        # 4. 结算模态弹窗
        if self.settlement_dialog.is_visible:
            box = self.settlement_dialog.draw_backdrop(surface)

            is_win = (self.winner == PieceColor.BLACK)
            title_txt = "对局胜利" if is_win else "对局惜败"
            title_col = COLOR_GOLD_PRIMARY if is_win else COLOR_TEXT_MUTED

            font_res_title = get_font(28, bold=True)
            res_surf = font_res_title.render(title_txt, True, title_col)
            surface.blit(res_surf, res_surf.get_rect(center=(box.centerx, box.y + 44)))

            font_sub = get_font(16)
            if self.mode == GameMode.RANKED and self.settlement_result:
                res = self.settlement_result
                star_str = f"天梯星数变动: {'+' if res.stars_delta >= 0 else ''}{res.stars_delta} 星"
                r_surf = font_sub.render(
                    f"{res.old_rank} ➔ {res.new_rank}",
                    True, COLOR_TEXT_MAIN
                )
                s_surf = font_sub.render(star_str, True, COLOR_GOLD_PRIMARY)
                surface.blit(r_surf, r_surf.get_rect(center=(box.centerx, box.y + 96)))
                surface.blit(s_surf, s_surf.get_rect(center=(box.centerx, box.y + 128)))

                # 勇者积分说明
                brave_msg = (
                    f"获得勇者积分 +{res.brave_points_gained} "
                    f"(当前累计: {res.current_brave_points})"
                )
                if res.protection_triggered:
                    brave_msg += " [已触发保星抵扣]"
                if res.bonus_star_triggered:
                    brave_msg += " [满额额外晋星]"
                b_surf = font_sub.render(brave_msg, True, COLOR_TEXT_MUTED)
                surface.blit(b_surf, b_surf.get_rect(center=(box.centerx, box.y + 160)))
            else:
                c_msg = "休闲对局结束，不计入天梯排位星数"
                c_surf = font_sub.render(c_msg, True, COLOR_TEXT_MUTED)
                surface.blit(c_surf, c_surf.get_rect(center=(box.centerx, box.y + 120)))

            self.btn_confirm.draw(surface)
