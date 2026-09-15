"""五子棋桌面端局域网与本地好友房间码通信服务模块。

基于 Python 原生 socket 与多线程架构，实现 6 位房间码创建、加入、落子帧同步及断线清理。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import json
import socket
import threading
from typing import Callable, Dict, Optional, Tuple

DEFAULT_ROOM_PORT = 8088


class RoomSession:
    """房间连接会话实体。"""

    def __init__(self, room_id: str, host_conn: socket.socket, host_name: str) -> None:
        """初始化房间会话。"""
        self.room_id = room_id
        self.host_conn = host_conn
        self.host_name = host_name
        self.guest_conn: Optional[socket.socket] = None
        self.guest_name: str = ""
        self.is_started: bool = False


class RoomHostServer:
    """轻量级房间监听调度服务端。"""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_ROOM_PORT) -> None:
        """初始化房间服务器。"""
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.is_running: bool = False
        self.rooms: Dict[str, RoomSession] = {}
        self.lock = threading.Lock()

    def start(self) -> bool:
        """启动后台监听线程，若端口已被占用则返回 False。"""
        if self.is_running:
            return True
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
            self.is_running = True

            t = threading.Thread(target=self._listen_loop, daemon=True)
            t.start()
            return True
        except Exception:
            self.is_running = False
            return False

    def stop(self) -> None:
        """停止服务端并释放套接字。"""
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass

    def _listen_loop(self) -> None:
        """接收新客户端接入循环。"""
        while self.is_running and self.server_sock:
            try:
                conn, _ = self.server_sock.accept()
                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
            except Exception:
                break

    def _handle_client(self, conn: socket.socket) -> None:
        """处理单客户端连接帧通信。"""
        buffer = ""
        current_room_id: Optional[str] = None
        is_host: bool = False

        try:
            while self.is_running:
                data = conn.recv(2048).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    action = msg.get("action")

                    if action == "create":
                        room_id = msg.get("room_id", "")
                        username = msg.get("username", "房主")
                        with self.lock:
                            self.rooms[room_id] = RoomSession(room_id, conn, username)
                        current_room_id = room_id
                        is_host = True
                        self._send(conn, {"event": "created", "room_id": room_id})

                    elif action == "join":
                        room_id = msg.get("room_id", "")
                        username = msg.get("username", "客方")
                        with self.lock:
                            session = self.rooms.get(room_id)
                            if not session:
                                self._send(conn, {"event": "error", "msg": "房间码不存在"})
                                continue
                            if session.guest_conn:
                                self._send(conn, {"event": "error", "msg": "房间已满员"})
                                continue
                            session.guest_conn = conn
                            session.guest_name = username
                            session.is_started = True

                        current_room_id = room_id
                        is_host = False

                        # 双方通知开局：房主执黑先手，客方执白后手
                        self._send(session.host_conn, {
                            "event": "start",
                            "my_color": "black",
                            "opponent_name": username,
                        })
                        self._send(conn, {
                            "event": "start",
                            "my_color": "white",
                            "opponent_name": session.host_name,
                        })

                    elif action in ("move", "surrender"):
                        # 转发对局消息至对方
                        with self.lock:
                            session = self.rooms.get(current_room_id)
                            if session:
                                target = session.guest_conn if is_host else session.host_conn
                                if target:
                                    self._send(target, msg)
        except Exception:
            pass
        finally:
            conn.close()
            if current_room_id:
                with self.lock:
                    session = self.rooms.get(current_room_id)
                    if session:
                        target = session.guest_conn if is_host else session.host_conn
                        if target:
                            try:
                                self._send(target, {"event": "opponent_quit"})
                            except Exception:
                                pass
                        del self.rooms[current_room_id]

    @staticmethod
    def _send(conn: socket.socket, data: dict) -> None:
        """向套接字发送换行结尾的 JSON 帧。"""
        raw = json.dumps(data) + "\n"
        conn.sendall(raw.encode("utf-8"))


class RoomClient:
    """房间网络客户端。"""

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_ROOM_PORT) -> None:
        """初始化客户端。"""
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.is_connected: bool = False
        self.on_message: Optional[Callable[[dict], None]] = None

    def connect(self) -> bool:
        """连接服务端。"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            t = threading.Thread(target=self._recv_loop, daemon=True)
            t.start()
            return True
        except Exception:
            self.is_connected = False
            return False

    def send(self, msg: dict) -> bool:
        """发送 JSON 帧。"""
        if not self.is_connected or not self.sock:
            return False
        try:
            raw = json.dumps(msg) + "\n"
            self.sock.sendall(raw.encode("utf-8"))
            return True
        except Exception:
            self.is_connected = False
            return False

    def _recv_loop(self) -> None:
        """接收服务端推送循环。"""
        buffer = ""
        while self.is_connected and self.sock:
            try:
                data = self.sock.recv(2048).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    if self.on_message:
                        self.on_message(msg)
            except Exception:
                break
        self.is_connected = False

    def close(self) -> None:
        """断开连接。"""
        self.is_connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


# 全局共享房间服务端单例
global_room_server: Optional[RoomHostServer] = None


def get_or_start_room_server(port: int = DEFAULT_ROOM_PORT) -> Tuple[bool, RoomHostServer]:
    """获取或启动本地房间服务端单例。"""
    global global_room_server
    if global_room_server is None:
        global_room_server = RoomHostServer(port=port)
    started = global_room_server.start()
    return started, global_room_server
