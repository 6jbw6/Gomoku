"""用户认证与个人信息路由模块。

包含免密游客快速登录、正式账号注册、密码登录与个人信息获取。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from gomoku.api.deps import (
    create_access_token,
    get_current_user,
    get_user_repository,
    hash_password,
    verify_password,
)
from gomoku.api.schemas import (
    GuestLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
)
from gomoku.core.enums import RankTier
from gomoku.services.rank_service import RankState
from gomoku.storage.models import UserModel
from gomoku.storage.repositories import IUserRepository

router = APIRouter(prefix="/api/auth", tags=["用户与认证"])


def build_user_profile_response(user: UserModel) -> UserProfileResponse:
    """构建用户个人信息视图对象的纯函数。"""
    try:
        tier_enum = RankTier(user.tier)
    except ValueError:
        tier_enum = RankTier.BRONZE

    state = RankState(
        tier=tier_enum,
        sub_tier=user.sub_tier,
        stars=user.stars,
        brave_points=user.brave_points,
        winning_streak=user.winning_streak,
        total_matches=user.total_matches,
        win_matches=user.win_matches,
    )

    return UserProfileResponse(
        user_id=user.user_id,
        username=user.username,
        is_guest=user.is_guest,
        tier=user.tier,
        sub_tier=user.sub_tier,
        stars=user.stars,
        display_rank=state.display_rank,
        brave_points=user.brave_points,
        winning_streak=user.winning_streak,
        total_matches=user.total_matches,
        win_matches=user.win_matches,
        win_rate=state.win_rate,
    )


@router.post("/guest", response_model=TokenResponse, summary="游客一键快速进入")
async def guest_login(
    req: GuestLoginRequest,
    repo: IUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """创建或获取游客账号，并返回专属 JWT 凭证。"""
    user = await repo.create_guest_user(req.nickname)
    token = create_access_token(user.user_id, user.username)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        username=user.username,
        is_guest=True,
    )


@router.post("/register", response_model=TokenResponse, summary="正式账号注册")
async def register(
    req: RegisterRequest,
    repo: IUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """注册正式账号，用户名唯一校验。"""
    existing = await repo.get_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该昵称或用户名已被占用，请尝试其他名称",
        )

    pwd_hash = hash_password(req.password)
    user = await repo.create_user(req.username, pwd_hash)
    token = create_access_token(user.user_id, user.username)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        username=user.username,
        is_guest=False,
    )


@router.post("/login", response_model=TokenResponse, summary="正式账号登录")
async def login(
    req: LoginRequest,
    repo: IUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """通过用户名和密码进行登录鉴权。"""
    user = await repo.get_by_username(req.username)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
        )

    token = create_access_token(user.user_id, user.username)
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        username=user.username,
        is_guest=False,
    )


@router.get("/me", response_model=UserProfileResponse, summary="获取当前登录玩家信息")
async def get_my_profile(
    current_user: UserModel = Depends(get_current_user),
) -> UserProfileResponse:
    """返回当前玩家的完整段位数据与战绩统计。"""
    return build_user_profile_response(current_user)
