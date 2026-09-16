"""五子棋桌面端 Pygame 核心应用主程序。

统一调度窗口生命周期、背景图层渲染、事件分发与场景流转。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import os
import sys
import threading
from typing import Any, Optional
import pygame
from gomoku.core.enums import GameMode, PieceColor
from gomoku.gui.audio import SoundManager
from gomoku.gui.constants import (
    COLOR_BG_DARK,
    FPS,
    TITLE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from gomoku.gui.profile import UserProfileManager
from gomoku.gui.scenes import GameScene, LobbyScene


class GomokuApp:
    """五子棋桌面端应用程序总控类。"""

    def __init__(self) -> None:
        """初始化 Pygame 引擎、窗口、音效与档案管理器。"""
        pygame.init()
        # 关闭文本输入模式，解除窗口与输入法（IME）的关联：
        # 否则中文输入法开启时，小写字母按键会被组字状态拦截，
        # 导致 KEYDOWN 的键码与 unicode 均丢失而无法输入房间码
        # （开启大写锁定才可输入的现象即源于此）。
        # 按键由事件键码直接识别，游戏窗口无需输入法参与。
        pygame.key.stop_text_input()
        pygame.display.set_caption(TITLE)

        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED
        )
        self.clock = pygame.time.Clock()
        self.is_running: bool = True

        # 设置窗口小图标与前置激活
        self._set_app_icon()
        self._bring_to_foreground()

        # 音频与档案子系统
        self.sound_mgr = SoundManager()
        self.profile_mgr = UserProfileManager()

        # 加载与缩放沉香茶室雅境背景图
        self.bg_surface: Optional[pygame.Surface] = self._load_and_prepare_background()
        # 对局页提亮版背景：暖色加法提亮，缓解全局遮罩的暗沉
        self.bg_surface_game: Optional[pygame.Surface] = None
        if self.bg_surface is not None:
            bright = self.bg_surface.copy()
            bright.fill((34, 30, 24), special_flags=pygame.BLEND_RGB_ADD)
            self.bg_surface_game = bright

        # 场景状态机
        self.current_scene: str = "lobby"
        self.lobby_scene = LobbyScene(
            self.profile_mgr,
            self.sound_mgr,
            on_start_game=self.start_game,
        )
        self.game_scene: Optional[GameScene] = None

        # 后台预热局域网主机发现：UDP 广播探测约需 1 秒，
        # 若在主线程同步执行（点击匹配/建房时）将冻结界面导致
        # 点击丢失；启动即后台解析并缓存，后续连接零阻塞
        from gomoku.gui.room_net import resolve_room_host

        threading.Thread(target=resolve_room_host, daemon=True).start()

    def _bring_to_foreground(self) -> None:
        """若在 Windows 系统下运行，强制将窗口前置并获取交互焦点。"""
        if sys.platform != "win32":
            return
        try:
            wm_info = pygame.display.get_wm_info()
            hwnd = wm_info.get("window")
            if hwnd:
                import ctypes
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, 5)  # SW_SHOW
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _set_app_icon(self) -> None:
        """动态生成黑曜石棋子图标并注入窗口。"""
        icon_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon_surf, (22, 20, 18), (16, 16), 14)
        pygame.draw.circle(icon_surf, (212, 175, 55), (16, 16), 14, width=2)
        pygame.draw.circle(icon_surf, (80, 75, 70), (12, 12), 5)
        pygame.display.set_icon(icon_surf)

    @staticmethod
    def _load_and_prepare_background() -> Optional[pygame.Surface]:
        """加载雅室背景图并应用高透东方暖炭黑遮罩。"""
        bg_path = os.path.join(
            os.path.dirname(__file__), "assets", "theme_bg.jpg"
        )
        if not os.path.exists(bg_path):
            return None

        try:
            raw_bg = pygame.image.load(bg_path).convert()
            scaled_bg = pygame.transform.smoothscale(
                raw_bg, (WINDOW_WIDTH, WINDOW_HEIGHT)
            )

            # 叠加明亮通透暖色滤镜遮罩
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((22, 20, 18, 45))
            scaled_bg.blit(overlay, (0, 0))
            return scaled_bg
        except Exception as err:
            print(f"[背景加载提示] 无法载入背景图，采用默认炭黑底色: {err}")
            return None

    def start_game(
        self,
        mode: GameMode,
        title: str,
        opponent_name: str = "弈心棋友",
        opponent_rank: str = "初入棋道",
        player_color: PieceColor = PieceColor.BLACK,
        room_client: Any = None,
    ) -> None:
        """从大厅进入对局场景。"""
        self.game_scene = GameScene(
            mode=mode,
            title=title,
            profile_mgr=self.profile_mgr,
            sound_mgr=self.sound_mgr,
            on_exit=self.back_to_lobby,
            opponent_name=opponent_name,
            opponent_rank=opponent_rank,
            player_color=player_color,
            room_client=room_client,
        )
        self.current_scene = "game"

    def back_to_lobby(self) -> None:
        """从对局场景返回大厅并刷新档案。"""
        self.current_scene = "lobby"
        self.game_scene = None

    def run(self) -> None:
        """主游戏循环，驱动 60 帧刷新、事件处理与场景渲染。"""
        first_frame: bool = True
        while self.is_running:
            # 1. 全局事件分发
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                    break
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.current_scene == "game":
                            self.back_to_lobby()

                # 分发给当前活跃场景
                if self.current_scene == "lobby":
                    self.lobby_scene.handle_event(event)
                elif self.current_scene == "game" and self.game_scene:
                    self.game_scene.handle_event(event)

            # 2. 逻辑更新（大厅需驱动匹配撮合与房间事件轮询）
            if self.current_scene == "lobby":
                self.lobby_scene.update()
            elif self.current_scene == "game" and self.game_scene:
                self.game_scene.update()

            # 3. 画面渲染（对局页使用提亮版背景）
            game_bg = (
                self.current_scene == "game" and self.game_scene
            )
            bg = self.bg_surface_game if game_bg else self.bg_surface
            if bg is not None:
                self.screen.blit(bg, (0, 0))
            else:
                self.screen.fill(COLOR_BG_DARK)

            if self.current_scene == "lobby":
                self.lobby_scene.draw(self.screen)
            elif self.current_scene == "game" and self.game_scene:
                self.game_scene.draw(self.screen)

            # 4. 刷新屏幕
            pygame.display.flip()
            if first_frame:
                self._bring_to_foreground()
                first_frame = False
            self.clock.tick(FPS)

        # 退出清理
        pygame.quit()
        sys.exit(0)
