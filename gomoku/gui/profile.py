"""五子棋桌面端本地档案与排位状态管理器。

对接领域 RankService 算法，负责段位换算、勇者积分增减、战绩持久化与天梯数据生成。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

import json
import os
import random
from typing import Any, Dict, List, Tuple
from gomoku.core.enums import RankTier
from gomoku.services.rank_service import (
    RankService,
    RankSettlementResult,
    RankState,
)


class UserProfileManager:
    """本地棋手档案管理器。"""

    def __init__(self, filename: str = "gomoku_profile.json") -> None:
        """初始化档案并自动恢复或生成数据。"""
        self.filename = filename
        self.username: str = f"棋客_{random.randint(1000, 9999):04x}"
        self.state: RankState = RankState(
            tier=RankTier.BRONZE,
            sub_tier=3,
            stars=0,
            brave_points=0,
            winning_streak=0,
            total_matches=0,
            win_matches=0,
        )
        self.load()

    def load(self) -> None:
        """从本地磁盘文件加载档案。"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.username = data.get("username", self.username)
                    tier_str = data.get("tier", RankTier.BRONZE.value)
                    # 匹配 RankTier
                    tier = RankTier.BRONZE
                    for t in RankTier:
                        if t.value == tier_str or t.name == tier_str:
                            tier = t
                            break

                    self.state = RankState(
                        tier=tier,
                        sub_tier=int(data.get("sub_tier", 3)),
                        stars=int(data.get("stars", 0)),
                        brave_points=int(data.get("brave_points", 0)),
                        winning_streak=int(data.get("winning_streak", 0)),
                        total_matches=int(data.get("total_matches", 0)),
                        win_matches=int(data.get("win_matches", 0)),
                    )
            except Exception as err:
                print(f"[档案读取提示] 读取本地档案异常，使用默认档案: {err}")

    def save(self) -> None:
        """将当前战绩档案写入本地磁盘。"""
        data = {
            "username": self.username,
            "tier": self.state.tier.value,
            "sub_tier": self.state.sub_tier,
            "stars": self.state.stars,
            "brave_points": self.state.brave_points,
            "winning_streak": self.state.winning_streak,
            "total_matches": self.state.total_matches,
            "win_matches": self.state.win_matches,
        }
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as err:
            print(f"[档案写入警告] 保存本地档案失败: {err}")

    @property
    def display_rank(self) -> str:
        """获取当前格式化段位全称。"""
        return self.state.display_rank

    @property
    def brave_points_cap(self) -> int:
        """获取当前段位的勇者积分上限。"""
        return RankService.BRAVE_POINTS_CAP.get(self.state.tier, 100)

    @property
    def win_rate(self) -> float:
        """计算胜率百分比。"""
        return self.state.win_rate

    def settle_match(
        self, is_winner: bool, moves_count: int
    ) -> Tuple[RankState, RankSettlementResult]:
        """执行天梯对局结算并持久化更新档案。"""
        new_state, settlement = RankService.settle_match(
            current_state=self.state,
            is_win=is_winner,
            total_moves=moves_count,
        )
        self.state = new_state
        self.save()
        return new_state, settlement

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """获取全服天梯大师榜（按星数降序排列，仅展示棋客数据）。"""
        mock_data = [
            {"username": "棋客_8988", "stars": 128, "tier": "绝世王者", "rate": "87.5% (210/240)"},
            {"username": "棋客_7721", "stars": 85, "tier": "传奇王者", "rate": "83.3% (150/180)"},
            {"username": "棋客_3319", "stars": 54, "tier": "传奇王者", "rate": "78.4% (98/125)"},
            {"username": "棋客_6620", "stars": 32, "tier": "荣耀王者", "rate": "73.0% (65/89)"},
            {"username": "棋客_1204", "stars": 18, "tier": "最强王者", "rate": "70.0% (42/60)"},
            {
                "username": self.username,
                "stars": self.state.stars,
                "tier": self.display_rank,
                "rate": f"{self.win_rate}% ({self.state.win_matches}/{self.state.total_matches})",
            },
        ]

        # 排序并返回
        mock_data.sort(key=lambda x: x["stars"], reverse=True)
        res = []
        for idx, item in enumerate(mock_data, start=1):
            res.append({
                "rank": idx,
                "username": item["username"],
                "tier_name": item["tier"],
                "win_rate": item["rate"],
                "stars": item["stars"],
            })
        return res
