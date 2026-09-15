/**
 * 前端核心应用状态机与控制器模块。
 * 
 * 协调用户鉴权、页面路由、长连接信令、棋盘渲染、落子交互与天梯结算呈现。
 * 所有代码注释采用中文。
 */

document.addEventListener('DOMContentLoaded', async () => {
  // 核心实例引用
  const wsClient = new GomokuWebSocketClient();
  let canvasBoard = null;

  // 用户与当前房间会话状态
  let currentUser = null;
  let currentRoomId = null;
  let currentRoomState = null;
  let timerInterval = null;

  // 获取页面 DOM 元素
  const lobbyView = document.getElementById('lobby-view');
  const gameView = document.getElementById('game-view');
  const userNicknameEl = document.getElementById('user-nickname');
  const userRankBadgeEl = document.getElementById('user-rank-badge');
  const userStarsRowEl = document.getElementById('user-stars-row');
  const userBraveTextEl = document.getElementById('user-brave-text');
  const userBraveBarEl = document.getElementById('user-brave-bar');
  const winRateTextEl = document.getElementById('user-win-rate');

  // 模态弹窗元素
  const matchModal = document.getElementById('match-modal');
  const matchModeTitle = document.getElementById('match-mode-title');
  const friendModal = document.getElementById('friend-modal');
  const leaderboardModal = document.getElementById('leaderboard-modal');
  const settlementModal = document.getElementById('settlement-modal');

  /**
   * 1. 自动游客免密登录与档案加载
   */
  async function initAuth() {
    let token = localStorage.getItem('gomoku_token');
    if (!token) {
      try {
        const res = await fetch('/api/auth/guest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        const data = await res.json();
        token = data.access_token;
        localStorage.setItem('gomoku_token', token);
      } catch (err) {
        console.error('游客登录失败:', err);
      }
    }

    await loadUserProfile(token);
    wsClient.connect(token);
  }

  /**
   * 加载当前玩家个人资料与段位信息。
   */
  async function loadUserProfile(token) {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        currentUser = await res.json();
        renderUserProfile();
      } else {
        // 令牌可能失效，清空重登
        localStorage.removeItem('gomoku_token');
        initAuth();
      }
    } catch (err) {
      console.warn('获取玩家资料异常:', err);
    }
  }

  /**
   * 渲染用户顶部状态栏。
   */
  function renderUserProfile() {
    if (!currentUser) return;
    userNicknameEl.textContent = currentUser.username;
    userRankBadgeEl.textContent = currentUser.display_rank;

    const theme = RankUIHelper.getTierTheme(currentUser.tier);
    userRankBadgeEl.style.background = theme.badgeBg;
    userRankBadgeEl.style.color = theme.textColor;
    userRankBadgeEl.style.border = `1px solid ${theme.border}`;

    const cap = RankUIHelper.getBravePointsCap(currentUser.tier);
    const maxStars = currentUser.tier.includes('青铜') || currentUser.tier.includes('白银') ? 3 : (currentUser.tier.includes('黄金') || currentUser.tier.includes('铂金') ? 4 : 5);
    userStarsRowEl.innerHTML = RankUIHelper.renderStars(currentUser.tier, currentUser.sub_tier, currentUser.stars, maxStars);

    userBraveTextEl.textContent = `${currentUser.brave_points} / ${cap}`;
    const percent = Math.min(100, Math.round((currentUser.brave_points / cap) * 100));
    userBraveBarEl.style.width = `${percent}%`;

    winRateTextEl.textContent = `胜率: ${currentUser.win_rate}% (${currentUser.win_matches}/${currentUser.total_matches}场) | 连胜: ${currentUser.winning_streak}`;
  }

  /**
   * 2. 初始化 15x15 棋盘
   */
  const canvasEl = document.getElementById('gomoku-canvas');
  canvasBoard = new GomokuCanvasBoard(canvasEl, (x, y) => {
    // 触发玩家落子信令
    if (!currentRoomId || !currentRoomState) return;
    wsClient.send('move', currentRoomId, { x, y });
    window.soundSynth.playStoneClick();
  });

  /**
   * 3. 视图切换调度
   */
  function switchView(viewName) {
    if (viewName === 'lobby') {
      lobbyView.classList.add('active');
      gameView.classList.remove('active');
      currentRoomId = null;
      currentRoomState = null;
      stopTimerCountdown();
    } else if (viewName === 'game') {
      lobbyView.classList.remove('active');
      gameView.classList.add('active');
      canvasBoard.resize();
    }
  }

  /**
   * 4. WebSocket 业务消息事件监听
   */
  wsClient.on('match_status', (data) => {
    if (data.status === 'searching') {
      matchModeTitle.textContent = data.mode === 'ranked' ? '天梯排位赛匹配中...' : '单人休闲对局匹配中...';
      matchModal.classList.add('show');
    } else if (data.status === 'cancelled') {
      matchModal.classList.remove('show');
    }
  });

  wsClient.on('match_success', (data) => {
    matchModal.classList.remove('show');
    currentRoomId = data.room_id;
    currentRoomState = data.room_state;
    switchView('game');
    updateGameRoomUI();
  });

  wsClient.on('room_state', (state) => {
    currentRoomState = state;
    currentRoomId = state.room_id;
    switchView('game');
    updateGameRoomUI();
  });

  wsClient.on('game_over', (payload) => {
    stopTimerCountdown();
    if (currentRoomState) {
      currentRoomState.status = 'finished';
      currentRoomState.winner = payload.winner;
      currentRoomState.win_reason = payload.win_reason;
      currentRoomState.winning_line = payload.winning_line || [];
      updateGameRoomUI();
    }
    if (currentRoomState && currentUser) {
      const myColor = getMyColorInRoom();
      const isWinner = payload.winner === myColor;
      if (isWinner) {
        window.soundSynth.playWinChord();
      }

      // 非排位赛（休闲与好友房间）直接弹出终局结算卡片
      if (currentRoomState.mode !== 'ranked') {
        showCasualGameOverModal(isWinner, payload.win_reason);
      }
    }
  });

  wsClient.on('rank_settled', (settlement) => {
    showSettlementModal(settlement);
    // 重新拉取最新段位数据
    loadUserProfile(localStorage.getItem('gomoku_token'));
  });

  wsClient.on('error', (payload) => {
    alert(payload.message || '操作异常');
  });

  /**
   * 判断当前玩家在房间中的执子颜色（1黑 2白 0观战）。
   */
  function getMyColorInRoom() {
    if (!currentRoomState || !currentUser) return 0;
    if (currentRoomState.black_player && currentRoomState.black_player.player_id === currentUser.user_id) {
      return 1;
    }
    if (currentRoomState.white_player && currentRoomState.white_player.player_id === currentUser.user_id) {
      return 2;
    }
    return 0;
  }

  /**
   * 刷新房间内界面与棋盘渲染
   */
  function updateGameRoomUI() {
    if (!currentRoomState) return;

    const myColor = getMyColorInRoom();
    const isMyTurn = currentRoomState.status === 'playing' && currentRoomState.current_turn === myColor;

    // 更新棋盘
    canvasBoard.updateState(
      currentRoomState.board,
      currentRoomState.last_move,
      currentRoomState.winning_line,
      isMyTurn,
      myColor === 0 ? 1 : myColor
    );

    // 更新房间号与模式标签
    const modeNameMap = { friend: '好友对局', casual: '单人匹配', ranked: '天梯排位赛' };
    document.getElementById('game-room-tag').textContent = `${modeNameMap[currentRoomState.mode] || '对局'} (房间码: ${currentRoomState.room_id})`;

    // 更新黑方信息卡片
    const blackCard = document.getElementById('card-black');
    const blackName = document.getElementById('black-player-name');
    const blackRank = document.getElementById('black-player-rank');
    if (currentRoomState.black_player) {
      blackName.textContent = currentRoomState.black_player.username;
      blackRank.textContent = currentRoomState.black_player.rank_display;
    } else {
      blackName.textContent = '等待玩家加入...';
      blackRank.textContent = '--';
    }

    // 更新白方信息卡片
    const whiteCard = document.getElementById('card-white');
    const whiteName = document.getElementById('white-player-name');
    const whiteRank = document.getElementById('white-player-rank');
    if (currentRoomState.white_player) {
      whiteName.textContent = currentRoomState.white_player.username;
      whiteRank.textContent = currentRoomState.white_player.rank_display;
    } else {
      whiteName.textContent = '等待玩家加入...';
      whiteRank.textContent = '--';
    }

    // 回合高亮
    if (currentRoomState.status === 'playing') {
      if (currentRoomState.current_turn === 1) {
        blackCard.classList.add('active-turn');
        whiteCard.classList.remove('active-turn');
      } else {
        whiteCard.classList.add('active-turn');
        blackCard.classList.remove('active-turn');
      }
    } else {
      blackCard.classList.remove('active-turn');
      whiteCard.classList.remove('active-turn');
    }

    // 准备与认输按钮状态联动
    const readyBtn = document.getElementById('btn-ready');
    const resignBtn = document.getElementById('btn-resign');

    if (currentRoomState.status === 'waiting') {
      readyBtn.style.display = 'inline-block';
      resignBtn.style.display = 'none';
      let isReady = false;
      if (myColor === 1 && currentRoomState.black_player) isReady = currentRoomState.black_player.is_ready;
      if (myColor === 2 && currentRoomState.white_player) isReady = currentRoomState.white_player.is_ready;
      readyBtn.textContent = isReady ? '已就绪 (等待开局)' : '准备就绪';
      readyBtn.disabled = isReady;
    } else if (currentRoomState.status === 'playing') {
      readyBtn.style.display = 'none';
      resignBtn.style.display = 'inline-block';
    } else {
      // 对局已完成 finished
      readyBtn.style.display = 'none';
      resignBtn.style.display = 'none';
      document.getElementById('turn-timer-text').textContent = '对局已结束';
    }

    // 启动或刷新倒计时
    startTimerCountdown(currentRoomState.remaining_seconds);
  }

  /**
   * 局内步时倒计时器
   */
  function startTimerCountdown(initialSeconds) {
    stopTimerCountdown();
    if (!currentRoomState || currentRoomState.status !== 'playing' || currentRoomState.turn_timeout <= 0) {
      document.getElementById('turn-timer-text').textContent = '--';
      return;
    }

    let remaining = initialSeconds;
    const timerEl = document.getElementById('turn-timer-text');

    const updateDisplay = () => {
      timerEl.textContent = `${remaining}s`;
      if (remaining <= 5) {
        timerEl.classList.add('urgent');
        window.soundSynth.playTimerTick();
      } else {
        timerEl.classList.remove('urgent');
      }
    };

    updateDisplay();
    timerInterval = setInterval(() => {
      remaining--;
      if (remaining >= 0) {
        updateDisplay();
      } else {
        stopTimerCountdown();
      }
    }, 1000);
  }

  function stopTimerCountdown() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  /**
   * 5. 排位赛结算弹窗动效
   */
  function showSettlementModal(data) {
    const titleEl = document.getElementById('settlement-title');
    const rankEl = document.getElementById('settlement-rank-text');
    const starsDeltaEl = document.getElementById('settlement-stars-delta');
    const braveEl = document.getElementById('settlement-brave-text');
    const badgeEl = document.getElementById('settlement-badge-tip');

    if (data.is_win) {
      titleEl.textContent = '胜利';
      titleEl.className = 'settlement-title settlement-win';
    } else {
      titleEl.textContent = '失败';
      titleEl.className = 'settlement-title settlement-loss';
    }

    rankEl.textContent = `${data.old_rank}  ➔  ${data.new_rank}`;
    starsDeltaEl.textContent = data.stars_delta > 0 ? `星数 +${data.stars_delta}` : (data.stars_delta < 0 ? `星数 -1` : `星数保持不变`);

    braveEl.textContent = `获得勇者积分 +${data.brave_points_gained} (当前累计 ${data.current_brave_points})`;

    if (data.protection_triggered) {
      badgeEl.innerHTML = '<span style="color:#16A34A;font-weight:bold;">[掉星保护] 消耗勇者积分抵扣 1 颗掉星！</span>';
    } else if (data.bonus_star_triggered) {
      badgeEl.innerHTML = '<span style="color:#F59E0B;font-weight:bold;">[勇者奖励] 积分满额，额外赠送 1 颗星！</span>';
    } else {
      badgeEl.innerHTML = '';
    }

    settlementModal.classList.add('show');
  }

  /**
   * 休闲对局与好友对战终局弹窗展示
   */
  function showCasualGameOverModal(isWinner, winReason) {
    const titleEl = document.getElementById('settlement-title');
    const rankEl = document.getElementById('settlement-rank-text');
    const starsDeltaEl = document.getElementById('settlement-stars-delta');
    const braveEl = document.getElementById('settlement-brave-text');
    const badgeEl = document.getElementById('settlement-badge-tip');

    const reasonMap = {
      five_in_row: '五子连珠',
      resign: '认输',
      timeout: '步时超时',
      draw: '协商和棋',
      disconnect: '断线超时',
    };

    const reasonText = reasonMap[winReason] || '终局';

    if (isWinner) {
      titleEl.textContent = '胜利';
      titleEl.className = 'settlement-title settlement-win';
      starsDeltaEl.textContent = winReason === 'resign' ? '对手认输' : reasonText;
    } else {
      titleEl.textContent = '失败';
      titleEl.className = 'settlement-title settlement-loss';
      starsDeltaEl.textContent = winReason === 'resign' ? '主动认输' : reasonText;
    }

    rankEl.textContent = currentRoomState && currentRoomState.mode === 'friend' ? '好友开房对战' : '单人休闲对战';
    braveEl.textContent = '休闲与好友模式不计天梯星数变动';
    badgeEl.innerHTML = '';

    settlementModal.classList.add('show');
  }

  /**
   * 6. 用户交互按钮事件绑定
   */
  // 模式：天梯排位赛
  document.getElementById('card-ranked').addEventListener('click', () => {
    if (!currentUser) return;
    wsClient.send('match_queue', null, {
      mode: 'ranked',
      tier: currentUser.tier,
      stars: currentUser.stars,
    });
  });

  // 模式：单人休闲对战
  document.getElementById('card-casual').addEventListener('click', () => {
    wsClient.send('match_queue', null, { mode: 'casual' });
  });

  // 模式：好友对局
  document.getElementById('card-friend').addEventListener('click', () => {
    const roomInput = document.getElementById('input-room-code');
    if (roomInput) roomInput.value = '';
    friendModal.classList.add('show');
  });

  // 取消匹配
  document.getElementById('btn-cancel-match').addEventListener('click', () => {
    wsClient.send('match_cancel', null);
    matchModal.classList.remove('show');
  });

  // 好友房间：创建
  document.getElementById('btn-create-friend-room').addEventListener('click', async () => {
    const timeout = parseInt(document.getElementById('select-timeout').value, 10);
    try {
      const res = await fetch('/api/room/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ turn_timeout: timeout, preferred_color: 0 }),
      });
      const data = await res.json();
      const roomInput = document.getElementById('input-room-code');
      if (roomInput) roomInput.value = '';
      friendModal.classList.remove('show');
      wsClient.send('join_room', data.room_id, {
        turn_timeout: timeout,
        rank_display: currentUser ? currentUser.display_rank : '倔强青铜 III',
      });
    } catch (err) {
      alert('创建房间失败');
    }
  });

  // 好友房间：加入
  document.getElementById('btn-join-friend-room').addEventListener('click', () => {
    const roomInput = document.getElementById('input-room-code');
    const code = roomInput.value.trim().toUpperCase();
    if (!code) {
      alert('请输入 6 位房间码');
      return;
    }
    // 填完码加入后自动清空/删除输入框内容
    roomInput.value = '';
    friendModal.classList.remove('show');
    wsClient.send('join_room', code, {
      rank_display: currentUser ? currentUser.display_rank : '倔强青铜 III',
    });
  });

  // 局内：准备
  document.getElementById('btn-ready').addEventListener('click', () => {
    if (currentRoomId) {
      wsClient.send('ready', currentRoomId);
    }
  });

  // 局内：认输
  document.getElementById('btn-resign').addEventListener('click', () => {
    if (currentRoomState && currentRoomState.status !== 'playing') {
      return;
    }
    if (confirm('确认认输并结束当局比赛吗？')) {
      wsClient.send('resign', currentRoomId);
      if (currentRoomState) {
        currentRoomState.status = 'finished';
        updateGameRoomUI();
      }
    }
  });

  // 局内：离开/返回大厅
  document.getElementById('btn-leave-room').addEventListener('click', () => {
    if (currentRoomState && currentRoomState.status === 'playing') {
      if (!confirm('对局正在进行中，退出将自动判负，确认离开吗？')) {
        return;
      }
      wsClient.send('resign', currentRoomId);
    }
    if (currentRoomState) {
      currentRoomState.status = 'finished';
    }
    switchView('lobby');
  });

  // 结算弹窗：再来一局
  document.getElementById('btn-settlement-confirm').addEventListener('click', () => {
    settlementModal.classList.remove('show');
    switchView('lobby');
  });

  // 天梯总榜弹窗
  document.getElementById('btn-leaderboard').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/rank/leaderboard');
      const list = await res.json();
      const tbody = document.getElementById('leaderboard-tbody');
      tbody.innerHTML = '';
      list.forEach((item) => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #3D352E';
        tr.innerHTML = `
          <td style="padding:10px;font-weight:bold;color:#D4AF37;">${item.rank}</td>
          <td style="padding:10px;">${item.username}</td>
          <td style="padding:10px;"><span class="rank-pill">${item.display_rank}</span></td>
          <td style="padding:10px;">${item.win_rate}% (${item.win_matches}/${item.total_matches})</td>
        `;
        tbody.appendChild(tr);
      });
      leaderboardModal.classList.add('show');
    } catch (err) {
      alert('加载天梯榜单失败');
    }
  });

  // 关闭各类模态框并自动清空输入码
  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove('show');
    const roomInput = modal.querySelector('#input-room-code');
    if (roomInput) {
      roomInput.value = '';
    }
  }

  document.querySelectorAll('.btn-close-modal').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      closeModal(e.target.closest('.modal-overlay'));
    });
  });

  // 点击背景遮罩关闭并自动删除输入码
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeModal(overlay);
      }
    });
  });

  // 按 ESC 键关闭并自动删除输入码
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.show').forEach((m) => {
        closeModal(m);
      });
    }
  });

  // 音效切换
  const soundBtn = document.getElementById('btn-sound-toggle');
  soundBtn.addEventListener('click', () => {
    const muted = window.soundSynth.toggleMute();
    soundBtn.textContent = muted ? '🔇 音效: 关' : '🔊 音效: 开';
  });

  // 启动鉴权初始化流程
  initAuth();
});
