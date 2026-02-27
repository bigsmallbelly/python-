"""
手牌解析器 Hand Parser
將牌名列表 → Hand 物件（自動找出最高分的胡牌分解）
"""
from __future__ import annotations

from itertools import permutations
from typing import List, Optional, Tuple, Dict

from .tiles import (
    Suit, Tile, Meld, MeldType, Hand, TILES, get_tile
)


def parse_tile_names(names: List[str]) -> List[Tile]:
    """將牌名字串列表轉成 Tile 列表"""
    tiles = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        if name in TILES:
            tiles.append(TILES[name])
        else:
            raise ValueError(f"未知的牌名: {name!r}")
    return tiles


def _can_form_shuntzu(tiles: List[Tile]) -> bool:
    """3張牌能否組成順子"""
    if len(tiles) != 3:
        return False
    if any(not t.is_number for t in tiles):
        return False
    if len({t.suit for t in tiles}) != 1:
        return False
    values = sorted(t.value for t in tiles)
    return values[1] == values[0] + 1 and values[2] == values[1] + 1


def _can_form_kezi(tiles: List[Tile]) -> bool:
    """3張牌能否組成刻子"""
    if len(tiles) != 3:
        return False
    return len({t.name for t in tiles}) == 1


# ─── 窮舉胡牌解析（4刻/順 + 1對）────────────────────────────────────────────

class HandDecomposer:
    """
    遞迴嘗試所有 4組+1對 的分解方式
    對花牌不做分析（花牌單獨提出）
    """

    def decompose(self, tiles: List[Tile]) -> Optional[Tuple[List[Meld], Meld]]:
        """
        回傳 (melds_4, pair_meld) 或 None（無法胡牌）
        melds_4: 4組順子或刻子
        pair_meld: 雀頭（對子）
        """
        # 排序牌面，讓貪心搜尋更穩定
        sorted_tiles = self._sort_tiles(tiles)

        from collections import Counter
        cnt: Counter[str] = Counter(t.name for t in sorted_tiles)
        candidates = [(name, count) for name, count in cnt.items() if count >= 2]

        for pair_name, _ in candidates:
            remaining = list(sorted_tiles)
            removed = 0
            new_remaining = []
            for t in remaining:
                if t.name == pair_name and removed < 2:
                    removed += 1
                else:
                    new_remaining.append(t)

            pair_tile = TILES[pair_name]
            pair_meld = Meld(MeldType.PAIR, [pair_tile, pair_tile], is_concealed=True)

            result = self._find_melds(new_remaining, 4)
            if result is not None:
                return result, pair_meld

        return None

    @staticmethod
    def _sort_key(tile: Tile) -> Tuple[int, int]:
        suit_order = {
            "萬": 0, "條": 1, "餅": 2,
            "風": 3, "三元": 4, "花": 5, "季": 6,
        }
        suit_rank = suit_order.get(tile.suit.value, 9)
        val = tile.value if isinstance(tile.value, int) else tile.value.value if hasattr(tile.value, 'value') else 0
        return (suit_rank, val)

    def _sort_tiles(self, tiles: List[Tile]) -> List[Tile]:
        return sorted(tiles, key=self._sort_key)

    def _find_melds(self, tiles: List[Tile], need: int) -> Optional[List[Meld]]:
        if need == 0:
            return [] if not tiles else None
        if len(tiles) < 3:
            return None

        # 優先嘗試刻子（以第一張牌為準）
        first = tiles[0]
        rest = tiles[1:]

        # 嘗試刻子
        matches = [t for t in rest if t.name == first.name]
        if len(matches) >= 2:
            new_tiles = [t for t in rest if t.name != first.name] + matches[2:]
            meld = Meld(MeldType.KEZI, [first] * 3, is_concealed=True)
            result = self._find_melds(new_tiles, need - 1)
            if result is not None:
                return [meld] + result

        # 嘗試順子（只對數字牌）
        if first.is_number:
            target2 = f"{first.value + 1}{first.suit.value}"
            target3 = f"{first.value + 2}{first.suit.value}"
            if target2 in TILES and target3 in TILES:
                t2, t3 = TILES[target2], TILES[target3]
                remaining_tmp = list(rest)
                if t2.name in [t.name for t in remaining_tmp]:
                    remaining_tmp.remove(next(t for t in remaining_tmp if t.name == t2.name))
                    if t3.name in [t.name for t in remaining_tmp]:
                        remaining_tmp.remove(next(t for t in remaining_tmp if t.name == t3.name))
                        meld = Meld(MeldType.SHUNTZU,
                                    [first, t2, t3], is_concealed=True)
                        result = self._find_melds(remaining_tmp, need - 1)
                        if result is not None:
                            return [meld] + result

        return None


def parse_hand_from_names(
    tile_names: List[str],
    exposed_sets: Optional[List[Tuple[str, List[str]]]] = None,
    winning_tile_name: Optional[str] = None,
    is_self_draw: bool = False,
    is_last_tile: bool = False,
    is_after_kong: bool = False,
    is_robbing_kong: bool = False,
) -> Hand:
    """
    從牌名列表建構 Hand 物件。

    exposed_sets: 已明牌的組合，格式 [("順子", ["1萬","2萬","3萬"]), ...]
                  meld_type: "順子" / "刻子" / "槓子"
    """
    all_tiles = parse_tile_names(tile_names)
    winning_tile = TILES[winning_tile_name] if winning_tile_name else None

    # 分離花牌
    flower_tiles = [t for t in all_tiles if t.is_flower]
    hand_tiles = [t for t in all_tiles if not t.is_flower]

    # 建立已知的明刻/明順
    exposed: List[Meld] = []
    if exposed_sets:
        meld_type_map = {
            "順子": MeldType.SHUNTZU,
            "刻子": MeldType.KEZI,
            "槓子": MeldType.GANGZI,
        }
        for (mt_str, names) in exposed_sets:
            mt = meld_type_map.get(mt_str, MeldType.KEZI)
            ts = parse_tile_names(names)
            exposed.append(Meld(mt, ts, is_concealed=False))
            for t in ts:
                if t in hand_tiles:
                    hand_tiles.remove(t)

    # 自動分解剩餘暗牌
    decomposer = HandDecomposer()
    result = decomposer.decompose(hand_tiles)

    if result is None:
        # 無法解析（不完整手牌）—— 仍組裝 Hand
        hand = Hand(
            melds=exposed,
            pair=None,
            flowers=flower_tiles,
            winning_tile=winning_tile,
            is_self_draw=is_self_draw,
            is_last_tile=is_last_tile,
            is_after_kong=is_after_kong,
            is_robbing_kong=is_robbing_kong,
            is_fully_concealed=(len(exposed) == 0),
        )
    else:
        melds, pair = result
        hand = Hand(
            melds=exposed + melds,
            pair=pair,
            flowers=flower_tiles,
            winning_tile=winning_tile,
            is_self_draw=is_self_draw,
            is_last_tile=is_last_tile,
            is_after_kong=is_after_kong,
            is_robbing_kong=is_robbing_kong,
            is_fully_concealed=(len(exposed) == 0),
        )

    return hand
