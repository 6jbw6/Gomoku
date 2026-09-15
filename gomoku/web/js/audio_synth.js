/**
 * 五子棋原生音频合成引擎模块（纯 Web Audio API 实现）。
 * 
 * 无需下载任何外部 mp3/wav 静态文件，直接利用物理振荡器与噪声滤波器
 * 高保真合成清脆木石落子敲击声、步时倒计时滴答声与胜负鸣钟声。
 * 所有代码注释采用中文。
 */

class SoundSynthesizer {
  constructor() {
    this.audioCtx = null;
    this.isMuted = false;
  }

  /**
   * 延迟初始化 AudioContext（遵守现代浏览器用户手势激活规范）。
   */
  initContext() {
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  /**
   * 切换全局静音状态。
   * @returns {boolean} 当前是否静音
   */
  toggleMute() {
    this.isMuted = !this.isMuted;
    return this.isMuted;
  }

  /**
   * 播放逼真棋子敲击棋盘音效（木石碰撞瞬态冲击合成）。
   */
  playStoneClick() {
    if (this.isMuted) return;
    this.initContext();
    if (!this.audioCtx) return;

    const ctx = this.audioCtx;
    const now = ctx.currentTime;

    // 1. 低频木质共振振荡器（800Hz 快速衰减至 150Hz）
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(750, now);
    osc.frequency.exponentialRampToValueAtTime(140, now + 0.04);

    gainNode.gain.setValueAtTime(0.7, now);
    gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

    osc.connect(gainNode);
    gainNode.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.09);

    // 2. 高频玉石触碰清脆瞬态脉冲（白噪声高通滤波）
    const bufferSize = ctx.sampleRate * 0.02; // 20ms
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const output = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }

    const whiteNoise = ctx.createBufferSource();
    whiteNoise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 2400;
    filter.Q.value = 3.0;

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.5, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.025);

    whiteNoise.connect(filter);
    filter.connect(noiseGain);
    noiseGain.connect(ctx.destination);

    whiteNoise.start(now);
  }

  /**
   * 倒计时临界滴答提示音（高亢短促木鱼声）。
   */
  playTimerTick() {
    if (this.isMuted) return;
    this.initContext();
    if (!this.audioCtx) return;

    const ctx = this.audioCtx;
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(1200, now);
    osc.frequency.exponentialRampToValueAtTime(800, now + 0.03);

    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.035);
  }

  /**
   * 胜局金鼓鸣奏华彩音。
   */
  playWinChord() {
    if (this.isMuted) return;
    this.initContext();
    if (!this.audioCtx) return;

    const ctx = this.audioCtx;
    const now = ctx.currentTime;
    // 宫商角徵羽五声音阶和弦 (C5, D5, E5, G5, A5)
    const notes = [523.25, 659.25, 783.99, 1046.50];

    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.value = freq;

      const startTime = now + idx * 0.08;
      gain.gain.setValueAtTime(0.2, startTime);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.6);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(startTime + 0.65);
    });
  }
}

// 导出全局单例
window.soundSynth = new SoundSynthesizer();
