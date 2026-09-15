"""五子棋天梯竞技平台总启动脚本。

默认启动原生 Pygame 桌面端客户端；可通过参数 --web 启动 Web 网页服务。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import sys

if __name__ == "__main__":
    if "--web" in sys.argv:
        import uvicorn
        from gomoku.config import settings
        print("==================================================")
        print(f"  {settings.PROJECT_NAME} Web 网页服务启动中...")
        print(f"  本地访问地址: http://127.0.0.1:{settings.PORT}")
        print("==================================================")
        uvicorn.run(
            "gomoku.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            log_level="info",
        )
    else:
        from gomoku.gui.app import GomokuApp
        print("==================================================")
        print("  五子棋天梯竞技平台 (Gomoku Arena) 桌面端启动中...")
        print("  引擎架构: Pygame-ce 原生桌面图形客户端")
        print("  视觉主题: 东方金石雅韵与温润沉香木")
        print("==================================================")
        app = GomokuApp()
        app.run()
