"""Pydantic 数据模型与协议定义模块。

包含用户认证、房间操作、天梯排行榜与 WebSocket 实时消息协议。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GuestLoginRequest(BaseModel):
    """游客登录/快捷进入请求。"""
    nickname: Optional[str] = Field(None, max_length=20, description="自定义昵称")


class RegisterRequest(BaseModel):
    """用户注册请求。"""
    username: str = Field(..., min_length=2, max_length=20, description="登录用户名")
    password: str = Field(..., min_length=4, max_length=32, description="密码")


class LoginRequest(BaseModel):
    """用户登录请求。"""
    username: str = Field(..., description="登录用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """认证成功令牌响应。"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    is_guest: bool


class UserProfileResponse(BaseModel):
    """玩家基础与天梯信息响应。"""
    user_id: str
    username: str
    is_guest: bool
    tier: str
    sub_tier: int
    stars: int
    display_rank: str
    brave_points: int
    winning_streak: int
    total_matches: int
    win_matches: int
    win_rate: float


class CreateRoomRequest(BaseModel):
    """创建好友房间请求。"""
    turn_timeout: int = Field(30, ge=0, le=180, description="每步限时（秒），0为不限时")
    preferred_color: int = Field(0, ge=0, le=2, description="偏好执子（0随机，1黑，2白）")


class LeaderboardItem(BaseModel):
    """天梯排行榜单条记录。"""
    rank: int
    user_id: str
    username: str
    tier: str
    sub_tier: int
    stars: int
    display_rank: str
    total_matches: int
    win_matches: int
    win_rate: float


class WSMessage(BaseModel):
    """WebSocket 通用消息数据载荷结构。"""
    action: str = Field(..., description="操作指令动作标识")
    room_id: Optional[str] = Field(None, description="目标房间号")
    payload: Dict[str, Any] = Field(default_factory=dict, description="业务数据字段")
