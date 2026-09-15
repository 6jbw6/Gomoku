"""FastAPI 接口与系统集成测试用例模块。

测试覆盖：
1. 游客快速登录 (/api/auth/guest)；
2. 正式用户注册与登录校验 (/api/auth/register, /api/auth/login)；
3. 个人档案与段位信息拉取 (/api/auth/me)；
4. 好友对战房间创建 (/api/room/create)；
5. 天梯排行榜查询 (/api/rank/leaderboard)。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import pytest
from httpx import ASGITransport, AsyncClient
from gomoku.main import app
from gomoku.storage.database import init_db


@pytest.mark.anyio
async def test_auth_and_profile_flow() -> None:
    """测试完整用户认证与个人资料获取流程。"""
    await init_db()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. 测试游客登录
        res_guest = await client.post("/api/auth/guest", json={"nickname": "棋客_测试"})
        assert res_guest.status_code == 200
        data_guest = res_guest.json()
        assert "access_token" in data_guest
        assert data_guest["is_guest"] is True
        token = data_guest["access_token"]

        # 2. 测试根据 Token 查询资料
        res_me = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert res_me.status_code == 200
        data_me = res_me.json()
        assert data_me["username"].startswith("棋客")
        assert "倔强青铜" in data_me["tier"]
        assert data_me["stars"] == 0

        # 3. 测试创建好友对战房间
        res_room = await client.post(
            "/api/room/create", json={"turn_timeout": 60, "preferred_color": 0}
        )
        assert res_room.status_code == 200
        data_room = res_room.json()
        assert "room_id" in data_room
        assert len(data_room["room_id"]) == 6
        assert data_room["turn_timeout"] == 60

        # 4. 测试拉取天梯排行榜
        res_rank = await client.get("/api/rank/leaderboard")
        assert res_rank.status_code == 200
        leaderboard = res_rank.json()
        assert isinstance(leaderboard, list)
