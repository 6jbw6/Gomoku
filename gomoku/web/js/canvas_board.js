/**
 * 五子棋 15x15 Canvas 高清渲染引擎。
 * 
 * 特性：
 * 1. 自动适配高分屏（Retina DPR 缩放防模糊）；
 * 2. 真实木纹底色与天元星位绘制；
 * 3. 拟真立体光影黑白双色玉石棋子；
 * 4. 最后一步红印光环指示；
 * 5. 五子连珠高亮金色光带连线；
 * 6. 悬停半透明预落子光标。
 * 所有代码注释采用中文。
 */

class GomokuCanvasBoard {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Function} onCellClickCallback - 玩家点击棋盘交点触发回调 (x, y)
   */
  constructor(canvas, onCellClickCallback) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.onCellClick = onCellClickCallback;

    this.size = 15; // 15x15
    this.grid = []; // 当前 15x15 矩阵数据
    this.lastMove = null; // {x, y, color}
    this.winningLine = []; // [[x, y], ...]
    this.isMyTurn = false;
    this.myColor = 1; // 1黑 2白

    this.hoverCoord = null; // {x, y}
    this.padding = 32; // 边距留白（用于绘制坐标字符 A-O, 1-15）
    this.cellSize = 36;

    this.initBoardData();
    this.setupEvents();
    this.resize();
  }

  /**
   * 初始化空矩阵数据。
   */
  initBoardData() {
    this.grid = Array.from({ length: this.size }, () => Array(this.size).fill(0));
    this.lastMove = null;
    this.winningLine = [];
  }

  /**
   * 监听窗口缩放动态计算物理像素与尺寸。
   */
  resize() {
    // 根据容器或屏幕宽度自动缩放，保证移动端与桌面端完美自适应
    const containerWidth = Math.min(window.innerWidth - 48, 560);
    const displaySize = Math.max(320, containerWidth);

    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = displaySize * dpr;
    this.canvas.height = displaySize * dpr;
    this.canvas.style.width = `${displaySize}px`;
    this.canvas.style.height = `${displaySize}px`;

    this.ctx.scale(dpr, dpr);

    this.padding = displaySize * 0.07;
    this.cellSize = (displaySize - this.padding * 2) / (this.size - 1);

    this.render();
  }

  /**
   * 绑定鼠标与触摸事件。
   */
  setupEvents() {
    window.addEventListener('resize', () => this.resize());

    // 鼠标移动预选光标
    this.canvas.addEventListener('mousemove', (e) => {
      const coord = this.getGridCoordFromEvent(e);
      if (coord && this.isMyTurn && this.grid[coord.y][coord.x] === 0) {
        if (!this.hoverCoord || this.hoverCoord.x !== coord.x || this.hoverCoord.y !== coord.y) {
          this.hoverCoord = coord;
          this.render();
        }
      } else if (this.hoverCoord) {
        this.hoverCoord = null;
        this.render();
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      if (this.hoverCoord) {
        this.hoverCoord = null;
        this.render();
      }
    });

    // 点击落子
    this.canvas.addEventListener('click', (e) => {
      this.handleUserClick(e.clientX, e.clientY);
    });

    // 移动端触控落子支持
    this.canvas.addEventListener('touchend', (e) => {
      if (e.changedTouches && e.changedTouches.length > 0) {
        const touch = e.changedTouches[0];
        this.handleUserClick(touch.clientX, touch.clientY);
        e.preventDefault();
      }
    });
  }

  /**
   * 响应用户点击或触碰交点事件。
   */
  handleUserClick(clientX, clientY) {
    const coord = this.getGridCoordFromClientPos(clientX, clientY);
    if (coord && this.isMyTurn && this.grid[coord.y][coord.x] === 0) {
      if (typeof this.onCellClick === 'function') {
        this.onCellClick(coord.x, coord.y);
      }
    }
  }

  /**
   * 将屏幕视口像素坐标转换为棋盘网格整数索引 (0 到 14)。
   */
  getGridCoordFromClientPos(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;

    const x = Math.round((px - this.padding) / this.cellSize);
    const y = Math.round((py - this.padding) / this.cellSize);

    if (x >= 0 && x < this.size && y >= 0 && y < this.size) {
      return { x, y };
    }
    return null;
  }

  getGridCoordFromEvent(e) {
    return this.getGridCoordFromClientPos(e.clientX, e.clientY);
  }

  /**
   * 更新棋盘全量状态并触发重绘。
   */
  updateState(grid, lastMove, winningLine, isMyTurn, myColor) {
    this.grid = grid;
    this.lastMove = lastMove;
    this.winningLine = winningLine || [];
    this.isMyTurn = isMyTurn;
    this.myColor = myColor;
    this.render();
  }

  /**
   * 主渲染入口。
   */
  render() {
    const ctx = this.ctx;
    const displaySize = parseFloat(this.canvas.style.width) || 520;

    ctx.clearRect(0, 0, displaySize, displaySize);

    // 1. 绘制温润木质棋盘底色
    ctx.fillStyle = '#DDB26F';
    ctx.fillRect(0, 0, displaySize, displaySize);

    // 绘制自然木纹微细线条
    ctx.strokeStyle = 'rgba(84, 57, 22, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i < displaySize; i += 6) {
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(displaySize, i + Math.sin(i * 0.1) * 3);
      ctx.stroke();
    }

    // 2. 绘制 15x15 网格线与边框
    ctx.strokeStyle = '#543916';
    ctx.lineWidth = 1.2;

    for (let i = 0; i < this.size; i++) {
      const pos = this.padding + i * this.cellSize;

      // 横线
      ctx.beginPath();
      ctx.moveTo(this.padding, pos);
      ctx.lineTo(displaySize - this.padding, pos);
      ctx.stroke();

      // 竖线
      ctx.beginPath();
      ctx.moveTo(pos, this.padding);
      ctx.lineTo(pos, displaySize - this.padding);
      ctx.stroke();
    }

    // 绘制外围加粗边框
    ctx.lineWidth = 2.4;
    ctx.strokeRect(
      this.padding,
      this.padding,
      displaySize - this.padding * 2,
      displaySize - this.padding * 2
    );

    // 3. 绘制星位与天元 (天元 7,7 以及四个星角 3,3; 11,3; 3,11; 11,11)
    const starPoints = [
      [3, 3], [11, 3], [7, 7], [3, 11], [11, 11]
    ];
    ctx.fillStyle = '#543916';
    starPoints.forEach(([sx, sy]) => {
      const cx = this.padding + sx * this.cellSize;
      const cy = this.padding + sy * this.cellSize;
      ctx.beginPath();
      ctx.arc(cx, cy, 3.8, 0, Math.PI * 2);
      ctx.fill();
    });

    // 4. 绘制坐标标签 (A-O, 1-15)
    ctx.fillStyle = '#784D1A';
    ctx.font = `bold ${Math.max(10, Math.round(this.cellSize * 0.32))}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P'];
    for (let i = 0; i < this.size; i++) {
      const pos = this.padding + i * this.cellSize;
      // 顶部字母
      ctx.fillText(letters[i], pos, this.padding * 0.45);
      // 左侧数字
      ctx.fillText(String(15 - i), this.padding * 0.45, pos);
    }

    // 5. 绘制所有已落棋子
    const radius = this.cellSize * 0.44;
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const color = this.grid[y][x];
        if (color !== 0) {
          const cx = this.padding + x * this.cellSize;
          const cy = this.padding + y * this.cellSize;
          this.drawPiece(cx, cy, radius, color);
        }
      }
    }

    // 6. 绘制最后一步红印/金印标记
    if (this.lastMove) {
      const lx = this.padding + this.lastMove.x * this.cellSize;
      const ly = this.padding + this.lastMove.y * this.cellSize;
      ctx.beginPath();
      ctx.arc(lx, ly, radius * 0.3, 0, Math.PI * 2);
      ctx.fillStyle = '#DC2626'; // 朱砂红印
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#FAF7EE';
      ctx.stroke();
    }

    // 7. 绘制五子连珠胜利黄金连线
    if (this.winningLine && this.winningLine.length >= 5) {
      ctx.strokeStyle = '#F59E0B'; // 暖琥珀金
      ctx.lineWidth = 5;
      ctx.lineCap = 'round';
      ctx.shadowColor = 'rgba(212, 175, 55, 0.9)';
      ctx.shadowBlur = 12;

      ctx.beginPath();
      const first = this.winningLine[0];
      ctx.moveTo(this.padding + first[0] * this.cellSize, this.padding + first[1] * this.cellSize);

      for (let i = 1; i < this.winningLine.length; i++) {
        const pt = this.winningLine[i];
        ctx.lineTo(this.padding + pt[0] * this.cellSize, this.padding + pt[1] * this.cellSize);
      }
      ctx.stroke();
      ctx.shadowBlur = 0; // 重置阴影
    }

    // 8. 绘制预选落子半透明虚影
    if (this.hoverCoord && this.isMyTurn) {
      const hx = this.padding + this.hoverCoord.x * this.cellSize;
      const hy = this.padding + this.hoverCoord.y * this.cellSize;
      ctx.save();
      ctx.globalAlpha = 0.45;
      this.drawPiece(hx, hy, radius, this.myColor);
      ctx.restore();
    }
  }

  /**
   * 绘制具有球体质感与漫反射环境阴影的棋子。
   */
  drawPiece(x, y, r, color) {
    const ctx = this.ctx;

    // 投影
    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.45)';
    ctx.shadowBlur = 8;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 4;

    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);

    if (color === 1) {
      // 黑子：黑曜石质感球体渐变
      const grad = ctx.createRadialGradient(
        x - r * 0.35, y - r * 0.35, r * 0.1,
        x, y, r
      );
      grad.addColorStop(0, '#555555');
      grad.addColorStop(0.3, '#2A2A2A');
      grad.addColorStop(1, '#0C0C0C');
      ctx.fillStyle = grad;
    } else {
      // 白子：羊脂白玉质感球体渐变
      const grad = ctx.createRadialGradient(
        x - r * 0.35, y - r * 0.35, r * 0.1,
        x, y, r
      );
      grad.addColorStop(0, '#FFFFFF');
      grad.addColorStop(0.65, '#EDE7D8');
      grad.addColorStop(1, '#C9BEA7');
      ctx.fillStyle = grad;
    }

    ctx.fill();
    ctx.restore();
  }
}

window.GomokuCanvasBoard = GomokuCanvasBoard;
