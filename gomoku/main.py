"""FastAPI 核心应用入口与装配模块。

包含生命周期调度、路由装配、静态前端挂载与 CORS 中间件配置。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from gomoku.api.routes_auth import router as auth_router
from gomoku.api.routes_rank import router as rank_router
from gomoku.api.ws_handler import router as ws_router
from gomoku.config import settings
from gomoku.services.match_service import matchmaking_service
from gomoku.storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 异步生命周期管理（启动初始化与关闭资源释放）。"""
    # 启动时：初始化数据库表并开启后台匹配服务
    await init_db()
    await matchmaking_service.start()
    yield
    # 关闭时：优雅停止匹配轮询
    await matchmaking_service.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 与 WebSocket 路由
app.include_router(auth_router)
app.include_router(rank_router)
app.include_router(ws_router)

# 挂载 Web 表现层静态前端文件
WEB_DIR = Path(__file__).resolve().parent / "web"
if not WEB_DIR.exists():
    WEB_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
