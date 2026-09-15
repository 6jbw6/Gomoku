"""天梯排位与勇者积分结算服务模块。

包含经典星级段位梯队算法、升星/降星判定、掉星保护与勇者积分抵扣机制。
遵循 SOLID 原则中的单一职责原则（SRP）。
严格遵循 PEP 8 规范，所有注释与文档字符串均采用中文。
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from gomoku.core.enums import RankTier


@dataclass
class RankState:
    """玩家段位状态实体。

    Attributes:
        tier: 段位主大段（如 荣耀黄金、永恒钻石）
        sub_tier: 子小段（从低到高递进，如 4 代表 IV，1 代表 I；王者及以上固定为 1）
        stars: 当前小段内的星数（王者及以上表示总星数）
        brave_points: 当前累积的勇者积分
        winning_streak: 当前连胜场次
        total_matches: 总排位对局数
        win_matches: 总获胜场次
    """
    tier: RankTier
    sub_tier: int
    stars: int
    brave_points: int = 0
    winning_streak: int = 0
    total_matches: int = 0
    win_matches: int = 0

    @property
    def win_rate(self) -> float:
        """获取胜率百分比（0.0 - 100.0）。"""
        if self.total_matches == 0:
            return 0.0
        return round((self.win_matches / self.total_matches) * 100, 1)

    @property
    def display_rank(self) -> str:
        """获取格式化段位全称，例如：'荣耀黄金 II (3星)' 或 '最强王者 (18星)'。"""
        # 王者梯队直接显示星数
        if self.tier in (
            RankTier.KING,
            RankTier.GLORIOUS_KING,
            RankTier.LEGENDARY_KING,
            RankTier.PEERLESS_KING,
        ):
            return f"{self.tier.value} ({self.stars}星)"

        sub_roman_map = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}
        roman = sub_roman_map.get(self.sub_tier, str(self.sub_tier))
        return f"{self.tier.value} {roman} ({self.stars}星)"


@dataclass(frozen=True)
class RankSettlementResult:
    """排位对局结算结果数据对象。

    Attributes:
        is_win: 当局是否获胜
        old_rank: 结算前段位全称
        new_rank: 结算后段位全称
        stars_delta: 星数变动（+1, +2, -1, 0）
        brave_points_gained: 当局获得勇者积分
        brave_points_consumed: 当局抵扣/升级消耗勇者积分
        current_brave_points: 结算后最新勇者积分
        protection_triggered: 是否触发了掉星保护抵扣
        bonus_star_triggered: 是否触发了满额勇者积分额外升星
    """
    is_win: bool
    old_rank: str
    new_rank: str
    stars_delta: int
    brave_points_gained: int
    brave_points_consumed: int
    current_brave_points: int
    protection_triggered: bool
    bonus_star_triggered: bool


class RankService:
    """天梯竞技段位规则计算服务。"""

    # 段位大段从低到高顺序
    TIER_ORDER: List[RankTier] = [
        RankTier.BRONZE,
        RankTier.SILVER,
        RankTier.GOLD,
        RankTier.PLATINUM,
        RankTier.DIAMOND,
        RankTier.MASTER,
        RankTier.KING,
        RankTier.GLORIOUS_KING,
        RankTier.LEGENDARY_KING,
        RankTier.PEERLESS_KING,
    ]

    # 各大段的子段位数：青铜/白银为 3 段 (III->II->I)；黄金/铂金为 4 段 (IV->I)；钻石/星耀为 5 段 (V->I)
    SUB_TIER_COUNTS: Dict[RankTier, int] = {
        RankTier.BRONZE: 3,
        RankTier.SILVER: 3,
        RankTier.GOLD: 4,
        RankTier.PLATINUM: 4,
        RankTier.DIAMOND: 5,
        RankTier.MASTER: 5,
        RankTier.KING: 1,
        RankTier.GLORIOUS_KING: 1,
        RankTier.LEGENDARY_KING: 1,
        RankTier.PEERLESS_KING: 1,
    }

    # 各大段每小段升星所需星数
    STARS_PER_SUB_TIER: Dict[RankTier, int] = {
        RankTier.BRONZE: 3,
        RankTier.SILVER: 3,
        RankTier.GOLD: 4,
        RankTier.PLATINUM: 4,
        RankTier.DIAMOND: 5,
        RankTier.MASTER: 5,
        RankTier.KING: 9999,  # 王者星数连续累加，不设子段位截断
        RankTier.GLORIOUS_KING: 9999,
        RankTier.LEGENDARY_KING: 9999,
        RankTier.PEERLESS_KING: 9999,
    }

    # 勇者积分保星/升星阈值
    BRAVE_POINTS_CAP: Dict[RankTier, int] = {
        RankTier.BRONZE: 100,
        RankTier.SILVER: 120,
        RankTier.GOLD: 150,
        RankTier.PLATINUM: 200,
        RankTier.DIAMOND: 300,
        RankTier.MASTER: 300,
        RankTier.KING: 400,
        RankTier.GLORIOUS_KING: 400,
        RankTier.LEGENDARY_KING: 400,
        RankTier.PEERLESS_KING: 400,
    }

    @classmethod
    def calculate_brave_points_gained(
        cls,
        is_win: bool,
        winning_streak: int,
        total_moves: int,
    ) -> int:
        """计算单局对战获得的勇者积分。

        Args:
            is_win: 是否获胜
            winning_streak: 当前连胜场次（获胜后包含当局）
            total_moves: 对局总手数

        Returns:
            所获勇者积分总量
        """
        # 完赛基础表现分
        points = 10

        if is_win:
            # 获胜奖励
            points += 15
            # 连胜递增奖励
            if winning_streak >= 4:
                points += 30
            elif winning_streak == 3:
                points += 20
            elif winning_streak == 2:
                points += 10

        # 焦灼对弈鼓励分（手数超 60 手）
        if total_moves >= 60:
            points += 5

        return points

    @classmethod
    def settle_match(
        cls,
        current_state: RankState,
        is_win: bool,
        total_moves: int,
    ) -> Tuple[RankState, RankSettlementResult]:
        """对排位赛结果进行统一结算计算（纯业务函数）。

        Args:
            current_state: 玩家当前段位状态
            is_win: 本局是否获胜
            total_moves: 本局总下子手数

        Returns:
            (结算后的全新 RankState, 结算明细对象 RankSettlementResult)
        """
        old_display = current_state.display_rank
        tier = current_state.tier
        sub_tier = current_state.sub_tier
        stars = current_state.stars
        brave_points = current_state.brave_points
        streak = current_state.winning_streak
        total_matches = current_state.total_matches + 1
        win_matches = current_state.win_matches + (1 if is_win else 0)

        stars_delta = 0
        points_consumed = 0
        protection_triggered = False
        bonus_star_triggered = False

        if is_win:
            # 胜场：连胜数累加
            streak += 1
            points_gained = cls.calculate_brave_points_gained(
                is_win=True,
                winning_streak=streak,
                total_moves=total_moves,
            )
            brave_points += points_gained
            stars_delta += 1  # 基础胜利 +1 星

            threshold = cls.BRAVE_POINTS_CAP.get(tier, 300)
            # 勇者积分满额且获胜，额外赠送一颗星并扣除阈值积分
            if brave_points >= threshold:
                brave_points -= threshold
                points_consumed += threshold
                stars_delta += 1
                bonus_star_triggered = True

            # 统一执行加星与升段推演
            tier, sub_tier, stars = cls._add_stars(tier, sub_tier, stars, stars_delta)
        else:
            # 败场：连胜归零
            streak = 0
            points_gained = cls.calculate_brave_points_gained(
                is_win=False,
                winning_streak=0,
                total_moves=total_moves,
            )
            brave_points += points_gained

            # 青铜段位绝不掉星
            if tier == RankTier.BRONZE:
                stars_delta = 0
            else:
                threshold = cls.BRAVE_POINTS_CAP.get(tier, 300)
                # 若勇者积分达到抵扣线，触发保星抵扣
                if brave_points >= threshold:
                    brave_points -= threshold
                    points_consumed += threshold
                    protection_triggered = True
                    stars_delta = 0
                else:
                    # 正常扣除 1 星并处理降段
                    stars_delta = -1
                    tier, sub_tier, stars = cls._remove_stars(tier, sub_tier, stars, 1)

        new_state = RankState(
            tier=tier,
            sub_tier=sub_tier,
            stars=stars,
            brave_points=brave_points,
            winning_streak=streak,
            total_matches=total_matches,
            win_matches=win_matches,
        )

        settlement = RankSettlementResult(
            is_win=is_win,
            old_rank=old_display,
            new_rank=new_state.display_rank,
            stars_delta=stars_delta,
            brave_points_gained=points_gained,
            brave_points_consumed=points_consumed,
            current_brave_points=brave_points,
            protection_triggered=protection_triggered,
            bonus_star_triggered=bonus_star_triggered,
        )

        return new_state, settlement

    @classmethod
    def _is_king_tier(cls, tier: RankTier) -> bool:
        """判断是否已属于王者以上梯队。"""
        return tier in (
            RankTier.KING,
            RankTier.GLORIOUS_KING,
            RankTier.LEGENDARY_KING,
            RankTier.PEERLESS_KING,
        )

    @classmethod
    def _get_king_tier_by_stars(cls, stars: int) -> RankTier:
        """根据王者总星数换算对应王者称号。"""
        if stars >= 100:
            return RankTier.PEERLESS_KING
        if stars >= 50:
            return RankTier.LEGENDARY_KING
        if stars >= 25:
            return RankTier.GLORIOUS_KING
        return RankTier.KING

    @classmethod
    def _add_stars(
        cls,
        tier: RankTier,
        sub_tier: int,
        stars: int,
        delta: int,
    ) -> Tuple[RankTier, int, int]:
        """加星与升段递进计算。"""
        if delta <= 0:
            return tier, sub_tier, stars

        # 王者梯队直接累加星数并更新称号
        if cls._is_king_tier(tier):
            total_king_stars = stars + delta
            new_tier = cls._get_king_tier_by_stars(total_king_stars)
            return new_tier, 1, total_king_stars

        stars += delta
        required_stars = cls.STARS_PER_SUB_TIER[tier]

        while stars >= required_stars:
            stars -= required_stars
            if sub_tier > 1:
                # 子段位晋级（从大数向 1 推进，如 III -> II -> I）
                sub_tier -= 1
            else:
                # 升入下一个主大段
                tier_idx = cls.TIER_ORDER.index(tier)
                next_tier = cls.TIER_ORDER[tier_idx + 1]
                tier = next_tier

                if cls._is_king_tier(tier):
                    # 刚升入王者，剩余星数即为王者星数
                    return cls._get_king_tier_by_stars(stars), 1, stars

                # 进入新大段的最大小段（如黄金从 IV 开始）
                sub_tier = cls.SUB_TIER_COUNTS[tier]
                required_stars = cls.STARS_PER_SUB_TIER[tier]

        return tier, sub_tier, stars

    @classmethod
    def _remove_stars(
        cls,
        tier: RankTier,
        sub_tier: int,
        stars: int,
        delta: int,
    ) -> Tuple[RankTier, int, int]:
        """扣星与降段衰减计算。"""
        if delta <= 0:
            return tier, sub_tier, stars

        # 王者梯队
        if cls._is_king_tier(tier):
            if stars >= delta:
                total_king_stars = stars - delta
                new_tier = cls._get_king_tier_by_stars(total_king_stars)
                return new_tier, 1, total_king_stars
            else:
                # 跌出王者，降入至尊星耀 I（满星-1）
                tier = RankTier.MASTER
                sub_tier = 1
                stars = cls.STARS_PER_SUB_TIER[tier] - 1
                return tier, sub_tier, stars

        stars -= delta
        if stars >= 0:
            return tier, sub_tier, stars

        # 触发当前子段位向下跌落
        max_sub = cls.SUB_TIER_COUNTS[tier]
        if sub_tier < max_sub:
            # 降入更低的小段（如 II 跌到 III）
            sub_tier += 1
            stars = cls.STARS_PER_SUB_TIER[tier] - 1
            return tier, sub_tier, stars

        # 若已经在当前大段的最低子段位（如黄金 IV 0星），尝试降大段
        tier_idx = cls.TIER_ORDER.index(tier)
        if tier_idx > 0:
            lower_tier = cls.TIER_ORDER[tier_idx - 1]
            # 白银段位绝不跌入青铜
            if tier == RankTier.SILVER and lower_tier == RankTier.BRONZE:
                return tier, sub_tier, 0

            tier = lower_tier
            sub_tier = 1  # 降入上一大段的 I 段
            stars = cls.STARS_PER_SUB_TIER[tier] - 1
            return tier, sub_tier, stars

        # 最低段位保底（青铜 III 0星）
        return tier, sub_tier, 0
