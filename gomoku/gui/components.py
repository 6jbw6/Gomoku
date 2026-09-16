"""五子棋桌面端通用 UI 组件库。

提供国风金石按钮、卡片、模态弹窗与进度条组件。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import sys
from typing import Callable, List, Optional, Tuple
import pygame
from gomoku.gui.constants import (
    COLOR_BORDER_DIM,
    COLOR_CARD_BG,
    COLOR_CARD_HOVER,
    COLOR_GOLD_BORDER,
    COLOR_GOLD_HOVER,
    COLOR_GOLD_PRIMARY,
    COLOR_PANEL_BG,
    COLOR_RED_CRIMSON,
    COLOR_TEXT_MAIN,
)

# 字体缓存字典
_FONT_CACHE: dict = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """获取中文渲染字体（优先使用系统雅黑或黑体）。"""
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    font_names = ["microsoftyahei", "simhei", "pingfangsc", "arial"]
    font = pygame.font.SysFont(font_names, size, bold=bold)
    _FONT_CACHE[key] = font
    return font


def _win_clipboard_put(text: str) -> bool:
    """经 Windows 原生接口将 UTF-16 文本写入系统剪贴板。"""
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    # 64 位下句柄为指针宽度，必须显式声明返回类型防止截断
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]

    cf_unicode_text = 13
    gmem_moveable = 0x0002
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return False
        try:
            ctypes.memmove(ptr, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(cf_unicode_text, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def _win_clipboard_get() -> str:
    """经 Windows 原生接口读取系统剪贴板 UTF-16 文本。"""
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

    cf_unicode_text = 13
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(cf_unicode_text)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def clipboard_put_text(text: str) -> bool:
    """将文本写入系统剪贴板（Windows 原生接口，失败静默返回 False）。"""
    try:
        if sys.platform == "win32":
            return _win_clipboard_put(text)
        import pygame.scrap
        if not pygame.scrap.get_init():
            return False
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
        return True
    except Exception:
        return False


def clipboard_get_text() -> str:
    """读取系统剪贴板文本并仅保留半角字母与数字（失败返回空串）。

    房间码为纯半角字母数字，此处过滤掉粘贴文本中的空格、
    换行、汉字与全角字符等干扰内容，便于直接粘贴好友发来的房间码。
    """
    try:
        if sys.platform == "win32":
            text = _win_clipboard_get()
        else:
            import pygame.scrap
            if not pygame.scrap.get_init():
                return ""
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if raw is None:
                return ""
            text = raw.decode("utf-8", errors="ignore") if isinstance(
                raw, bytes
            ) else str(raw)
    except Exception:
        return ""
    return "".join(
        c for c in text.upper() if ("A" <= c <= "Z" or "0" <= c <= "9")
    )


class Button:
    """国风雅致按钮组件，支持悬浮过渡与点击回调。"""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        text: str,
        style: str = "gold",
        on_click: Optional[Callable[[], None]] = None,
        font_size: int = 18,
    ) -> None:
        """初始化按钮规格。"""
        self.rect = pygame.Rect(rect)
        self.text = text
        self.style = style
        self.on_click = on_click
        self.font_size = font_size
        self.is_hovered: bool = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理鼠标事件，被点击时返回 True。"""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """绘制按钮图形与文字。"""
        # 根据风格判定色系（严格禁止蓝紫色系）
        if self.style == "gold":
            bg_color = COLOR_GOLD_HOVER if self.is_hovered else COLOR_GOLD_PRIMARY
            border_color = (255, 215, 0) if self.is_hovered else COLOR_GOLD_BORDER
            text_color = (22, 20, 18)
        elif self.style == "danger":
            bg_color = (185, 28, 28) if self.is_hovered else COLOR_RED_CRIMSON
            border_color = (248, 113, 113) if self.is_hovered else (153, 27, 27)
            text_color = COLOR_TEXT_MAIN
        else:  # secondary
            bg_color = (52, 45, 40) if self.is_hovered else (38, 33, 29)
            border_color = COLOR_GOLD_PRIMARY if self.is_hovered else COLOR_BORDER_DIM
            text_color = COLOR_GOLD_PRIMARY if self.is_hovered else COLOR_TEXT_MAIN

        # 绘制按钮圆角主体与高光边框
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, border_color, self.rect, width=1, border_radius=8)

        # 绘制居中文本
        font = get_font(self.font_size, bold=True)
        txt_surf = font.render(self.text, True, text_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)


class Card:
    """半透明沉香木质卡片面板组件。"""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        border_gold: bool = False,
        clickable: bool = False,
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        """初始化卡片几何规格。"""
        self.rect = pygame.Rect(rect)
        self.border_gold = border_gold
        self.clickable = clickable
        self.on_click = on_click
        self.is_hovered: bool = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理悬浮与点击交互。"""
        if not self.clickable:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """绘制带半透明质感的圆角卡片。"""
        card_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        bg_color = COLOR_CARD_HOVER if (self.clickable and self.is_hovered) else COLOR_CARD_BG
        pygame.draw.rect(
            card_surf, bg_color, (0, 0, self.rect.width, self.rect.height), border_radius=12
        )
        surface.blit(card_surf, self.rect.topleft)

        border_color = (
            COLOR_GOLD_PRIMARY
            if (self.is_hovered or self.border_gold)
            else COLOR_BORDER_DIM
        )
        border_width = 2 if (self.is_hovered or self.border_gold) else 1
        pygame.draw.rect(surface, border_color, self.rect, width=border_width, border_radius=12)


class ProgressBar:
    """勇者积分进度条组件。"""

    def __init__(self, rect: Tuple[int, int, int, int]) -> None:
        """初始化进度条位置。"""
        self.rect = pygame.Rect(rect)

    def draw(self, surface: pygame.Surface, current: int, max_val: int) -> None:
        """绘制底槽与琥珀金进度填充。"""
        ratio = max(0.0, min(1.0, current / max(1, max_val)))
        # 底槽
        pygame.draw.rect(surface, (20, 18, 16), self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER_DIM, self.rect, width=1, border_radius=6)
        # 填充
        if ratio > 0.0:
            fill_w = int((self.rect.width - 2) * ratio)
            fill_rect = pygame.Rect(
                self.rect.x + 1, self.rect.y + 1, fill_w, self.rect.height - 2
            )
            pygame.draw.rect(surface, COLOR_GOLD_PRIMARY, fill_rect, border_radius=5)


class ModalDialog:
    """全局模态弹窗，覆盖全屏半透明遮罩，居中展示卡片。"""

    def __init__(self, width: int = 500, height: int = 380) -> None:
        """初始化居中弹窗规格。"""
        self.width = width
        self.height = height
        self.is_visible: bool = False
        self.buttons: List[Button] = []

    def show(self) -> None:
        """显示弹窗。"""
        self.is_visible = True

    def hide(self) -> None:
        """关闭弹窗。"""
        self.is_visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """分发弹窗内交互，阻止外部事件穿透。"""
        if not self.is_visible:
            return False
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        # 拦截点击事件，防止穿透到底层界面
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return True
        return False

    def draw_backdrop(self, surface: pygame.Surface) -> pygame.Rect:
        """绘制覆盖全屏的半透明深色蒙层并返回居中矩形。"""
        w, h = surface.get_size()
        dim_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 190))
        surface.blit(dim_surf, (0, 0))

        # 计算绝对居中卡片位置
        center_x = (w - self.width) // 2
        center_y = (h - self.height) // 2
        box_rect = pygame.Rect(center_x, center_y, self.width, self.height)

        # 绘制主弹窗卡片与高光金边
        pygame.draw.rect(surface, COLOR_PANEL_BG, box_rect, border_radius=16)
        pygame.draw.rect(surface, COLOR_GOLD_BORDER, box_rect, width=2, border_radius=16)

        return box_rect


class TextInput:
    """国风单行文本输入框，专用于房间码输入等交互场景。"""

    # 小键盘数字键码到字符的映射（主键盘字母数字由区间比较兜底）
    _KP_DIGITS: dict = {
        pygame.K_KP0: "0", pygame.K_KP1: "1", pygame.K_KP2: "2",
        pygame.K_KP3: "3", pygame.K_KP4: "4", pygame.K_KP5: "5",
        pygame.K_KP6: "6", pygame.K_KP7: "7", pygame.K_KP8: "8",
        pygame.K_KP9: "9",
    }

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        placeholder: str = "请输入6位房间码",
        max_length: int = 6,
        font_size: int = 20,
    ) -> None:
        """初始化输入框参数。"""
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.max_length = max_length
        self.font_size = font_size
        self.text: str = ""
        self.is_active: bool = False
        # 本次 KEYDOWN 已录入的字符（TEXTINPUT 紧随其后时据此去重）
        self._keydown_pending: str = ""

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理键盘输入与焦点切换事件。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_active = self.rect.collidepoint(event.pos)
            return self.is_active
        if (
            self.is_active
            and event.type == pygame.TEXTINPUT
            and hasattr(event, "text")
        ):
            # 文本输入通道兜底：KEYDOWN 的键码与 unicode 均被
            # 输入法深度拦截丢失时，TEXTINPUT 仍可能携带字符；
            # 紧随 KEYDOWN 而来时若 KEYDOWN 已录入则跳过防重复
            if not self._keydown_pending:
                for ch in event.text:
                    ch = ch.upper()
                    if len(self.text) < self.max_length and (
                        "A" <= ch <= "Z" or "0" <= ch <= "9"
                    ):
                        self.text += ch
            self._keydown_pending = ""
            return True
        if self.is_active and event.type == pygame.KEYDOWN:
            key_mod = getattr(event, "mod", 0)
            self._keydown_pending = ""
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return True
            elif key_mod & pygame.KMOD_CTRL and event.key == pygame.K_v:
                # 粘贴：从系统剪贴板过滤出字母数字并补齐至满位
                pasted = clipboard_get_text()
                if pasted:
                    self.text = (self.text + pasted)[: self.max_length]
                return True
            elif key_mod & pygame.KMOD_CTRL and event.key == pygame.K_c:
                # 复制：将输入框现有内容写入系统剪贴板
                clipboard_put_text(self.text)
                return True
            elif len(self.text) < self.max_length:
                ch = self._resolve_input_char(event)
                if ch:
                    self.text += ch
                    self._keydown_pending = ch
                    return True
        return False

    @classmethod
    def _resolve_input_char(cls, event: pygame.event.Event) -> str:
        """从键盘事件解析一个合法的半角字母或数字字符。

        中文输入法占用系统文本输入通道时，KEYDOWN 事件的 unicode
        字段可能为空（按键被输入法拦截进入组字状态），此时依据
        虚拟键码兜底识别字母与数字，保证机房等中文输入环境下
        房间码仍可正常输入；同时仅接受半角字母数字，防止输入法
        上屏的汉字等全角字符混入房间码。
        """
        ch = ""
        if event.unicode:
            ch = event.unicode.upper()
        elif pygame.K_a <= event.key <= pygame.K_z:
            ch = chr(ord("A") + event.key - pygame.K_a)
        elif pygame.K_0 <= event.key <= pygame.K_9:
            ch = chr(ord("0") + event.key - pygame.K_0)
        else:
            ch = cls._KP_DIGITS.get(event.key, "")
        if len(ch) == 1 and ("A" <= ch <= "Z" or "0" <= ch <= "9"):
            return ch
        return ""

    def draw(self, surface: pygame.Surface) -> None:
        """绘制带金石高光的输入框。"""
        pygame.draw.rect(surface, (20, 18, 16), self.rect, border_radius=8)
        border_color = COLOR_GOLD_PRIMARY if self.is_active else COLOR_BORDER_DIM
        border_width = 2 if self.is_active else 1
        pygame.draw.rect(surface, border_color, self.rect, width=border_width, border_radius=8)

        font = get_font(self.font_size, bold=True)
        if self.text:
            spaced_text = "  ".join(list(self.text))
            txt_surf = font.render(spaced_text, True, COLOR_GOLD_PRIMARY)
        else:
            txt_surf = font.render(self.placeholder, True, (120, 110, 100))

        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)
