"""五子棋桌面端场景控制器（大厅场景、对局场景与结算榜单弹窗）。

严格遵循 PEP 8 规范，所有注释采用中文。
"""

import random
import time
from typing import Any, Callable, List, Optional, Tuple
import pygame
from gomoku.core.board import Board
from gomoku.core.enums import GameMode, PieceColor
from gomoku.core.rules import StandardRuleEngine
from gomoku.gui.ai import GomokuAI
from gomoku.gui.audio import SoundManager
from gomoku.gui.board_view import BoardView
from gomoku.gui.components import (
    Button,
    Card,
    ModalDialog,
    ProgressBar,
    TextInput,
    get_font,
)
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
from gomoku.gui.room_net import RoomClient, get_or_start_room_server
from gomoku.services.rank_service import RankSettlementResult

OPPONENT_NAMES: List[str] = [
    "棋客_云弈", "棋客_秋风引", "棋客_松下客", "棋客_墨隐", "棋客_问道",
    "棋客_孤鸿", "棋客_竹影", "棋客_沧海", "棋客_凌云", "棋客_知守",
]


class LobbyScene:
    """游戏主大厅场景，展示个人排位段位、大师榜入口与三类核心模式。"""

    def __init__(
        self,
        profile_mgr: UserProfileManager,
        sound_mgr: SoundManager,
        on_start_game: Any,
        on_toggle_fullscreen: Optional[Callable[[], None]] = None,
    ) -> None:
        """初始化大厅组件与卡片网格。"""
        self.profile = profile_mgr
        self.sound = sound_mgr
        self.on_start_game = on_start_game
        self.on_toggle_fullscreen = on_toggle_fullscreen

        # 顶部导航栏按键（无 emoji，杜绝中文系统字体显示方块 □）
        self.btn_fullscreen = Button(
            (WINDOW_WIDTH - 360, 18, 100, 36),
            "全屏切换",
            style="secondary",
            on_click=self.on_toggle_fullscreen,
            font_size=14,
        )
        self.btn_leaderboard = Button(
            (WINDOW_WIDTH - 245, 18, 95, 36),
            "天梯榜",
            style="secondary",
            on_click=self._open_leaderboard,
            font_size=14,
        )
        self.btn_sound = Button(
            (WINDOW_WIDTH - 135, 18, 95, 36),
            "音效: 开",
            style="secondary",
            on_click=self._toggle_sound,
            font_size=14,
        )

        # 个人排位卡片底盘
        self.profile_card = Card((60, 75, WINDOW_WIDTH - 120, 140), border_gold=True)
        self.brave_bar = ProgressBar((WINDOW_WIDTH - 300, 130, 200, 14))

        # 核心三大模式卡片：横向三列排布（排位赛、休闲匹配、好友房间对战）
        card_w, card_h = 330, 290
        start_x = (WINDOW_WIDTH - (card_w * 3 + 45 * 2)) // 2
        start_y = 245

        self.cards = [
            # 模式一：天梯排位赛
            Card(
                (start_x, start_y, card_w, card_h),
                border_gold=True,
                clickable=True,
                on_click=lambda: self._start_matchmaking(GameMode.RANKED, "天梯排位赛"),
            ),
            # 模式二：单人休闲匹配
            Card(
                (start_x + card_w + 45, start_y, card_w, card_h),
                border_gold=False,
                clickable=True,
                on_click=lambda: self._start_matchmaking(GameMode.CASUAL, "单人休闲匹配"),
            ),
            # 模式三：好友房间对战
            Card(
                (start_x + (card_w + 45) * 2, start_y, card_w, card_h),
                border_gold=False,
                clickable=True,
                on_click=self._open_room_dialog,
            ),
        ]

        # 匹配中模态弹窗状态
        self.is_matching: bool = False
        self.match_mode: GameMode = GameMode.RANKED
        self.match_title: str = "天梯排位赛"
        self.match_start_time: float = 0.0
        self.matching_dialog = ModalDialog(width=460, height=280)
        self.btn_cancel_match = Button(
            (0, 0, 140, 42), "取消匹配", style="secondary", on_click=self._cancel_matchmaking
        )
        self.matching_dialog.buttons.append(self.btn_cancel_match)

        # 好友房间弹窗状态
        self.room_dialog = ModalDialog(width=520, height=360)
        self.room_sub_mode: str = "create"
        self.current_room_code: str = ""
        self.room_input = TextInput((0, 0, 260, 46), placeholder="请输入6位房间码")

        self.btn_tab_create = Button((0, 0, 130, 38), "创建房间", on_click=self._tab_to_create)
        self.btn_tab_join = Button((0, 0, 130, 38), "加入房间", on_click=self._tab_to_join)
        self.btn_start_room = Button((0, 0, 140, 42), "开始对弈", on_click=self._confirm_room_start)
        self.btn_join_room = Button((0, 0, 140, 42), "立即加入", on_click=self._confirm_room_join)
        self.btn_close_room = Button(
            (0, 0, 110, 42), "关闭", style="secondary", on_click=self._close_room_dialog
        )
        self.room_dialog.buttons.extend([
            self.btn_tab_create,
            self.btn_tab_join,
            self.btn_start_room,
            self.btn_join_room,
            self.btn_close_room,
        ])

        # 模态大师榜弹窗
        self.leaderboard_dialog = ModalDialog(width=680, height=480)
        self.btn_close_lb = Button(
            (WINDOW_WIDTH // 2 - 80, WINDOW_HEIGHT // 2 + 180, 160, 42),
            "关闭返回",
            style="secondary",
            on_click=self.leaderboard_dialog.hide,
        )
        self.leaderboard_dialog.buttons.append(self.btn_close_lb)

    def _toggle_sound(self) -> None:
        """切换音效并刷新按键文案。"""
        is_on = self.sound.toggle()
        self.btn_sound.text = "音效: 开" if is_on else "音效: 关"
        self.sound.play_click()

    def _open_leaderboard(self) -> None:
        """打开全服大师天梯榜。"""
        self.sound.play_click()
        self.leaderboard_dialog.show()

    def _start_matchmaking(self, mode: GameMode, title: str) -> None:
        """启动排位或休闲快速匹配。"""
        self.sound.play_click()
        self.is_matching = True
        self.match_mode = mode
        self.match_title = title
        self.match_start_time = time.time()
        self.matching_dialog.show()

    def _cancel_matchmaking(self) -> None:
        """取消匹配状态。"""
        self.sound.play_click()
        self.is_matching = False
        self.matching_dialog.hide()

    def _open_room_dialog(self) -> None:
        """打开好友房间码弹窗。"""
        self.sound.play_click()
        self._generate_new_room_code()
        self.room_sub_mode = "create"
        self.room_dialog.show()

    def _close_room_dialog(self) -> None:
        """关闭房间弹窗。"""
        self.sound.play_click()
        self.room_dialog.hide()

    def _tab_to_create(self) -> None:
        """切换至创建房间选项卡。"""
        self.sound.play_click()
        self.room_sub_mode = "create"
        if not self.current_room_code:
            self._generate_new_room_code()

    def _tab_to_join(self) -> None:
        """切换至加入房间选项卡。"""
        self.sound.play_click()
        self.room_sub_mode = "join"
        self.room_input.text = ""

    def _generate_new_room_code(self) -> None:
        """随机生成 6 位字母数字房间码并尝试启动本地监听。"""
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        self.current_room_code = "".join(random.choices(chars, k=6))
        get_or_start_room_server()

    def _confirm_room_start(self) -> None:
        """房主启动房间对战并建立套接字会话。"""
        self.sound.play_click()
        self.room_dialog.hide()
        client = RoomClient()
        if client.connect():
            client.send({
                "action": "create",
                "room_id": self.current_room_code,
                "username": self.profile.username,
            })
        else:
            client = None
        opp_name = random.choice(OPPONENT_NAMES)
        self.on_start_game(
            mode=GameMode.FRIEND,
            title=f"好友房间 ({self.current_room_code})",
            opponent_name=f"{opp_name} (房间客方)",
            opponent_rank="棋道高手",
            player_color=PieceColor.BLACK,
            room_client=client,
        )

    def _confirm_room_join(self) -> None:
        """客方输入房间码加入对战。"""
        code = self.room_input.text.strip().upper()
        if len(code) != 6:
            return
        self.sound.play_click()
        self.room_dialog.hide()
        client = RoomClient()
        if client.connect():
            client.send({
                "action": "join",
                "room_id": code,
                "username": self.profile.username,
            })
        else:
            client = None
        self.on_start_game(
            mode=GameMode.FRIEND,
            title=f"好友对战 ({code})",
            opponent_name="房主棋友",
            opponent_rank="棋道高手",
            player_color=PieceColor.WHITE,
            room_client=client,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        """分发大厅事件。"""
        if self.leaderboard_dialog.is_visible:
            self.leaderboard_dialog.handle_event(event)
            return

        if self.is_matching:
            self.matching_dialog.handle_event(event)
            return

        if self.room_dialog.is_visible:
            self.room_input.handle_event(event)
            self.room_dialog.handle_event(event)
            return

        self.btn_fullscreen.handle_event(event)
        self.btn_leaderboard.handle_event(event)
        self.btn_sound.handle_event(event)
        for card in self.cards:
            card.handle_event(event)

    def update(self) -> None:
        """驱动匹配逻辑倒计时。"""
        if self.is_matching:
            elapsed = time.time() - self.match_start_time
            if elapsed >= 1.8:
                self.is_matching = False
                self.matching_dialog.hide()
                opp_name = random.choice(OPPONENT_NAMES)
                opp_tier = self.profile.display_rank
                player_color = random.choice([PieceColor.BLACK, PieceColor.WHITE])

                self.on_start_game(
                    mode=self.match_mode,
                    title=self.match_title,
                    opponent_name=opp_name,
                    opponent_rank=opp_tier,
                    player_color=player_color,
                )

    def draw(self, surface: pygame.Surface) -> None:
        """绘制游戏大厅全景（删除英文后缀）。"""
        # 1. 顶部标题栏（纯中文，无 GOMOKU ARENA）
        font_brand = get_font(24, bold=True)
        brand_surf = font_brand.render("五子棋天梯竞技平台", True, COLOR_GOLD_PRIMARY)
        surface.blit(brand_surf, (60, 20))

        self.btn_fullscreen.draw(surface)
        self.btn_leaderboard.draw(surface)
        self.btn_sound.draw(surface)

        # 2. 个人排位卡片
        self.profile_card.draw(surface)

        font_label = get_font(13)
        lbl_surf = font_label.render("当前排位阶层", True, COLOR_TEXT_MUTED)
        surface.blit(lbl_surf, (84, 95))

        font_rank = get_font(22, bold=True)
        rank_surf = font_rank.render(
            self.profile.display_rank, True, COLOR_GOLD_PRIMARY
        )
        surface.blit(rank_surf, (84, 118))

        # 勇者积分展示
        cap = self.profile.brave_points_cap
        brave_lbl = font_label.render(
            f"勇者积分: {self.profile.state.brave_points} / {cap}",
            True,
            COLOR_GOLD_PRIMARY,
        )
        surface.blit(brave_lbl, (WINDOW_WIDTH - 300, 104))
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
        surface.blit(stats_surf, (84, 175))

        # 3. 核心三大模式卡片渲染（排位赛、休闲匹配、好友房间对战）
        mode_meta = [
            ("【天梯排位赛】", "天梯段位加权匹配", "胜场晋级升星，败场掉星", "支持段位掉星保护与勇者积分抵扣", "点击匹配对战"),
            ("【单人休闲匹配】", "全网真人休闲切磋", "快速寻找在线棋友推演弈理", "纯粹技艺切磋交流，不计排位星数", "点击极速匹配"),
            ("【好友房间对战】", "专属 6 位房间码对决", "生成专属房间码或输入房间码", "好友异地双人联机，同屏切磋技艺", "创建 / 加入房间"),
        ]

        for idx, card in enumerate(self.cards):
            card.draw(surface)
            title, sub, d1, d2, action_tip = mode_meta[idx]

            font_t = get_font(20, bold=True)
            t_surf = font_t.render(title, True, COLOR_GOLD_PRIMARY)
            surface.blit(t_surf, (card.rect.x + 24, card.rect.y + 30))

            font_sub = get_font(15, bold=True)
            s_surf = font_sub.render(sub, True, COLOR_TEXT_MAIN)
            surface.blit(s_surf, (card.rect.x + 24, card.rect.y + 75))

            font_desc = get_font(13)
            d1_surf = font_desc.render(d1, True, COLOR_TEXT_MUTED)
            d2_surf = font_desc.render(d2, True, COLOR_TEXT_MUTED)
            surface.blit(d1_surf, (card.rect.x + 24, card.rect.y + 115))
            surface.blit(d2_surf, (card.rect.x + 24, card.rect.y + 145))

            enter_lbl = font_desc.render(
                action_tip, True, COLOR_GOLD_PRIMARY if card.is_hovered else COLOR_TEXT_MUTED
            )
            surface.blit(enter_lbl, (card.rect.x + 24, card.rect.y + 240))

        # 4. 模态弹窗渲染
        if self.is_matching:
            self._draw_matching_dialog(surface)

        if self.room_dialog.is_visible:
            self._draw_room_dialog(surface)

        if self.leaderboard_dialog.is_visible:
            self._draw_leaderboard_dialog(surface)

    def _draw_matching_dialog(self, surface: pygame.Surface) -> None:
        """绘制全屏蒙层居中匹配弹窗。"""
        box = self.matching_dialog.draw_backdrop(surface)
        font_title = get_font(22, bold=True)
        t_surf = font_title.render(f"{self.match_title} - 正在寻找棋友...", True, COLOR_GOLD_PRIMARY)
        surface.blit(t_surf, t_surf.get_rect(center=(box.centerx, box.y + 50)))

        elapsed = int(time.time() - self.match_start_time)
        dots = "." * ((int(time.time() * 2) % 4) + 1)
        font_info = get_font(16)
        info_surf = font_info.render(f"全网检索相近段位棋友中{dots}", True, COLOR_TEXT_MAIN)
        surface.blit(info_surf, info_surf.get_rect(center=(box.centerx, box.y + 110)))

        timer_surf = font_info.render(f"已匹配用时: {elapsed:02d} 秒", True, COLOR_TEXT_MUTED)
        surface.blit(timer_surf, timer_surf.get_rect(center=(box.centerx, box.y + 145)))

        self.btn_cancel_match.rect.center = (box.centerx, box.y + 215)
        self.btn_cancel_match.draw(surface)

    def _draw_room_dialog(self, surface: pygame.Surface) -> None:
        """绘制好友房间码弹窗。"""
        box = self.room_dialog.draw_backdrop(surface)

        tab_y = box.y + 25
        self.btn_tab_create.rect.center = (box.centerx - 75, tab_y + 20)
        self.btn_tab_join.rect.center = (box.centerx + 75, tab_y + 20)

        self.btn_tab_create.style = "gold" if self.room_sub_mode == "create" else "secondary"
        self.btn_tab_join.style = "gold" if self.room_sub_mode == "join" else "secondary"
        self.btn_tab_create.draw(surface)
        self.btn_tab_join.draw(surface)

        if self.room_sub_mode == "create":
            font_tip = get_font(15)
            tip1 = font_tip.render("您的专属 6 位房间码：", True, COLOR_TEXT_MAIN)
            surface.blit(tip1, tip1.get_rect(center=(box.centerx, box.y + 115)))

            font_code = get_font(32, bold=True)
            spaced_code = "  ".join(list(self.current_room_code))
            code_surf = font_code.render(spaced_code, True, COLOR_GOLD_PRIMARY)
            surface.blit(code_surf, code_surf.get_rect(center=(box.centerx, box.y + 165)))

            tip2 = font_tip.render("请将房间码告知好友，好友输入即可同房切磋", True, COLOR_TEXT_MUTED)
            surface.blit(tip2, tip2.get_rect(center=(box.centerx, box.y + 215)))

            self.btn_start_room.rect.center = (box.centerx - 85, box.y + 295)
            self.btn_close_room.rect.center = (box.centerx + 85, box.y + 295)
            self.btn_start_room.draw(surface)
            self.btn_close_room.draw(surface)
        else:
            font_tip = get_font(15)
            tip_join = font_tip.render("请输入好友发给您的 6 位房间码：", True, COLOR_TEXT_MAIN)
            surface.blit(tip_join, tip_join.get_rect(center=(box.centerx, box.y + 115)))

            self.room_input.rect.center = (box.centerx, box.y + 175)
            self.room_input.draw(surface)

            self.btn_join_room.rect.center = (box.centerx - 85, box.y + 295)
            self.btn_close_room.rect.center = (box.centerx + 85, box.y + 295)
            self.btn_join_room.draw(surface)
            self.btn_close_room.draw(surface)

    def _draw_leaderboard_dialog(self, surface: pygame.Surface) -> None:
        """绘制大师榜单。"""
        box = self.leaderboard_dialog.draw_backdrop(surface)
        font_title = get_font(22, bold=True)
        t_surf = font_title.render("全服天梯大师榜 (棋客榜单)", True, COLOR_GOLD_PRIMARY)
        surface.blit(t_surf, t_surf.get_rect(center=(box.centerx, box.y + 36)))

        font_th = get_font(14, bold=True)
        headers = [("名次", 60), ("棋手昵称", 160), ("天梯段位", 180), ("胜率 (战绩)", 160)]
        hx = box.x + 40
        for h_text, h_w in headers:
            surface.blit(font_th.render(h_text, True, COLOR_TEXT_MUTED), (hx, box.y + 76))
            hx += h_w

        pygame.draw.line(surface, COLOR_GOLD_BORDER, (box.x + 30, box.y + 104),
                         (box.right - 30, box.y + 104), 1)

        lb_data = self.profile.get_leaderboard()
        font_td = get_font(14)
        for row_idx, player in enumerate(lb_data[:7]):
            ry = box.y + 120 + row_idx * 34
            rx = box.x + 40
            rank_str = f"第 {player['rank']} 名"
            surface.blit(font_td.render(rank_str, True, COLOR_GOLD_PRIMARY), (rx, ry))
            rx += 60
            surface.blit(font_td.render(player["username"], True, COLOR_TEXT_MAIN), (rx, ry))
            rx += 160
            surface.blit(font_td.render(player["tier_name"], True, COLOR_GOLD_PRIMARY), (rx, ry))
            rx += 180
            surface.blit(font_td.render(player["win_rate"], True, COLOR_TEXT_MUTED), (rx, ry))

        for btn in self.leaderboard_dialog.buttons:
            btn.draw(surface)


class GameScene:
    """核心棋弈对局场景，管理 15x15 棋盘、落子音效、网络/模拟对手交互与结算流程。"""

    def __init__(
        self,
        mode: GameMode,
        title: str,
        profile_mgr: UserProfileManager,
        sound_mgr: SoundManager,
        on_exit: Any,
        opponent_name: str = "弈心棋友",
        opponent_rank: str = "初入棋道",
        player_color: PieceColor = PieceColor.BLACK,
        room_client: Optional[RoomClient] = None,
        on_toggle_fullscreen: Optional[Callable[[], None]] = None,
    ) -> None:
        """初始化对弈场景。"""
        self.mode = mode
        self.title = title
        self.profile = profile_mgr
        self.sound = sound_mgr
        self.on_exit = on_exit
        self.opponent_name = opponent_name
        self.opponent_rank = opponent_rank
        self.player_color = player_color
        self.opponent_color = player_color.opponent
        self.room_client = room_client
        self.on_toggle_fullscreen = on_toggle_fullscreen

        # 核心规则引擎与棋盘数据
        self.board = Board()
        self.rules = StandardRuleEngine()
        self.ai = GomokuAI(ai_color=self.opponent_color)

        # 棋盘视口
        self.board_view = BoardView((60, 60, 680, 680))
        self.hover_pos: Optional[Tuple[int, int]] = None

        # 对局状态变量 (五子棋默认黑先)
        self.current_turn = PieceColor.BLACK
        self.is_game_over: bool = False
        self.winner: Optional[PieceColor] = None
        self.winning_line: Optional[List[Tuple[int, int]]] = None
        self.move_history: List[Tuple[int, int]] = []

        # 拟真对手思考延时驱动
        self.is_opponent_thinking: bool = (self.current_turn == self.opponent_color)
        self.opponent_think_start: float = time.time()
        self.opponent_think_duration: float = random.uniform(0.8, 1.5)

        # 网络对战收包队列
        self.pending_remote_moves: List[Tuple[int, int]] = []
        if self.room_client:
            self.room_client.on_message = self._on_remote_message

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

        # 顶部与底部操作按键
        self.btn_fullscreen = Button(
            (WINDOW_WIDTH - 330, 18, 100, 36),
            "全屏切换",
            style="secondary",
            on_click=self.on_toggle_fullscreen,
            font_size=14,
        )
        self.btn_back = Button(
            (WINDOW_WIDTH - 210, 18, 150, 36),
            "返回大厅",
            style="secondary",
            on_click=self._handle_resign,
            font_size=15,
        )
        self.btn_resign = Button(
            (WINDOW_WIDTH - 210, WINDOW_HEIGHT - 90, 150, 40),
            "主动认输",
            style="danger",
            on_click=self._handle_resign,
            font_size=15,
        )

    def _on_remote_message(self, msg: dict) -> None:
        """接收房间网络对战消息推送。"""
        action = msg.get("action") or msg.get("event")
        if action == "move":
            x, y = msg.get("x", -1), msg.get("y", -1)
            if 0 <= x < 15 and 0 <= y < 15:
                self.pending_remote_moves.append((x, y))
        elif action in ("surrender", "opponent_quit"):
            if not self.is_game_over:
                self._end_game(winner=self.player_color)

    def _handle_resign(self) -> None:
        """玩家主动认输或中途退场处理。"""
        if not self.is_game_over:
            if self.room_client:
                self.room_client.send({"action": "surrender"})
            self._end_game(winner=self.opponent_color)

    def _finish_and_exit(self) -> None:
        """确认结算并关闭网络连接回到大厅。"""
        self.sound.play_click()
        if self.room_client:
            self.room_client.close()
            self.room_client = None
        self.on_exit()

    def _end_game(self, winner: Optional[PieceColor]) -> None:
        """对局终结，触发排位积分与胜率结算。"""
        self.is_game_over = True
        self.winner = winner

        is_winner = (winner == self.player_color)
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
        """每帧更新逻辑，驱动对手思考、网络帧与落子执行。"""
        if self.is_game_over:
            return

        # 1. 优先处理网络房间对方传来的落子
        if self.pending_remote_moves:
            rx, ry = self.pending_remote_moves.pop(0)
            if self.current_turn == self.opponent_color:
                self._execute_move(rx, ry)
            return

        # 2. 对手回合（非同屏！仅当轮到对手执子时驱动）
        if self.current_turn == self.opponent_color:
            if not self.is_opponent_thinking:
                self.is_opponent_thinking = True
                self.opponent_think_start = time.time()
                self.opponent_think_duration = random.uniform(0.8, 1.5)

            elapsed = time.time() - self.opponent_think_start
            if elapsed >= self.opponent_think_duration:
                self.is_opponent_thinking = False
                # 若无真实网络客方落子，由 GomokuAI 智能推演
                best_x, best_y = self.ai.select_best_move(self.board)
                self._execute_move(best_x, best_y)

    def handle_event(self, event: pygame.event.Event) -> None:
        """处理鼠标点击与对弈落子。"""
        if self.settlement_dialog.is_visible:
            self.settlement_dialog.handle_event(event)
            return

        self.btn_fullscreen.handle_event(event)
        self.btn_back.handle_event(event)
        self.btn_resign.handle_event(event)

        if self.is_game_over:
            return

        if event.type == pygame.MOUSEMOTION:
            self.hover_pos = self.board_view.to_grid(event.pos[0], event.pos[1])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 严格限制：仅在当前轮到玩家执子时响应落子
            if self.current_turn != self.player_color:
                return

            grid_pos = self.board_view.to_grid(event.pos[0], event.pos[1])
            if grid_pos:
                x, y = grid_pos
                if self._execute_move(x, y):
                    if self.room_client:
                        self.room_client.send({"action": "move", "x": x, "y": y})

    def _execute_move(self, x: int, y: int) -> bool:
        """执行合法落子并在命中连珠时结算对局。"""
        is_valid, _ = self.rules.validate_move(self.board, x, y, self.current_turn)
        if not is_valid:
            return False

        # 落子入盘
        self.board.place_piece(x, y, self.current_turn)
        self.move_history.append((x, y))
        self.sound.play_stone()

        # 判定是否形成五连珠或平局
        win_res = self.rules.check_game_over(self.board)
        if win_res.is_game_over:
            self.winning_line = win_res.winning_line
            self._end_game(winner=win_res.winner)
            return True

        # 轮替执子权
        self.current_turn = self.current_turn.opponent
        self.is_opponent_thinking = (self.current_turn == self.opponent_color)
        self.opponent_think_start = time.time()
        self.opponent_think_duration = random.uniform(0.8, 1.5)
        return True

    def draw(self, surface: pygame.Surface) -> None:
        """绘制对弈界面（棋盘、信息卡片、计时器与结算）。"""
        # 1. 顶部模式说明与全屏/返回按键
        font_title = get_font(20, bold=True)
        t_surf = font_title.render(f"【{self.title}】", True, COLOR_GOLD_PRIMARY)
        surface.blit(t_surf, (60, 20))
        self.btn_fullscreen.draw(surface)
        self.btn_back.draw(surface)

        # 2. 棋盘绘制
        last_mv = self.move_history[-1] if self.move_history else None
        show_hover = (
            self.hover_pos
            if (not self.is_game_over and self.current_turn == self.player_color)
            else None
        )
        self.board_view.draw(
            surface,
            self.board,
            last_move=last_mv,
            hover_pos=show_hover,
            current_turn=self.current_turn,
            winning_line=self.winning_line,
        )

        # 3. 右侧对弈状态面板
        panel_x = 780
        panel_w = 360

        # 对手卡片
        opp_card = Card((panel_x, 80, panel_w, 140))
        opp_card.draw(surface)
        opp_color_name = "黑方" if self.opponent_color == PieceColor.BLACK else "白方"
        opp_stone_color = (
            COLOR_STONE_BLACK
            if self.opponent_color == PieceColor.BLACK
            else COLOR_STONE_WHITE
        )
        opp_stone_border = (
            (80, 70, 60)
            if self.opponent_color == PieceColor.BLACK
            else (180, 170, 160)
        )

        pygame.draw.circle(surface, opp_stone_color, (panel_x + 36, 120), 16)
        pygame.draw.circle(surface, opp_stone_border, (panel_x + 36, 120), 16, width=1)

        font_name = get_font(18, bold=True)
        surface.blit(
            font_name.render(f"{self.opponent_name} ({opp_color_name})", True, COLOR_TEXT_MAIN),
            (panel_x + 64, 108),
        )
        font_tier = get_font(13)
        surface.blit(
            font_tier.render(f"段位: {self.opponent_rank}", True, COLOR_TEXT_MUTED),
            (panel_x + 64, 136),
        )

        # 局势提示看板
        status_card = Card((panel_x, 240, panel_w, 100), border_gold=True)
        status_card.draw(surface)

        is_my_turn = (self.current_turn == self.player_color)
        status_text = "轮到我方落子" if is_my_turn else f"{self.opponent_name} 正在思考着法..."
        status_color = COLOR_GREEN_JADE if is_my_turn else COLOR_GOLD_PRIMARY

        font_status = get_font(18, bold=True)
        st_surf = font_status.render(status_text, True, status_color)
        surface.blit(st_surf, (panel_x + 24, 260))

        font_moves = get_font(14)
        moves_msg = f"当前对局手数: 第 {len(self.move_history) + 1} 手"
        surface.blit(font_moves.render(moves_msg, True, COLOR_TEXT_MUTED), (panel_x + 24, 298))

        # 己方卡片
        my_card = Card((panel_x, 360, panel_w, 140))
        my_card.draw(surface)

        my_color_name = "黑方" if self.player_color == PieceColor.BLACK else "白方"
        my_stone_color = (
            COLOR_STONE_BLACK
            if self.player_color == PieceColor.BLACK
            else COLOR_STONE_WHITE
        )
        my_stone_border = (
            (80, 70, 60)
            if self.player_color == PieceColor.BLACK
            else (180, 170, 160)
        )

        pygame.draw.circle(surface, my_stone_color, (panel_x + 36, 400), 16)
        pygame.draw.circle(surface, my_stone_border, (panel_x + 36, 400), 16, width=1)

        surface.blit(
            font_name.render(f"{self.profile.username} ({my_color_name})", True, COLOR_TEXT_MAIN),
            (panel_x + 64, 388),
        )
        surface.blit(
            font_tier.render(f"当前段位: {self.profile.display_rank}", True, COLOR_GOLD_PRIMARY),
            (panel_x + 64, 416),
        )

        # 认输按钮
        self.btn_resign.draw(surface)

        # 4. 结算模态弹窗
        if self.settlement_dialog.is_visible:
            box = self.settlement_dialog.draw_backdrop(surface)

            is_win = (self.winner == self.player_color)
            if self.winner is None:
                title_txt = "双方握手言和"
                title_col = COLOR_TEXT_MUTED
            elif is_win:
                title_txt = "对局胜利"
                title_col = COLOR_GOLD_PRIMARY
            else:
                title_txt = "对局惜败"
                title_col = COLOR_TEXT_MUTED

            font_res_title = get_font(28, bold=True)
            res_surf = font_res_title.render(title_txt, True, title_col)
            surface.blit(res_surf, res_surf.get_rect(center=(box.centerx, box.y + 44)))

            font_sub = get_font(16)
            if self.mode == GameMode.RANKED and self.settlement_result:
                res = self.settlement_result
                star_str = f"天梯星数变动: {'+' if res.stars_delta >= 0 else ''}{res.stars_delta} 星"
                r_surf = font_sub.render(
                    f"{res.old_rank} -> {res.new_rank}",
                    True, COLOR_TEXT_MAIN
                )
                s_surf = font_sub.render(star_str, True, COLOR_GOLD_PRIMARY)
                surface.blit(r_surf, r_surf.get_rect(center=(box.centerx, box.y + 96)))
                surface.blit(s_surf, s_surf.get_rect(center=(box.centerx, box.y + 128)))

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
