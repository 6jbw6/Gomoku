"""五子棋天梯竞技平台启动脚本。

通过 Uvicorn 异步服务引擎启动应用。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import uvicorn
from gomoku.config import settings

if __name__ == "__main__":
    print(f"==================================================")
    print(f"  {settings.PROJECT_NAME} 服务启动中...")
    print(f"  本地访问地址: http://127.0.0.1:{settings.PORT}")
    print(f"==================================================")
    uvicorn.run(
        "gomoku.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info",
    )
