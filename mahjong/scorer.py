"""
台式麻將北部算法 - 計分引擎
Taiwan Mahjong Northern Rules Scoring Engine

台數規則對照表
───────────────────────────────────────────────────────
類別        條件                      台數
───────────────────────────────────────────────────────
莊台        莊家胡牌                  +1
            連莊 n 次               +n*2+1 (取代基本莊1台)
牌型台      門清                      +1
            獨聽                      +1
            平胡                      +2
            碰碰胡                    +4
花台        正花                      每張+1
            花槓                      +1 (額外，含自花位置)
            七搶一 (7花)              +8
            八仙過海 (8花)            +8
天地人胡    天胡                      +24
            地胡                      +16
            人胡                      +16
            天聽                      +8
            地聽                      +4
三元台      三元刻 (一組)             +1
            小三元                    +4
            大三元                    +8
暗刻台      三暗刻                    +2
            四暗刻                    +5
            五暗刻                    +8
風刻台      圈風刻                    +1
            門風刻                    +1
自摸台      自摸                      +1
            門清自摸 (門清+自摸+不求人) +3 (含門清1+自摸1+不求人1)
            海底撈月                  +1
            槓上開花                  +1
一色台      混一色                    +4
            清一色                    +8
            字一色                    +16
胡牌方式    全求人                    +1
            搶槓                      +1
            不求人 (含自摸)           +1
四喜台      小四喜                    +8
            大四喜                    +16
特殊        哩咕哩咕 (4槓)            +8
            河底撈魚 (最後1張被放槍)  +1
───────────────────────────────────────────────────────
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple
from .tiles import (
    Suit, Wind, Dragon, MeldType, Meld, Hand, GameState, Tile
)


@dataclass
class ScoringDetail:
    """單項台數明細"""
    category: str       # 類別
    description: str    # 說明
    points: int         # 台數


@dataclass
class ScoreResult:
    """計分結果"""
    total: int
    details: List[ScoringDetail] = field(default_factory=list)

    def add(self, category: str, description: str, points: int):
        self.details.append(ScoringDetail(category, description, points))
        self.total += points

    def report(self) -> str:
        lines = ["=" * 50, "台式麻將北部算法 計分結果", "=" * 50]
        for d in self.details:
            lines.append(f"  [{d.category}] {d.description:<20} +{d.points} 台")
        lines.append("-" * 50)
        lines.append(f"  合計：{self.total} 台")
        lines.append("=" * 50)
        return "\n".join(lines)


# ─── Main Scorer ──────────────────────────────────────────────────────────────

class MahjongScorer:
    """台式麻將北部算法計分引擎"""

    def score(self, hand: Hand, state: GameState) -> ScoreResult:
        result = ScoreResult(total=0)

        # 天地人胡 (最高優先，若命中直接回傳)
        if self._score_heaven_earth(hand, state, result):
            return result

        # 莊台
        self._score_dealer(state, result)

        # 牌型台
        self._score_hand_type(hand, state, result)

        # 花台
        self._score_flowers(hand, state, result)

        # 三元台
        self._score_dragons(hand, result)

        # 四喜台
        self._score_four_winds(hand, result)

        # 暗刻台
        self._score_concealed_sets(hand, result)

        # 風刻台
        self._score_wind_sets(hand, state, result)

        # 一色台
        self._score_flush(hand, result)

        # 特殊胡牌方式
        self._score_win_method(hand, state, result)

        # 特殊牌型
        self._score_special(hand, state, result)

        return result

    # ─── 莊台 ────────────────────────────────────────────────────────────────

    def _score_dealer(self, state: GameState, result: ScoreResult):
        if not state.is_dealer:
            return
        if state.consecutive_wins > 0:
            pts = state.consecutive_wins * 2 + 1
            result.add("莊台", f"連莊{state.consecutive_wins}次", pts)
        else:
            result.add("莊台", "莊家", 1)

    # ─── 天地人胡 ─────────────────────────────────────────────────────────────

    def _score_heaven_earth(self, hand: Hand, state: GameState,
                            result: ScoreResult) -> bool:
        if state.tianhu:
            result.add("天地人胡", "天胡", 24)
            return True
        if state.dihu:
            result.add("天地人胡", "地胡", 16)
            return True
        if state.renhu:
            result.add("天地人胡", "人胡", 16)
            return True
        if state.tiantin:
            result.add("天地人胡", "天聽", 8)
        if state.ditin:
            result.add("天地人胡", "地聽", 4)
        return False

    # ─── 牌型台 ──────────────────────────────────────────────────────────────

    def _score_hand_type(self, hand: Hand, state: GameState, result: ScoreResult):
        is_pinhu = self._is_pinhu(hand)
        is_pengpenghu = self._is_pengpenghu(hand)
        is_menqing = hand.is_fully_concealed

        # 碰碰胡 與 平胡 互斥 (碰碰胡優先)
        if is_pengpenghu:
            result.add("牌型台", "碰碰胡", 4)
        elif is_pinhu:
            result.add("牌型台", "平胡", 2)

        if is_menqing:
            result.add("牌型台", "門清", 1)

        if state.dutin:
            result.add("牌型台", "獨聽", 1)

    def _is_pinhu(self, hand: Hand) -> bool:
        """
        平胡：四組順子 + 一對（且對子非三元/風牌）
        """
        melds = hand.melds
        if len(melds) != 4:
            return False
        for m in melds:
            if m.meld_type != MeldType.SHUNTZU:
                return False
        if hand.pair is None:
            return False
        pair_tile = hand.pair.base_tile
        if pair_tile.suit in (Suit.DRAGON, Suit.WIND):
            return False
        return True

    def _is_pengpenghu(self, hand: Hand) -> bool:
        """碰碰胡：四組刻子/槓子 + 一對"""
        melds = hand.melds
        if len(melds) != 4:
            return False
        for m in melds:
            if m.meld_type not in (MeldType.KEZI, MeldType.GANGZI):
                return False
        return True

    # ─── 花台 ────────────────────────────────────────────────────────────────

    def _score_flowers(self, hand: Hand, state: GameState, result: ScoreResult):
        flower_tiles = hand.flowers
        n_flowers = len(flower_tiles)

        if n_flowers == 0:
            return

        if n_flowers == 8:
            result.add("花台", "八仙過海 (8花)", 8)
            return

        if n_flowers == 7:
            result.add("花台", "七搶一 (7花)", 8)
            return

        # 正花 +1 each
        result.add("花台", f"正花 x{n_flowers}", n_flowers)

        # 花槓：玩家座位對應的花號 (東1梅春, 南2蘭夏, 西3菊秋, 北4竹冬)
        seat_flowers = self._player_seat_flowers(state.seat_number)
        has_kong_flower = all(fn in [t.flower_num for t in flower_tiles]
                              for fn in seat_flowers)
        if has_kong_flower and n_flowers >= 2:
            result.add("花台", "花槓", 1)

    def _player_seat_flowers(self, seat_number: int) -> List[int]:
        """
        每個座位對應的正花號
        東1: 梅(1)+春(5)  南2: 蘭(2)+夏(6)
        西3: 菊(3)+秋(7)  北4: 竹(4)+冬(8)
        """
        mapping = {1: [1, 5], 2: [2, 6], 3: [3, 7], 4: [4, 8]}
        return mapping.get(seat_number, [])

    # ─── 三元台 ──────────────────────────────────────────────────────────────

    def _score_dragons(self, hand: Hand, result: ScoreResult):
        dragon_kezi: List[Meld] = []
        for m in hand.melds:
            if m.base_tile.suit == Suit.DRAGON and m.meld_type in (
                    MeldType.KEZI, MeldType.GANGZI):
                dragon_kezi.append(m)

        count = len(dragon_kezi)
        if count == 3:
            result.add("三元台", "大三元", 8)
        elif count == 2:
            # 小三元: 2刻 + 對子是三元牌
            if hand.pair and hand.pair.base_tile.suit == Suit.DRAGON:
                result.add("三元台", "小三元", 4)
            else:
                for _ in range(count):
                    result.add("三元台", "三元刻", 1)
        elif count == 1:
            result.add("三元台", "三元刻", 1)

    # ─── 四喜台 ──────────────────────────────────────────────────────────────

    def _score_four_winds(self, hand: Hand, result: ScoreResult):
        wind_kezi: List[Meld] = []
        has_wind_pair = (hand.pair and hand.pair.base_tile.suit == Suit.WIND)
        for m in hand.melds:
            if m.base_tile.suit == Suit.WIND and m.meld_type in (
                    MeldType.KEZI, MeldType.GANGZI):
                wind_kezi.append(m)

        count = len(wind_kezi)
        if count == 4:
            result.add("四喜台", "大四喜", 16)
        elif count == 3 and has_wind_pair:
            result.add("四喜台", "小四喜", 8)

    # ─── 暗刻台 ──────────────────────────────────────────────────────────────

    def _score_concealed_sets(self, hand: Hand, result: ScoreResult):
        anke_count = sum(
            1 for m in hand.melds
            if m.is_concealed and m.meld_type in (MeldType.KEZI, MeldType.GANGZI)
        )
        if anke_count >= 5:
            result.add("暗刻台", "五暗刻", 8)
        elif anke_count == 4:
            result.add("暗刻台", "四暗刻", 5)
        elif anke_count == 3:
            result.add("暗刻台", "三暗刻", 2)

    # ─── 風刻台 ──────────────────────────────────────────────────────────────

    def _score_wind_sets(self, hand: Hand, state: GameState, result: ScoreResult):
        for m in hand.melds:
            if m.base_tile.suit != Suit.WIND:
                continue
            if m.meld_type not in (MeldType.KEZI, MeldType.GANGZI):
                continue
            wind_val = m.base_tile.value  # Wind enum
            if wind_val == state.round_wind:
                result.add("風刻台", f"圈風刻({wind_val.value})", 1)
            if wind_val == state.seat_wind:
                result.add("風刻台", f"門風刻({wind_val.value})", 1)

    # ─── 一色台 ──────────────────────────────────────────────────────────────

    def _score_flush(self, hand: Hand, result: ScoreResult):
        # 只看非花牌
        suits_in_hand = set()
        has_honor = False
        for m in hand.all_melds():
            t = m.base_tile
            if t.suit in (Suit.WAN, Suit.TIAO, Suit.BING):
                suits_in_hand.add(t.suit)
            elif t.suit in (Suit.WIND, Suit.DRAGON):
                has_honor = True

        n_suits = len(suits_in_hand)

        if n_suits == 0 and has_honor:
            result.add("一色台", "字一色", 16)
        elif n_suits == 1 and not has_honor:
            result.add("一色台", "清一色", 8)
        elif n_suits == 1 and has_honor:
            result.add("一色台", "混一色", 4)

    # ─── 胡牌方式 ─────────────────────────────────────────────────────────────

    def _score_win_method(self, hand: Hand, state: GameState, result: ScoreResult):
        is_menqing = hand.is_fully_concealed

        if hand.is_robbing_kong:
            result.add("胡牌方式", "搶槓", 1)

        if hand.is_self_draw:
            if is_menqing:
                # 門清自摸 = 門清1 + 自摸1 + 不求人1 (已在牌型台加了門清1)
                # 這裡補 自摸+不求人
                result.add("自摸台", "自摸", 1)
                result.add("胡牌方式", "不求人", 1)
            else:
                result.add("自摸台", "自摸", 1)
            if hand.is_last_tile:
                result.add("自摸台", "海底撈月", 1)
            if hand.is_after_kong:
                result.add("自摸台", "槓上開花", 1)
        else:
            if hand.is_last_tile:
                result.add("特殊", "河底撈魚", 1)
            # 全求人：門清且沒有自摸，由別人放槍
            n_exposed = len(hand.exposed_melds())
            if n_exposed == 4:
                result.add("胡牌方式", "全求人", 1)
            elif is_menqing and not hand.is_self_draw:
                result.add("胡牌方式", "不求人", 1)

    # ─── 特殊牌型 ─────────────────────────────────────────────────────────────

    def _score_special(self, hand: Hand, state: GameState, result: ScoreResult):
        # 哩咕哩咕 (4槓)
        kong_count = sum(1 for m in hand.melds if m.meld_type == MeldType.GANGZI)
        if kong_count == 4:
            result.add("特殊", "哩咕哩咕 (4槓)", 8)


# ─── Convenience function ─────────────────────────────────────────────────────

def calculate_score(hand: Hand, state: GameState) -> ScoreResult:
    """計算麻將台數的便利函式"""
    scorer = MahjongScorer()
    return scorer.score(hand, state)
