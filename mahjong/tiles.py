"""
台式麻將 - 牌面定義與資料結構
Taiwan Mahjong Tile Definitions and Data Structures
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional


class Suit(Enum):
    """牌組 Tile Suit"""
    WAN = "萬"      # 萬子 Characters (1-9)
    TIAO = "條"     # 條子 Bamboo (1-9)
    BING = "餅"     # 餅子 Circles (1-9)
    WIND = "風"     # 風牌 Winds
    DRAGON = "三元" # 三元牌 Dragons
    FLOWER = "花"   # 花牌 Flowers
    SEASON = "季"   # 季節牌 Seasons


class Wind(Enum):
    """風牌 Wind Tiles"""
    EAST = "東"
    SOUTH = "南"
    WEST = "西"
    NORTH = "北"


class Dragon(Enum):
    """三元牌 Dragon Tiles"""
    ZHONG = "中"    # 紅中
    FA = "發"       # 發財
    BAI = "白"      # 白板


class Flower(Enum):
    """花牌 Flower Tiles"""
    MEI = "梅"      # 梅 (1)
    LAN = "蘭"      # 蘭 (2)
    JU = "菊"       # 菊 (3)
    ZHU = "竹"      # 竹 (4)
    CHUN = "春"     # 春 (5)
    XIA = "夏"      # 夏 (6)
    QIU = "秋"      # 秋 (7)
    DONG = "冬"     # 冬 (8)


@dataclass(frozen=True, eq=True)
class Tile:
    """麻將牌 A single mahjong tile"""
    suit: Suit
    value: int = 0          # 1-9 for number tiles; Wind/Dragon enum value for honor tiles
    name: str = ""          # Display name
    flower_num: int = 0     # Flower number (1-8), 0 for non-flower

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Tile({self.name})"

    @property
    def is_number(self) -> bool:
        return self.suit in (Suit.WAN, Suit.TIAO, Suit.BING)

    @property
    def is_honor(self) -> bool:
        return self.suit in (Suit.WIND, Suit.DRAGON)

    @property
    def is_terminal(self) -> bool:
        """么九牌 (1 or 9)"""
        return self.is_number and self.value in (1, 9)

    @property
    def is_simple(self) -> bool:
        """中張牌 (2-8)"""
        return self.is_number and 2 <= self.value <= 8

    @property
    def is_flower(self) -> bool:
        return self.suit in (Suit.FLOWER, Suit.SEASON)


def make_tile(suit: Suit, value: int = 0, name: str = "", flower_num: int = 0) -> Tile:
    return Tile(suit=suit, value=value, name=name, flower_num=flower_num)


# ─── Build full tile set ───────────────────────────────────────────────────────

def _build_tile_set() -> dict:
    tiles = {}

    # 萬子 / 條子 / 餅子
    for suit, label in [(Suit.WAN, "萬"), (Suit.TIAO, "條"), (Suit.BING, "餅")]:
        for v in range(1, 10):
            key = f"{v}{label}"
            tiles[key] = Tile(suit=suit, value=v, name=key)

    # 風牌
    for wind in Wind:
        tiles[wind.value] = Tile(suit=Suit.WIND, value=wind, name=wind.value)  # type: ignore[arg-type]

    # 三元牌
    for dragon in Dragon:
        tiles[dragon.value] = Tile(suit=Suit.DRAGON, value=dragon, name=dragon.value)  # type: ignore[arg-type]

    # 花牌 (1-4 正花, 5-8 季節)
    flowers = [Flower.MEI, Flower.LAN, Flower.JU, Flower.ZHU,
               Flower.CHUN, Flower.XIA, Flower.QIU, Flower.DONG]
    for i, fl in enumerate(flowers, 1):
        suit = Suit.FLOWER if i <= 4 else Suit.SEASON
        tiles[fl.value] = Tile(suit=suit, value=fl, name=fl.value, flower_num=i)  # type: ignore[arg-type]

    return tiles


TILES: dict[str, Tile] = _build_tile_set()


def get_tile(name: str) -> Tile:
    """Get tile by display name"""
    if name not in TILES:
        raise ValueError(f"Unknown tile: {name!r}")
    return TILES[name]


# ─── Meld types ───────────────────────────────────────────────────────────────

class MeldType(Enum):
    SHUNTZU = "順子"    # Sequence (chi)
    KEZI = "刻子"       # Triplet (pong)
    GANGZI = "槓子"     # Quad (kong)
    PAIR = "對子"       # Pair (eye)


@dataclass
class Meld:
    """A meld (set) of tiles"""
    meld_type: MeldType
    tiles: List[Tile]
    is_concealed: bool = True   # 暗 = True, 明 = False

    def __str__(self):
        concealed = "暗" if self.is_concealed else "明"
        return f"{concealed}{self.meld_type.value}[{''.join(str(t) for t in self.tiles)}]"

    @property
    def base_tile(self) -> Tile:
        return self.tiles[0]


@dataclass
class Hand:
    """玩家手牌 Player hand"""
    melds: List[Meld] = field(default_factory=list)
    pair: Optional[Meld] = None
    flowers: List[Tile] = field(default_factory=list)
    winning_tile: Optional[Tile] = None
    is_self_draw: bool = False          # 自摸
    is_last_tile: bool = False          # 海底/河底
    is_after_kong: bool = False         # 槓上開花
    is_robbing_kong: bool = False       # 搶槓
    is_fully_concealed: bool = True     # 門清

    def all_melds(self) -> List[Meld]:
        result = list(self.melds)
        if self.pair:
            result.append(self.pair)
        return result

    def concealed_melds(self) -> List[Meld]:
        return [m for m in self.all_melds() if m.is_concealed]

    def exposed_melds(self) -> List[Meld]:
        return [m for m in self.all_melds() if not m.is_concealed]

    def all_tiles(self) -> List[Tile]:
        tiles = []
        for meld in self.all_melds():
            tiles.extend(meld.tiles)
        tiles.extend(self.flowers)
        if self.winning_tile and self.winning_tile not in tiles:
            tiles.append(self.winning_tile)
        return tiles


@dataclass
class GameState:
    """遊戲狀態 Current game state"""
    round_wind: Wind = Wind.EAST        # 圈風
    seat_wind: Wind = Wind.EAST         # 門風 (player's seat)
    is_dealer: bool = False             # 是否莊家
    consecutive_wins: int = 0           # 連莊次數
    player_flowers: List[int] = field(default_factory=list)  # 對應花號 (1-8)
    seat_number: int = 1                # 座位號 1=東 2=南 3=西 4=北
    is_dealer_win: bool = False         # 莊家胡牌
    tianhu: bool = False                # 天胡
    dihu: bool = False                  # 地胡
    renhu: bool = False                 # 人胡
    tiantin: bool = False               # 天聽
    ditin: bool = False                 # 地聽
    dutin: bool = False                 # 獨聽 (only one winning tile)
