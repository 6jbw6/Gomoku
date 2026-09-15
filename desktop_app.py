"""五子棋天梯竞技平台桌面端启动入口。

基于 Pygame 引擎驱动的原生桌面客户端。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from gomoku.gui.app import GomokuApp

if __name__ == "__main__":
    app = GomokuApp()
    app.run()
