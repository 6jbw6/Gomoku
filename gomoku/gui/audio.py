"""五子棋桌面端音频音效管理器。

采用纯数学波形算法动态合成东方金石落子声与国风五音提示音，零外部音效文件依赖。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import io
import math
import os
import struct
import wave
from typing import Optional
import pygame


class SoundManager:
    """音频音效管理器，负责落子声波合成与播放调度。"""

    def __init__(self) -> None:
        """初始化音频子系统与合成缓存（快速探测，杜绝无声卡环境卡顿）。"""
        self.enabled: bool = False
        self.stone_sound: Optional[pygame.mixer.Sound] = None
        self.click_sound: Optional[pygame.mixer.Sound] = None
        self.win_sound: Optional[pygame.mixer.Sound] = None
        self.loss_sound: Optional[pygame.mixer.Sound] = None

        self._init_mixer()
        if pygame.mixer.get_init():
            self._synthesize_all_sounds()
            self.enabled = True

    def _init_mixer(self) -> None:
        """初始化 Pygame 混音器（优先 directsound，无设备时秒级回退 dummy 驱动）。"""
        if "SDL_AUDIODRIVER" not in os.environ:
            os.environ["SDL_AUDIODRIVER"] = "directsound"

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            try:
                os.environ["SDL_AUDIODRIVER"] = "dummy"
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception as err:
                print(f"[音频初始化提示] 当前环境无可用音频设备: {err}")

    def toggle(self) -> bool:
        """切换音效启用状态并返回当前状态。"""
        self.enabled = not self.enabled
        return self.enabled

    def play_stone(self) -> None:
        """播放温润落子脆响。"""
        if self.enabled and self.stone_sound:
            self.stone_sound.play()

    def play_click(self) -> None:
        """播放界面轻微点击音。"""
        if self.enabled and self.click_sound:
            self.click_sound.play()

    def play_win(self) -> None:
        """播放获胜清雅五音音律。"""
        if self.enabled and self.win_sound:
            self.win_sound.play()

    def play_loss(self) -> None:
        """播放对局战败低缓音。"""
        if self.enabled and self.loss_sound:
            self.loss_sound.play()

    def _synthesize_all_sounds(self) -> None:
        """在内存中合成所有音效 WAV 数据并加载为 Sound 对象。"""
        try:
            self.stone_sound = self._create_stone_sound()
            self.click_sound = self._create_click_sound()
            self.win_sound = self._create_win_sound()
            self.loss_sound = self._create_loss_sound()
        except Exception as err:
            print(f"[音效合成警告] 音频波形生成失败: {err}")

    @staticmethod
    def _create_stone_sound() -> pygame.mixer.Sound:
        """合成真实的沉香木盘落子音（瞬态敲击与木纹衰减谐振）。"""
        sample_rate: int = 44100
        duration: float = 0.16
        total_samples: int = int(sample_rate * duration)
        raw_bytes: bytearray = bytearray()

        for i in range(total_samples):
            t: float = i / sample_rate
            # 瞬态高频敲击波 (2200 Hz) + 木盘沉香回响 (260 Hz)
            env_high: float = math.exp(-t * 85.0)
            env_low: float = math.exp(-t * 26.0)
            wave_val: float = (
                0.55 * math.sin(2.0 * math.pi * 2200.0 * t) * env_high
                + 0.45 * math.sin(2.0 * math.pi * 260.0 * t) * env_low
            )
            sample: int = max(-32767, min(32767, int(wave_val * 32767.0)))
            raw_bytes.extend(struct.pack("<hh", sample, sample))

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)
        buf.seek(0)
        return pygame.mixer.Sound(buf)

    @staticmethod
    def _create_click_sound() -> pygame.mixer.Sound:
        """合成按键短促木质点击音。"""
        sample_rate: int = 44100
        duration: float = 0.04
        total_samples: int = int(sample_rate * duration)
        raw_bytes: bytearray = bytearray()

        for i in range(total_samples):
            t: float = i / sample_rate
            env: float = math.exp(-t * 120.0)
            wave_val: float = math.sin(2.0 * math.pi * 1200.0 * t) * env * 0.4
            sample: int = int(wave_val * 32767.0)
            raw_bytes.extend(struct.pack("<hh", sample, sample))

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)
        buf.seek(0)
        return pygame.mixer.Sound(buf)

    @staticmethod
    def _create_win_sound() -> pygame.mixer.Sound:
        """合成获胜宫商角徵羽国风上升旋律。"""
        sample_rate: int = 44100
        notes = [523.25, 587.33, 659.25, 783.99, 1046.50]  # C5, D5, E5, G5, C6
        note_dur: float = 0.09
        raw_bytes: bytearray = bytearray()

        for idx, freq in enumerate(notes):
            n_samples = int(sample_rate * note_dur)
            for i in range(n_samples):
                t = i / sample_rate
                env = math.sin(math.pi * (i / n_samples))
                wave_val = math.sin(2.0 * math.pi * freq * t) * env * 0.45
                sample = int(wave_val * 32767.0)
                raw_bytes.extend(struct.pack("<hh", sample, sample))

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)
        buf.seek(0)
        return pygame.mixer.Sound(buf)

    @staticmethod
    def _create_loss_sound() -> pygame.mixer.Sound:
        """合成对局惜败低音弦律。"""
        sample_rate: int = 44100
        notes = [440.0, 392.0, 329.63]  # A4, G4, E4
        note_dur: float = 0.16
        raw_bytes: bytearray = bytearray()

        for freq in notes:
            n_samples = int(sample_rate * note_dur)
            for i in range(n_samples):
                t = i / sample_rate
                env = math.exp(-t * 9.0)
                wave_val = math.sin(2.0 * math.pi * freq * t) * env * 0.4
                sample = int(wave_val * 32767.0)
                raw_bytes.extend(struct.pack("<hh", sample, sample))

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)
        buf.seek(0)
        return pygame.mixer.Sound(buf)
