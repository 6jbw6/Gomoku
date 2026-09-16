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

        # 测试全屏切换方法
        old_fullscreen = app.is_fullscreen
        app.toggle_fullscreen()
        assert app.is_fullscreen != old_fullscreen

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
        """测试 UDP 信标应答与局域网主机自动发现。"""
        import socket as sk

        from gomoku.gui.room_net import LanBeacon, RoomHostServer, discover_room_host

        # 本机场景下应答源地址由内核路由决定（可能为回环或虚拟网卡地址）
        server = RoomHostServer(port=18088)
        assert server.start() is True
        beacon = LanBeacon(port=18089, room_port=18088)
        assert beacon.start() is True

        found = discover_room_host(timeout=0.8, discovery_port=18089)
        assert found is not None
        assert found[1] == 18088

        # 验证发现的地址可真实接入本机房间服务器
        with sk.create_connection(found, timeout=1.0):
            pass

        beacon.stop()
        server.stop()

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
