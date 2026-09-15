"""系统全局配置模块。

使用 Pydantic Settings 进行环境变量注入与类型强校验。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统全局应用配置类。"""

    # 服务网络配置
    HOST: str = "0.0.0.0"
    PORT: int = 8088
    DEBUG: bool = False
    PROJECT_NAME: str = "五子棋天梯竞技平台"
    VERSION: str = "1.0.0"

    # 安全鉴权与 JWT 令牌配置
    SECRET_KEY: str = "gomoku-secure-production-secret-key-2026-wood-and-gold"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 令牌有效期 7 天

    # 数据库持久化配置（采用轻量高效嵌入式 aiosqlite）
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DB_PATH: Path = BASE_DIR / "gomoku.db"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"

    # 匹配机制与超时控制
    MATCH_TIMEOUT_SECONDS: int = 5  # 休闲匹配等待超时阈值（秒），超时后自动介入智能 AI 替补
    TURN_TIMEOUT_SECONDS_DEFAULT: int = 30  # 默认每步棋落子限时（秒）

    # 棋盘标准规格
    BOARD_SIZE: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# 单例全局配置实例
settings = Settings()
