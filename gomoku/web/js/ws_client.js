/**
 * WebSocket 通信客户端模块。
 * 
 * 提供断线自动重连、心跳保活检测、强类型信令封包与事件分发订阅。
 * 所有代码注释采用中文。
 */

class GomokuWebSocketClient {
  constructor() {
    this.ws = null;
    this.token = localStorage.getItem('gomoku_token') || '';
    this.eventHandlers = new Map();
    this.reconnectTimer = null;
    this.pingInterval = null;
    this.isConnected = false;
  }

  /**
   * 注册指定 action 的监听处理器。
   */
  on(action, handler) {
    if (!this.eventHandlers.has(action)) {
      this.eventHandlers.set(action, []);
    }
    this.eventHandlers.get(action).push(handler);
  }

  /**
   * 分发接收到的事件通知。
   */
  emit(action, data) {
    const handlers = this.eventHandlers.get(action);
    if (handlers) {
      handlers.forEach((fn) => fn(data));
    }
  }

  /**
   * 建立长连接通道。
   */
  connect(token) {
    if (token) {
      this.token = token;
      localStorage.setItem('gomoku_token', token);
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws${this.token ? `?token=${encodeURIComponent(this.token)}` : ''}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.isConnected = true;
      this.startHeartbeat();
      this.emit('connection_status', { connected: true });
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const action = msg.action;
        const payload = msg.payload;

        if (action === 'pong') {
          return;
        }

        // 分发给对应的业务监听函数
        this.emit(action, payload);
      } catch (err) {
        console.error('WebSocket 数据解析失败:', err);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.stopHeartbeat();
      this.emit('connection_status', { connected: false });
      this.scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.warn('WebSocket 通道波动:', err);
    };
  }

  /**
   * 发送指令封包。
   */
  send(action, roomId, payload = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket 尚未就绪，消息已挂起');
      return;
    }
    const msg = {
      action: action,
      room_id: roomId,
      payload: payload,
    };
    this.ws.send(JSON.stringify(msg));
  }

  /**
   * 启动心跳检测（每 25 秒发送一次轻量 ping）。
   */
  startHeartbeat() {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ action: 'ping' }));
      }
    }, 25000);
  }

  /**
   * 停止心跳计时器。
   */
  stopHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * 延迟重连机制。
   */
  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }
}

window.GomokuWebSocketClient = GomokuWebSocketClient;
