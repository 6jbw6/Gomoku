"""五子棋桌面端 GUI 与局域网联机单元测试。

测试 Pygame 视口几何转换、本地档案状态结算与局域网联机通信逻辑。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import os

# 设置无头显示驱动以支持 CI/CD 与终端自动化测试
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
from gomoku.core.enums import GameMode, PieceColor  # noqa: E402
from gomoku.gui.app import GomokuApp  # noqa: E402
from gomoku.gui.board_view import BoardView  # noqa: E402
from gomoku.gui.profile import UserProfileManager  # noqa: E402


class TestBoardView:
    """测试棋盘坐标像素映射与吸附逻辑。"""

    def test_coordinate_mapping(self) -> None:
        """测试正向像素映射与反向吸附网格坐标。"""
        pygame.init()
        bv = BoardView((60, 60, 680, 680))
        px, py = bv.to_pixel(7, 7)
        grid_pos = bv.to_grid(px, py)
        assert grid_pos == (7, 7)

    def test_out_of_bounds_pixel(self) -> None:
        """测试棋盘区域外像素坐标返回 None。"""
        bv = BoardView((60, 60, 680, 680))
        assert bv.to_grid(10, 10) is None


class TestUserProfileManager:
    """测试本地棋手档案管理器。"""

    def test_settle_match_progression(self, tmp_path) -> None:
        """测试排位赛胜利后星数与勇者积分累加。"""
        profile_file = str(tmp_path / "test_profile.json")
        mgr = UserProfileManager(filename=profile_file)
        old_stars = mgr.state.stars

        mgr.settle_match(is_winner=True, moves_count=30)
        assert mgr.state.stars == old_stars + 1
        assert mgr.state.win_matches == 1
        assert mgr.state.total_matches == 1


class TestTextInput:
    """测试房间码文本输入框的字符解析与焦点交互。"""

    @staticmethod
    def _press(inp, key: int, unicode: str = "") -> None:
        """向输入框投递一次按键事件。"""
        event = pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)
        inp.handle_event(event)

    def test_ime_blocked_input_fallback(self) -> None:
        """测试中文输入法拦截文本通道（unicode 为空）时按键兜底输入。"""
        from gomoku.gui.components import TextInput

        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        # 模拟中文输入法组字状态：KEYDOWN 携带键码但 unicode 为空
        for key in (pygame.K_a, pygame.K_b, pygame.K_3, pygame.K_KP5, pygame.K_z):
            self._press(inp, key, unicode="")
        assert inp.text == "AB35Z"

    def test_normal_unicode_input(self) -> None:
        """测试常规文本输入通道下字符转大写录入。"""
        from gomoku.gui.components import TextInput

        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        self._press(inp, pygame.K_c, unicode="c")
        self._press(inp, pygame.K_d, unicode="d")
        self._press(inp, pygame.K_7, unicode="7")
        assert inp.text == "CD7"

    def test_fullwidth_and_cjk_rejected(self) -> None:
        """测试汉字与全角字符不得混入房间码。"""
        from gomoku.gui.components import TextInput

        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        self._press(inp, pygame.K_SPACE, unicode="棋")
        self._press(inp, pygame.K_a, unicode="Ａ")
        assert inp.text == ""

    def test_max_length_and_backspace(self) -> None:
        """测试六位上限截断与退格删除。"""
        from gomoku.gui.components import TextInput

        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        for key in (pygame.K_1, pygame.K_2, pygame.K_3,
                    pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7):
            self._press(inp, key, unicode="")
        assert inp.text == "123456"
        self._press(inp, pygame.K_BACKSPACE)
        assert inp.text == "12345"

    def test_inactive_ignores_keys(self) -> None:
        """测试未获得焦点时键盘事件不录入。"""
        from gomoku.gui.components import TextInput

        inp = TextInput((0, 0, 260, 46))
        inp.is_active = False
        self._press(inp, pygame.K_a, unicode="a")
        assert inp.text == ""
        # 点击输入框区域后激活焦点
        click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(130, 23)
        )
        assert inp.handle_event(click) is True
        assert inp.is_active is True

    def test_paste_from_clipboard(self) -> None:
        """测试 Ctrl+V 粘贴房间码（过滤干扰字符并截断至六位）。"""
        from gomoku.gui.components import TextInput, clipboard_put_text

        # 真实写入系统剪贴板，内容含空格、汉字与全角字符等干扰项
        assert clipboard_put_text("ab12 34方xyz！") is True
        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        event = pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_v, mod=pygame.KMOD_CTRL, unicode=""
        )
        inp.handle_event(event)
        assert inp.text == "AB1234"

    def test_paste_truncates_to_max_length(self) -> None:
        """测试粘贴超长内容时仅保留前六位。"""
        from gomoku.gui.components import TextInput, clipboard_put_text

        assert clipboard_put_text("AB12CD78EF") is True
        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        event = pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_v, mod=pygame.KMOD_CTRL, unicode=""
        )
        inp.handle_event(event)
        assert inp.text == "AB12CD"

    def test_copy_to_clipboard(self) -> None:
        """测试 Ctrl+C 将输入框内容复制到系统剪贴板并回读一致。"""
        from gomoku.gui.components import TextInput, clipboard_get_text

        inp = TextInput((0, 0, 260, 46))
        inp.is_active = True
        inp.text = "RZC8HA"
        event = pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_c, mod=pygame.KMOD_CTRL, unicode=""
        )
        assert inp.handle_event(event) is True
        # 回读系统剪贴板验证写入成功（过滤后应保持原房间码）
        assert clipboard_get_text() == "RZC8HA"


class TestGomokuAppFlow:
    """测试 Pygame 桌面端应用生命周期与场景状态流转。"""

    def test_app_lifecycle(self, tmp_path) -> None:
        """测试大厅进入对局、落子与返回大厅全流程。"""
        profile_file = str(tmp_path / "flow_profile.json")
        app = GomokuApp()
        app.profile_mgr = UserProfileManager(filename=profile_file)
        app.lobby_scene.profile = app.profile_mgr
        assert app.current_scene == "lobby"

        # 启动天梯排位赛对局
        app.start_game(
            GameMode.RANKED,
            "天梯排位赛",
            opponent_name="棋客_云弈",
            player_color=PieceColor.BLACK,
        )
        assert app.current_scene == "game"
        assert app.game_scene is not None
        assert app.game_scene.player_color == PieceColor.BLACK

        # 模拟黑棋在天元落子
        app.game_scene._execute_move(7, 7)
        assert len(app.game_scene.move_history) == 1

        # 认输并检查结算弹窗弹出
        app.game_scene._handle_resign()
        assert app.game_scene.settlement_dialog.is_visible is True

        # 返回大厅
        app.back_to_lobby()
        assert app.current_scene == "lobby"
        assert app.game_scene is None


class TestRoomNet:
    """测试局域网/本地好友房间码创建与加入通信。"""

    def test_room_host_and_client(self) -> None:
        """测试服务端创建房间与客户端帧同步。"""
        import time
        from gomoku.gui.room_net import RoomClient, RoomHostServer

        server = RoomHostServer(port=8099)
        assert server.start() is True

        client = RoomClient(port=8099)
        assert client.connect() is True

        client.send({"action": "create", "room_id": "TEST99", "username": "测试房主"})
        time.sleep(0.1)

        received = client.poll_messages()
        assert len(received) >= 1
        assert received[0].get("event") == "created"

        client.close()
        server.stop()

    def test_two_clients_match(self) -> None:
        """测试两个客户端同时匹配成功撮合为真人对弈。"""
        import time
        from gomoku.gui.room_net import RoomClient, RoomHostServer

        server = RoomHostServer(port=8098)
        assert server.start() is True

        client_a = RoomClient(port=8098)
        client_b = RoomClient(port=8098)
        assert client_a.connect() is True
        assert client_b.connect() is True

        client_a.send({
            "action": "match", "mode": "ranked", "username": "棋客A", "rank": "青铜"
        })
        time.sleep(0.05)
        client_b.send({
            "action": "match", "mode": "ranked", "username": "棋客B", "rank": "青铜"
        })
        time.sleep(0.1)

        msg_a = client_a.poll_messages()
        msg_b = client_b.poll_messages()
        assert len(msg_a) >= 1
        assert len(msg_b) >= 1
        assert msg_a[0].get("event") == "start"
        assert msg_b[0].get("event") == "start"

        client_a.close()
        client_b.close()
        server.stop()

    def test_room_two_players_turn_moves(self) -> None:
        """测试好友房间对弈双端落子同步，确保无 AI 介入。"""
        import time
        from gomoku.gui.room_net import RoomClient, RoomHostServer

        server = RoomHostServer(port=8097)
        assert server.start() is True

        host = RoomClient(port=8097)
        guest = RoomClient(port=8097)
        assert host.connect() is True
        assert guest.connect() is True

        # 房主创建房间
        host.send({
            "action": "create", "room_id": "TEST88", "username": "房主", "rank": "青铜"
        })
        time.sleep(0.05)
        # 客方加入房间
        guest.send({
            "action": "join", "room_id": "TEST88", "username": "客方", "rank": "青铜"
        })
        time.sleep(0.05)

        # 双方均收到 start 事件
        host_msgs = host.poll_messages()
        guest_msgs = guest.poll_messages()
        assert any(m.get("event") == "start" for m in host_msgs)
        assert any(m.get("event") == "start" for m in guest_msgs)

        # 房主执黑落子 (7, 7)
        host.send({"action": "move", "x": 7, "y": 7})
        time.sleep(0.05)
        guest_moves = guest.poll_messages()
        assert len(guest_moves) == 1
        assert guest_moves[0].get("x") == 7 and guest_moves[0].get("y") == 7

        # 客方执白落子 (7, 8)
        guest.send({"action": "move", "x": 7, "y": 8})
        time.sleep(0.05)
        host_moves = host.poll_messages()
        assert len(host_moves) == 1
        assert host_moves[0].get("x") == 7 and host_moves[0].get("y") == 8

        host.close()
        guest.close()
        server.stop()

    def test_lan_beacon_discovery(self) -> None:
        """测试 UDP 信标应答、局域网主机发现与本机自答过滤。"""
        import socket as sk

        from gomoku.gui import room_net
        from gomoku.gui.room_net import LanBeacon, RoomHostServer, discover_room_host

        server = RoomHostServer(port=18088)
        assert server.start() is True
        beacon = LanBeacon(port=18089, room_port=18088)
        assert beacon.start() is True

        # 保留真实本机 IP 集合，用于测试后还原
        real_ips = list(room_net._local_ips())
        try:
            # 伪造本机 IP 为无关地址：本机信标应答源不在集合内，可被发现
            room_net._local_ip_cache = ["10.99.99.99"]
            found = discover_room_host(timeout=0.8, discovery_port=18089)
            assert found is not None
            assert found[1] == 18088

            # 验证发现的地址可真实接入本机房间服务器
            with sk.create_connection(found, timeout=1.0):
                pass

            # 把回环与真实网卡均计入本机：信标全部自答应被过滤，
            # 修复机房全员自任主机时本机应答掩盖真实远端主机的问题
            room_net._local_ip_cache = ["127.0.0.1"] + real_ips
            assert discover_room_host(timeout=0.8, discovery_port=18089) is None
        finally:
            room_net._local_ip_cache = real_ips
            beacon.stop()
            server.stop()

    def test_pick_converge_host_rules(self) -> None:
        """测试撮合收敛目标选择：全网向 IP 数值最小的存活主机收敛。"""
        from gomoku.gui import room_net

        fake_hosts: list = []
        orig_disc = room_net.discover_room_hosts
        orig_alive = room_net._tcp_alive
        room_net.discover_room_hosts = lambda **kw: list(fake_hosts)
        room_net._tcp_alive = lambda h, p, timeout=0.6: True
        try:
            # 本机 .20 自任主机：远端存在数值更小的 .9 → 迁移到 .9
            room_net._local_ip_cache = ["192.168.10.20"]
            fake_hosts[:] = [("192.168.10.9", 8088)]
            assert room_net.pick_converge_host("127.0.0.1", 8088) == ("192.168.10.9", 8088)

            # 本机 .9 自任主机（全网数值最小，即收敛汇点）→ 留守不迁移
            room_net._local_ip_cache = ["192.168.10.9"]
            fake_hosts[:] = [("192.168.10.20", 8088)]
            assert room_net.pick_converge_host("127.0.0.1", 8088) is None

            # 已在收敛目标主机上 → 无需迁移
            room_net._local_ip_cache = ["192.168.10.30"]
            fake_hosts[:] = [("192.168.10.9", 8088), ("192.168.10.20", 8088)]
            assert room_net.pick_converge_host("192.168.10.9", 8088) is None

            # 接入非收敛主机 → 向数值最小的存活主机迁移
            assert room_net.pick_converge_host("192.168.10.20", 8088) == (
                "192.168.10.9", 8088
            )

            # 数值最小的主机 TCP 失活 → 顺延次优存活主机
            alive = {"192.168.10.9": False, "192.168.10.20": True}
            room_net._tcp_alive = lambda h, p, timeout=0.6: alive.get(h, True)
            assert room_net.pick_converge_host("192.168.10.30", 8088) == (
                "192.168.10.20", 8088
            )

            # 局域网内无其他主机 → 不迁移
            fake_hosts[:] = []
            assert room_net.pick_converge_host("127.0.0.1", 8088) is None
        finally:
            room_net.discover_room_hosts = orig_disc
            room_net._tcp_alive = orig_alive
            room_net._local_ip_cache = None

    def test_discover_timeout_returns_none(self) -> None:
        """测试无局域网主机时应答超时返回 None。"""
        from gomoku.gui.room_net import discover_room_host

        assert discover_room_host(timeout=0.3, discovery_port=18090) is None

    def test_resolve_room_host_local_fallback(self) -> None:
        """测试无远端主机时本机自动担任房间服务器并生成缓存。"""
        from gomoku.gui import room_net
        from gomoku.gui.room_net import (
            RoomClient,
            invalidate_room_host_cache,
            resolve_room_host,
        )

        try:
            invalidate_room_host_cache()
            # 清理其他用例（含应用启动预热线程）残留的默认端口全局单例，
            # 保证本用例以 18087 端口自建全新服务器
            if room_net.global_room_server is not None:
                room_net.global_room_server.stop()
                room_net.global_room_server = None
            if room_net.global_lan_beacon is not None:
                room_net.global_lan_beacon.stop()
                room_net.global_lan_beacon = None
            host, port = resolve_room_host(port=18087, discovery_port=28091)
            assert host == "127.0.0.1"
            assert port == 18087

            client = RoomClient(host=host, port=port)
            assert client.connect() is True
            client.close()
        finally:
            # 清理全局单例与缓存，避免影响其他用例
            invalidate_room_host_cache()
            if room_net.global_room_server is not None:
                room_net.global_room_server.stop()
                room_net.global_room_server = None
            if room_net.global_lan_beacon is not None:
                room_net.global_lan_beacon.stop()
                room_net.global_lan_beacon = None

    def test_match_heal_migration_and_match(self, tmp_path) -> None:
        """撮合空等自愈全链路：体检到收敛主机后迁移重排并成功撮合。"""
        import time as tm

        from gomoku.core.enums import GameMode
        from gomoku.gui import room_net
        from gomoku.gui.audio import SoundManager
        from gomoku.gui.profile import UserProfileManager
        from gomoku.gui.room_net import (
            RoomClient,
            RoomHostServer,
            invalidate_room_host_cache,
        )
        from gomoku.gui.scenes import LobbyScene

        server_self = RoomHostServer(port=18095)  # 模拟本机自任主机
        assert server_self.start() is True
        server_conv = RoomHostServer(port=18096)  # 模拟远端收敛主机
        assert server_conv.start() is True

        started: list = []
        lobby = LobbyScene(
            UserProfileManager(filename=str(tmp_path / "heal_profile.json")),
            SoundManager(),
            on_start_game=lambda **kw: started.append(kw),
        )
        opponent = RoomClient(port=18096)

        try:
            # 本机自任主机上排队（模拟机房全员自任主机时的分裂态）
            room_net.set_resolved_room_host("127.0.0.1", 18095)
            lobby._start_matchmaking(GameMode.RANKED, "测试匹配")
            assert lobby.match_client is not None
            assert lobby.match_client.port == 18095

            # 收敛体检产出目标：应迁移重排到远端收敛主机
            lobby.match_heal_done = True
            lobby.match_heal_target = ("127.0.0.1", 18096)
            lobby.update()
            assert lobby.match_client is not None
            assert lobby.match_client.port == 18096

            # 收敛主机上另一棋手入队 → 双方立即撮合开局
            assert opponent.connect() is True
            opponent.send({
                "action": "match", "mode": "ranked", "username": "对手", "rank": "青铜"
            })
            tm.sleep(0.2)
            lobby.update()

            assert len(started) == 1
            assert started[0].get("mode") == GameMode.RANKED
            game_client = started[0].get("room_client")
            assert game_client is not None
            assert game_client.port == 18096
            assert lobby.is_matching is False
        finally:
            if lobby.match_client is not None:
                lobby.match_client.close()
            opponent.close()
            server_self.stop()
            server_conv.stop()
            invalidate_room_host_cache()
            if room_net.global_room_server is not None:
                room_net.global_room_server.stop()
                room_net.global_room_server = None
            if room_net.global_lan_beacon is not None:
                room_net.global_lan_beacon.stop()
                room_net.global_lan_beacon = None
