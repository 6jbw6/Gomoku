"""FastAPI 依赖注入与安全鉴权模块。

使用 PyJWT 生成与校验令牌，使用 PassLib Bcrypt 散列密码。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from gomoku.config import settings
from gomoku.storage.database import get_db
from gomoku.storage.models import UserModel
from gomoku.storage.repositories import IUserRepository, UserRepository

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Bearer Token 抽取器
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """对原始密码进行安全散列哈希。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希值匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, username: str) -> str:
    """为指定用户生成 JWT 访问令牌。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "name": username,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解析并验证 JWT 访问令牌，若失效或非法返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


async def get_user_repository(
    session: AsyncSession = Depends(get_db),
) -> IUserRepository:
    """FastAPI 依赖：获取用户仓储实例。"""
    return UserRepository(session)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    repo: IUserRepository = Depends(get_user_repository),
) -> Optional[UserModel]:
    """FastAPI 可选依赖：解析当前登录用户，若未登录返回 None。"""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return await repo.get_by_user_id(user_id)


async def get_current_user(
    user: Optional[UserModel] = Depends(get_current_user_optional),
) -> UserModel:
    """FastAPI 严格依赖：必须为有效登录用户，否则抛出 401 Unauthorized。"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录或登录令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
