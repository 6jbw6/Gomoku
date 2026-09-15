"""五子棋业务服务模块。

包含段位积分换算与天梯排位服务。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from gomoku.services.rank_service import (
    RankService,
    RankSettlementResult,
    RankState,
)

__all__ = [
    "RankService",
    "RankState",
    "RankSettlementResult",
]
