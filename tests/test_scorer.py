"""
台式麻將北部算法 - 計分單元測試
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mahjong.tiles import Wind, MeldType, Hand, Meld, GameState, TILES, Tile, Suit
from mahjong.scorer import calculate_score
from mahjong.hand_parser import parse_hand_from_names


def _state(**kwargs) -> GameState:
    defaults = dict(
        round_wind=Wind.EAST,
        seat_wind=Wind.EAST,
        seat_number=1,
        is_dealer=False,
        consecutive_wins=0,
    )
    defaults.update(kwargs)
    return GameState(**defaults)


def _meld(names: list[str], meld_type=MeldType.SHUNTZU,
          concealed=True) -> Meld:
    tiles = [TILES[n] for n in names]
    return Meld(meld_type=meld_type, tiles=tiles, is_concealed=concealed)


# ─── 莊台 ────────────────────────────────────────────────────────────────────

class TestDealer:
    def test_dealer_1_tai(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 東 東 東 中 中".split(),
            winning_tile_name="中",
        )
        state = _state(is_dealer=True, consecutive_wins=0)
        result = calculate_score(hand, state)
        descs = [d.description for d in result.details]
        assert any("莊家" in d for d in descs)

    def test_consecutive_wins(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 東 東 東 中 中".split(),
            winning_tile_name="中",
        )
        state = _state(is_dealer=True, consecutive_wins=2)
        result = calculate_score(hand, state)
        # 連莊2: 2*2+1 = 5台
        dealer_pts = sum(d.points for d in result.details if d.category == "莊台")
        assert dealer_pts == 5


# ─── 牌型台 ──────────────────────────────────────────────────────────────────

class TestHandType:
    def test_pinhu(self):
        # 平胡：4順子 + 非榮譽牌對子
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 1條 2條 3條 7餅 8餅 9餅 5餅 5餅".split(),
            winning_tile_name="5餅",
        )
        state = _state()
        result = calculate_score(hand, state)
        type_pts = sum(d.points for d in result.details
                       if d.description == "平胡")
        assert type_pts == 2

    def test_pengpenghu(self):
        hand = parse_hand_from_names(
            "東 東 東 南 南 南 西 西 西 北 北 北 中 中".split(),
            winning_tile_name="中",
        )
        state = _state()
        result = calculate_score(hand, state)
        type_pts = sum(d.points for d in result.details
                       if d.description == "碰碰胡")
        assert type_pts == 4

    def test_menqing(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 1條 2條 3條 1餅 2餅 3餅 東 東 東 中 中".split(),
            winning_tile_name="中",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "門清" for d in result.details)


# ─── 花台 ────────────────────────────────────────────────────────────────────

class TestFlower:
    def test_flowers_counted(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 東 東 東 中 中 梅 蘭".split(),
            winning_tile_name="中",
        )
        state = _state(seat_number=1)
        result = calculate_score(hand, state)
        flower_pts = sum(d.points for d in result.details if d.category == "花台")
        # 2花 → 2台（正花），且梅=1號=東座正花，蘭=2號，非花槓（需梅+春）
        assert flower_pts >= 2

    def test_ba_xian(self):
        """八仙過海：8花"""
        all_flowers = "梅 蘭 菊 竹 春 夏 秋 冬".split()
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 東 東 東 中 中".split() +
            all_flowers,
            winning_tile_name="中",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description.startswith("八仙過海") for d in result.details)


# ─── 一色台 ──────────────────────────────────────────────────────────────────

class TestFlush:
    def test_qing_yi_se(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 1萬 1萬 1萬 2萬 2萬".split(),
            winning_tile_name="2萬",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "清一色" for d in result.details)

    def test_zi_yi_se(self):
        hand = parse_hand_from_names(
            "東 東 東 南 南 南 西 西 西 北 北 北 中 中".split(),
            winning_tile_name="中",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "字一色" for d in result.details)

    def test_hun_yi_se(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 東 東 東 中 中".split(),
            winning_tile_name="中",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "混一色" for d in result.details)


# ─── 三元台 ──────────────────────────────────────────────────────────────────

class TestDragons:
    def test_da_san_yuan(self):
        hand = parse_hand_from_names(
            "中 中 中 發 發 發 白 白 白 1萬 2萬 3萬 東 東".split(),
            winning_tile_name="東",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "大三元" for d in result.details)

    def test_xiao_san_yuan(self):
        hand = parse_hand_from_names(
            "中 中 中 發 發 發 1萬 2萬 3萬 4萬 5萬 6萬 白 白".split(),
            winning_tile_name="白",
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "小三元" for d in result.details)


# ─── 自摸台 ──────────────────────────────────────────────────────────────────

class TestSelfDraw:
    def test_zi_mo(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 1條 2條 3條 中 中".split(),
            winning_tile_name="中",
            is_self_draw=True,
        )
        state = _state()
        result = calculate_score(hand, state)
        assert any(d.description == "自摸" for d in result.details)

    def test_men_qing_zi_mo(self):
        """門清自摸：門清+自摸+不求人 = 3台"""
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 1條 2條 3條 中 中".split(),
            winning_tile_name="中",
            is_self_draw=True,
        )
        state = _state()
        result = calculate_score(hand, state)
        descs = [d.description for d in result.details]
        assert "自摸" in descs
        assert "門清" in descs
        assert "不求人" in descs


# ─── 天地人胡 ─────────────────────────────────────────────────────────────────

class TestHeavenEarth:
    def test_tianhu(self):
        hand = parse_hand_from_names(
            "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 1條 2條 3條 中 中".split(),
            winning_tile_name="中",
        )
        state = _state(tianhu=True)
        result = calculate_score(hand, state)
        assert result.total == 24


# ─── 風刻台 ──────────────────────────────────────────────────────────────────

class TestWindSets:
    def test_seat_wind(self):
        hand = parse_hand_from_names(
            "東 東 東 1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 中 中".split(),
            winning_tile_name="中",
        )
        state = _state(seat_wind=Wind.EAST, round_wind=Wind.SOUTH)
        result = calculate_score(hand, state)
        assert any("門風刻" in d.description for d in result.details)

    def test_round_wind(self):
        hand = parse_hand_from_names(
            "東 東 東 1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 中 中".split(),
            winning_tile_name="中",
        )
        state = _state(seat_wind=Wind.SOUTH, round_wind=Wind.EAST)
        result = calculate_score(hand, state)
        assert any("圈風刻" in d.description for d in result.details)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
