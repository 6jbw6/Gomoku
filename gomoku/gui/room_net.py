"""五子棋桌面端局域网与本地房间码及联机匹配通信服务模块。

基于 Python 原生 socket 与多线程架构，实现房间码对战、双端联机匹配与落子帧同步。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import json
import queue
import random
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple

DEFAULT_ROOM_PORT = 8088
DEFAULT_DISCOVERY_PORT = 8089


class RoomSession:
    """房间连接会话实体。"""

    def __init__(
        self,
        room_id: str,
        host_conn: socket.socket,
        host_name: str,
        host_rank: str = "初入棋道",
    ) -> None:
        """初始化房间会话。"""
        self.room_id = room_id
        self.host_conn = host_conn
        self.host_name = host_name
        self.host_rank = host_rank
        self.guest_conn: Optional[socket.socket] = None
        self.guest_name: str = ""
        self.guest_rank: str = "初入棋道"
        self.is_started: bool = False


class RoomHostServer:
    """轻量级房间监听与联机撮合服务端。"""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_ROOM_PORT) -> None:
        """初始化房间服务器。"""
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.is_running: bool = False
        self.rooms: Dict[str, RoomSession] = {}
        self.match_queues: Dict[str, List[dict]] = {"ranked": [], "casual": []}
        # 连接 → (房间号, 是否房主) 映射：撮合建房时需跨线程登记双方身份
        self.conn_room_map: Dict[socket.socket, Tuple[str, bool]] = {}
        self.lock = threading.Lock()

    def start(self) -> bool:
        """启动后台监听线程，若端口已被占用则返回 False。"""
        if self.is_running:
            return True
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(10)
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
                        room_id = msg.get("room_id", "").strip().upper()
                        username = msg.get("username", "房主")
                        rank = msg.get("rank", "初入棋道")
                        with self.lock:
                            self.rooms[room_id] = RoomSession(room_id, conn, username, rank)
                            self.conn_room_map[conn] = (room_id, True)
                        self._send(conn, {"event": "created", "room_id": room_id})

                    elif action == "join":
                        room_id = msg.get("room_id", "").strip().upper()
                        username = msg.get("username", "客方")
                        rank = msg.get("rank", "初入棋道")
                        with self.lock:
                            session = self.rooms.get(room_id)
                            if not session:
                                self._send(conn, {"event": "error", "msg": "房间码不存在或已解散"})
                                continue
                            if session.guest_conn is not None:
                                self._send(conn, {"event": "error", "msg": "房间已满员"})
                                continue
                            session.guest_conn = conn
                            session.guest_name = username
                            session.guest_rank = rank
                            session.is_started = True
                            self.conn_room_map[conn] = (room_id, False)

                            h_name = session.host_name
                            g_name = username
                            if h_name == g_name:
                                h_name = f"{h_name} (房主)"
                                g_name = f"{g_name} (客方)"

                            # 双方通知开局：房主执黑先手，客方执白后手
                            self._send(session.host_conn, {
                                "event": "start",
                                "mode": "friend",
                                "room_id": room_id,
                                "my_color": "black",
                                "opponent_name": g_name,
                                "opponent_rank": session.guest_rank,
                            })
                            self._send(conn, {
                                "event": "start",
                                "mode": "friend",
                                "room_id": room_id,
                                "my_color": "white",
                                "opponent_name": h_name,
                                "opponent_rank": session.host_rank,
                            })

                    elif action == "match":
                        mode_key = msg.get("mode", "ranked")
                        username = msg.get("username", "棋客")
                        rank = msg.get("rank", "初入棋道")
                        with self.lock:
                            queue = self.match_queues.setdefault(mode_key, [])
                            queue = [q for q in queue if q["conn"] != conn]
                            self.match_queues[mode_key] = queue

                            if queue:
                                # 撮合匹配成功！
                                peer_item = queue.pop(0)
                                peer_conn = peer_item["conn"]
                                peer_name = peer_item["username"]
                                peer_rank = peer_item["rank"]

                                m_id = f"M{int(time.time() * 1000) % 1000000}"
                                ms = RoomSession(m_id, peer_conn, peer_name, peer_rank)
                                ms.guest_conn = conn
                                ms.guest_name = username
                                ms.guest_rank = rank
                                ms.is_started = True
                                self.rooms[m_id] = ms

                                # 撮合建房须同步登记双方连接身份：
                                # 先入队的房主线程无法感知自己已被撮合，
                                # 须通过映射表跨线程登记其 (房间号, 是否房主)
                                self.conn_room_map[conn] = (m_id, False)
                                self.conn_room_map[peer_conn] = (m_id, True)

                                p_name = peer_name
                                u_name = username
                                if p_name == u_name:
                                    p_name = f"{p_name}_先手"
                                    u_name = f"{u_name}_后手"

                                self._send(peer_conn, {
                                    "event": "start",
                                    "mode": mode_key,
                                    "room_id": m_id,
                                    "my_color": "black",
                                    "opponent_name": u_name,
                                    "opponent_rank": rank,
                                })
                                self._send(conn, {
                                    "event": "start",
                                    "mode": mode_key,
                                    "room_id": m_id,
                                    "my_color": "white",
                                    "opponent_name": p_name,
                                    "opponent_rank": peer_rank,
                                })
                            else:
                                queue.append({
                                    "conn": conn,
                                    "username": username,
                                    "rank": rank,
                                    "mode": mode_key,
                                    "time": time.time(),
                                })

                    elif action == "cancel_match":
                        with self.lock:
                            for q in self.match_queues.values():
                                q[:] = [item for item in q if item["conn"] != conn]

                    elif action in ("move", "surrender"):
                        with self.lock:
                            room_info = self.conn_room_map.get(conn)
                            session = self.rooms.get(room_info[0]) if room_info else None
                            if session:
                                target = (
                                    session.guest_conn if room_info[1] else session.host_conn
                                )
                                if target:
                                    self._send(target, msg)
        except Exception:
            pass
        finally:
            conn.close()
            with self.lock:
                # 断线时移出匹配队列并清理房间映射
                for q in self.match_queues.values():
                    q[:] = [item for item in q if item["conn"] != conn]
                room_info = self.conn_room_map.pop(conn, None)
                if room_info:
                    session = self.rooms.get(room_info[0])
                    if session:
                        target = (
                            session.guest_conn if room_info[1] else session.host_conn
                        )
                        if target:
                            try:
                                self._send(target, {"event": "opponent_quit"})
                            except Exception:
                                pass
                            self.conn_room_map.pop(target, None)
                        del self.rooms[room_info[0]]

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
        self.msg_queue: queue.Queue = queue.Queue()

    def connect(self) -> bool:
        """连接服务端。"""
        if self.is_connected and self.sock:
            return True
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

    def poll_messages(self) -> List[dict]:
        """主线程轮询获取已到达的网络帧。"""
        messages = []
        while not self.msg_queue.empty():
            try:
                messages.append(self.msg_queue.get_nowait())
            except queue.Empty:
                break
        return messages

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
                    self.msg_queue.put(msg)
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


class LanBeacon:
    """局域网 UDP 广播应答信标。

    监听发现端口并即时回应本机房间服务器地址，
    使同机房与校园网内其他机器的客户端可自动发现并接入本机对战服务。
    """

    def __init__(
        self,
        port: int = DEFAULT_DISCOVERY_PORT,
        room_port: int = DEFAULT_ROOM_PORT,
    ) -> None:
        """初始化信标监听端口与对外通告的房间端口。"""
        self.port = port
        self.room_port = room_port
        self.sock: Optional[socket.socket] = None
        self.is_running: bool = False

    def start(self) -> bool:
        """启动应答后台线程，端口被占用时返回 False。"""
        if self.is_running:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", self.port))
            self.sock.settimeout(1.0)
            self.is_running = True
            t = threading.Thread(target=self._serve_loop, daemon=True)
            t.start()
            return True
        except Exception:
            self.is_running = False
            return False

    def stop(self) -> None:
        """停止信标并释放套接字。"""
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def _serve_loop(self) -> None:
        """循环接收发现请求并回应服务器在线帧。"""
        while self.is_running and self.sock:
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("type") == "discover":
                    reply = {"type": "server_here", "port": self.room_port}
                    self.sock.sendto(json.dumps(reply).encode("utf-8"), addr)
            except socket.timeout:
                continue
            except Exception:
                if not self.is_running:
                    break
                continue


def _broadcast_targets() -> List[str]:
    """枚举局域网探测目标地址（受限广播、定向广播与本机回环）。"""
    targets = {"255.255.255.255", "127.0.0.1"}
    try:
        local_ips = socket.gethostbyname_ex(socket.gethostname())[2]
    except Exception:
        local_ips = []
    for ip in local_ips:
        parts = ip.split(".")
        if len(parts) != 4 or parts[0] in ("127", "169"):
            continue
        targets.add(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
        targets.add(f"{parts[0]}.{parts[1]}.255.255")
    return list(targets)


# 本机网卡 IPv4 地址缓存：过滤本机信标对定向广播的自答
_local_ip_cache: Optional[List[str]] = None


def _local_ips() -> List[str]:
    """获取本机各网卡的 IPv4 地址列表（解析失败返回空表）。"""
    global _local_ip_cache
    if _local_ip_cache is None:
        try:
            ips = socket.gethostbyname_ex(socket.gethostname())[2]
            _local_ip_cache = [ip for ip in ips if not ip.startswith("127.")]
        except Exception:
            _local_ip_cache = []
    return _local_ip_cache


def _ip_sort_key(ip: str) -> Tuple[int, int, int, int]:
    """将点分 IPv4 转为数值元组用于比较（非法地址排最后）。"""
    try:
        parts = tuple(int(p) for p in ip.split("."))
        if len(parts) == 4:
            return parts  # type: ignore[return-value]
    except Exception:
        pass
    return (255, 255, 255, 255)


def discover_room_hosts(
    timeout: float = 1.0,
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
) -> List[Tuple[str, int]]:
    """向局域网广播探测并收集全部房间服务器。

    返回所有应答主机的 (地址, 房间端口) 列表；本机信标对
    定向广播与回环探测的自答会被过滤，确保结果只含机房内
    其他机器，避免全员自任主机时本机应答掩盖真实远端主机。
    """
    probe = {"type": "discover"}
    payload = json.dumps(probe).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    own_ips = set(_local_ips())
    found: Dict[str, int] = {}
    try:
        rounds = max(1, int(round(timeout / 0.25)))
        targets = _broadcast_targets()
        for _ in range(rounds):
            for target in targets:
                try:
                    sock.sendto(payload, (target, discovery_port))
                except Exception:
                    continue
            # 本轮窗口内持续接收，收集所有应答主机（应答有先后）
            deadline = time.time() + 0.25
            while True:
                remain = deadline - time.time()
                if remain <= 0:
                    break
                sock.settimeout(remain)
                try:
                    data, addr = sock.recvfrom(1024)
                except Exception:
                    break
                ip = addr[0]
                # 本机信标自答（定向广播回环/本机回环）不计入结果
                if ip in own_ips or ip == "127.0.0.1":
                    continue
                try:
                    msg = json.loads(data.decode("utf-8"))
                except Exception:
                    continue
                if msg.get("type") == "server_here":
                    found[ip] = int(msg.get("port", DEFAULT_ROOM_PORT))
        return list(found.items())
    finally:
        sock.close()


def discover_room_host(
    timeout: float = 1.0,
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
) -> Optional[Tuple[str, int]]:
    """向局域网广播探测正在运行的房间服务器，返回首个应答主机。"""
    hosts = discover_room_hosts(timeout=timeout, discovery_port=discovery_port)
    return hosts[0] if hosts else None


def _tcp_alive(host: str, port: int, timeout: float = 0.6) -> bool:
    """探测远端房间服务器 TCP 端口是否可正常接入。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# 已解析的房间服务器地址缓存（避免每次连接都重复广播探测）
_resolved_host_cache: Optional[Tuple[str, int]] = None


def invalidate_room_host_cache() -> None:
    """清空已解析的服务器地址缓存（链路失效后重新发现用）。"""
    global _resolved_host_cache
    _resolved_host_cache = None


def set_resolved_room_host(host: str, port: int) -> None:
    """外部直接设定已解析的服务器地址缓存（收敛迁移后同步缓存）。"""
    global _resolved_host_cache
    _resolved_host_cache = (host, port)


def resolve_room_host(
    port: int = DEFAULT_ROOM_PORT,
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
) -> Tuple[str, int]:
    """解析当前可用的房间服务器地址。

    优先接入局域网（机房/校园网）内已运行的远端主机；
    若无应答则本机自动担任主机并对外广播信标。
    机房内整机同时启动时各机首轮探测均无应答（最先自任
    主机的机器信标尚未就绪），全员会同时自任主机导致撮合
    队列分裂，故自任前随机退避后复探一次错开启动竞争。
    """
    global _resolved_host_cache
    if _resolved_host_cache is not None:
        return _resolved_host_cache

    found = discover_room_host(discovery_port=discovery_port)
    if found is None:
        time.sleep(random.uniform(0.3, 0.9))
        found = discover_room_host(discovery_port=discovery_port)

    if found is not None and _tcp_alive(found[0], found[1]):
        _resolved_host_cache = found
        return found

    get_or_start_room_server(port=port)
    fallback = ("127.0.0.1", port)
    _resolved_host_cache = fallback
    return fallback


def pick_converge_host(
    current_host: str,
    current_port: int,
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
) -> Optional[Tuple[str, int]]:
    """为撮合队列挑选全网统一的收敛迁移目标主机。

    机房整机同时启动时各机同时自任主机，撮合队列被分裂在
    各自本机服务器上永远撮合不到对手（本地回环连接恒成功，
    缓存永不失效）。本函数使全网按统一规则收敛到同一台主机：
    取局域网内 IP 数值最小且存活的远端主机为目标；本机自任
    主机时仅当目标 IP 小于本机 IP 才迁移，保证存在唯一汇点
    （IP 最小的机器），杜绝两台自任主机互迁抖动。
    """
    hosts = discover_room_hosts(discovery_port=discovery_port)
    if not hosts:
        return None

    is_self_host = current_host in ("127.0.0.1", "localhost")
    my_ips = sorted(_local_ips(), key=_ip_sort_key)
    my_min = _ip_sort_key(my_ips[0]) if my_ips else None

    for ip, port in sorted(hosts, key=lambda h: _ip_sort_key(h[0])):
        if (ip, port) == (current_host, current_port):
            return None  # 已在收敛目标主机上，无需迁移
        if is_self_host and my_min is not None and not _ip_sort_key(ip) < my_min:
            # 目标不小于本机 IP：本机即汇点，留守待其他机器向本机收敛
            continue
        if _tcp_alive(ip, port, timeout=0.6):
            return (ip, port)
    return None


# 全局共享房间服务端单例与局域网信标单例
global_room_server: Optional[RoomHostServer] = None
global_lan_beacon: Optional[LanBeacon] = None


def get_or_start_room_server(port: int = DEFAULT_ROOM_PORT) -> Tuple[bool, RoomHostServer]:
    """获取或启动本地房间服务端单例，并同步开启局域网广播信标。"""
    global global_room_server, global_lan_beacon
    if global_room_server is None:
        global_room_server = RoomHostServer(port=port)
    started = global_room_server.start()
    if started and global_lan_beacon is None:
        # 开启 UDP 信标，使同机房/校园网其他机器可以发现本机服务
        beacon = LanBeacon(room_port=port)
        if beacon.start():
            global_lan_beacon = beacon
    return started, global_room_server
