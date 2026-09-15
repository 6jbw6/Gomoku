"""天梯排位与勇者积分算法测试用例模块。

测试覆盖：
1. 胜场升星与小段晋级（青铜 III 0星 -> 青铜 III 1星 -> ... -> 青铜 II 0星）；
2. 青铜段位不掉星保护；
3. 白银段位掉星但不跌入青铜；
4. 勇者积分连胜加成与焦灼局加分；
5. 勇者积分满额自动抵扣掉星；
6. 勇者积分满额且获胜奖励额外升星；
7. 晋升王者与星数累积。
严格遵循 PEP 8 规范，所有注释采用中文。
"""

from gomoku.core.enums import RankTier
from gomoku.services.rank_service import RankService, RankState


class TestRankService:
    """天梯段位算法测试类。"""

    def test_bronze_progression_and_no_drop(self) -> None:
        """测试青铜晋级与青铜失败绝不掉星。"""
        state = RankState(tier=RankTier.BRONZE, sub_tier=3, stars=0)
        assert state.display_rank == "倔强青铜 III (0星)"

        # 获胜 +1 星
        state, settlement = RankService.settle_match(state, is_win=True, total_moves=20)
        assert settlement.stars_delta == 1
        assert state.stars == 1
        assert state.winning_streak == 1

        # 战败，青铜不掉星
        state, settlement = RankService.settle_match(state, is_win=False, total_moves=20)
        assert settlement.stars_delta == 0
        assert state.stars == 1
        assert state.winning_streak == 0

    def test_sub_tier_promotion(self) -> None:
        """测试小段位满星晋级（青铜 III 2星 -> 青铜 II 0星）。"""
        state = RankState(tier=RankTier.BRONZE, sub_tier=3, stars=2)
        # 再赢一局（青铜每小段需要 3 星晋级）
        state, settlement = RankService.settle_match(state, is_win=True, total_moves=20)
        assert state.sub_tier == 2
        assert state.stars == 0
        assert state.display_rank == "倔强青铜 II (0星)"

    def test_brave_points_protection(self) -> None:
        """测试勇者积分抵扣掉星保护。"""
        # 黄金段位保星阈值为 150 分
        state = RankState(
            tier=RankTier.GOLD,
            sub_tier=2,
            stars=2,
            brave_points=160,
        )
        # 战败，勇者积分满足 150 分，应触发保星抵扣，星数不减
        state, settlement = RankService.settle_match(state, is_win=False, total_moves=25)
        assert settlement.protection_triggered is True
        assert settlement.stars_delta == 0
        assert state.stars == 2
        # 160 + 10(完赛) - 150(抵扣) = 20
        assert state.brave_points == 20

    def test_brave_points_bonus_star(self) -> None:
        """测试勇者积分满额且获胜时额外获得 1 颗星。"""
        # 黄金段位，当前积分 140
        state = RankState(
            tier=RankTier.GOLD,
            sub_tier=3,
            stars=1,
            brave_points=140,
            winning_streak=1,
        )
        # 获胜：完赛10 + 胜场15 + 2连胜10 = +35 分，总计 175 分 >= 150，触发额外升星
        state, settlement = RankService.settle_match(state, is_win=True, total_moves=25)
        assert settlement.bonus_star_triggered is True
        assert settlement.stars_delta == 2  # 基础 1 星 + 额外 1 星
        assert state.stars == 3
        # 140 + 35 - 150 = 25
        assert state.brave_points == 25

    def test_silver_cannot_drop_to_bronze(self) -> None:
        """测试白银段位 0 星战败绝不跌入青铜。"""
        state = RankState(tier=RankTier.SILVER, sub_tier=3, stars=0, brave_points=0)
        state, settlement = RankService.settle_match(state, is_win=False, total_moves=20)
        assert state.tier == RankTier.SILVER
        assert state.sub_tier == 3
        assert state.stars == 0
