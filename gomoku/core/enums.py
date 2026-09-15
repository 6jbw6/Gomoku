"""五子棋核心枚举定义模块。

包含棋子颜色、游戏模式、对局状态、胜负原因与天梯排位段位。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from enum import Enum, IntEnum, unique


@unique
class PieceColor(IntEnum):
    """棋盘交点状态及玩家棋子颜色枚举。"""
    EMPTY = 0   # 空位
    BLACK = 1   # 黑子（先手）
    WHITE = 2   # 白子（后手）

    @property
    def opponent(self) -> "PieceColor":
        """获取对手棋子颜色。"""
        if self == PieceColor.BLACK:
            return PieceColor.WHITE
        if self == PieceColor.WHITE:
            return PieceColor.BLACK
        return PieceColor.EMPTY

    @property
    def display_name(self) -> str:
        """获取中文显示名称。"""
        names = {
            PieceColor.EMPTY: "空",
            PieceColor.BLACK: "黑子",
            PieceColor.WHITE: "白子",
        }
        return names[self]


@unique
class GameMode(str, Enum):
    """对战模式枚举。"""
    FRIEND = "friend"      # 好友开房对战（自定义规则、房间码分享）
    CASUAL = "casual"      # 休闲单人匹配（快速对战，超时AI替补）
    RANKED = "ranked"      # 天梯排位赛（胜负计星，勇者积分）


@unique
class GameStatus(str, Enum):
    """房间与对局生命周期状态枚举。"""
    WAITING = "waiting"        # 等待玩家进入或准备
    PLAYING = "playing"        # 正在激烈对弈中
    FINISHED = "finished"      # 正常完赛并已结算
    ABORTED = "aborted"        # 对局异常终止或房间解散


@unique
class WinReason(str, Enum):
    """胜负判定原因枚举。"""
    FIVE_IN_ROW = "five_in_row"  # 五子连珠获胜
    RESIGN = "resign"            # 对手主动认输
    TIMEOUT = "timeout"          # 步时耗尽超时判负
    DRAW = "draw"                # 双方协商和棋或棋盘填满平局
    DISCONNECT = "disconnect"    # 玩家离线超时判负


@unique
class RankTier(str, Enum):
    """天梯排位段位层级枚举（经典星级体系，去外部品牌化）。"""
    BRONZE = "倔强青铜"
    SILVER = "秩序白银"
    GOLD = "荣耀黄金"
    PLATINUM = "尊贵铂金"
    DIAMOND = "永恒钻石"
    MASTER = "至尊星耀"
    KING = "最强王者"
    GLORIOUS_KING = "荣耀王者"
    LEGENDARY_KING = "传奇王者"
    PEERLESS_KING = "绝世王者"
