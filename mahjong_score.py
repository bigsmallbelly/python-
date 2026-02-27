#!/usr/bin/env python3
"""
台式麻將北部算法 計分主程式
Taiwan Mahjong Northern Rules Score Calculator

使用方式 Usage:
  # 手動輸入牌組計分
  python mahjong_score.py --hand "1萬 2萬 3萬 4萬 5萬 6萬 7萬 8萬 9萬 東 東 東 中 中" \
         --win-tile 中 --self-draw

  # 從圖片辨識並計分（需提供 templates 資料夾）
  python mahjong_score.py --image hand.jpg --templates ./templates/ \
         --win-tile 中 --seat east --round east

  # 從圖片辨識並計分（使用 CNN 模型）
  python mahjong_score.py --image hand.jpg --model ./model.pt \
         --win-tile 中 --seat east
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from mahjong.tiles import Wind, GameState
from mahjong.hand_parser import parse_hand_from_names
from mahjong.scorer import calculate_score

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


WIND_MAP = {
    "east": Wind.EAST, "東": Wind.EAST,
    "south": Wind.SOUTH, "南": Wind.SOUTH,
    "west": Wind.WEST, "西": Wind.WEST,
    "north": Wind.NORTH, "北": Wind.NORTH,
}
SEAT_MAP = {"east": 1, "東": 1, "south": 2, "南": 2,
            "west": 3, "西": 3, "north": 4, "北": 4}


def build_game_state(args: argparse.Namespace) -> GameState:
    round_wind = WIND_MAP.get(args.round_wind, Wind.EAST)
    seat_wind = WIND_MAP.get(args.seat_wind, Wind.EAST)
    seat_number = SEAT_MAP.get(args.seat_wind, 1)

    return GameState(
        round_wind=round_wind,
        seat_wind=seat_wind,
        seat_number=seat_number,
        is_dealer=(seat_wind == Wind.EAST),
        consecutive_wins=args.consecutive_wins,
        tianhu=args.tianhu,
        dihu=args.dihu,
        renhu=args.renhu,
        tiantin=args.tiantin,
        ditin=args.ditin,
        dutin=args.dutin,
    )


def recognize_tiles(args: argparse.Namespace) -> List[str]:
    """從圖片辨識牌名"""
    from mahjong.recognizer import MahjongRecognizer
    import cv2

    img = cv2.imread(args.image)
    if img is None:
        sys.exit(f"[錯誤] 無法讀取圖片：{args.image}")

    if args.model and Path(args.model).exists():
        print(f"[辨識] 使用 CNN 模型：{args.model}")
        rec = MahjongRecognizer("cnn", model_path=args.model)
    elif args.templates and Path(args.templates).is_dir():
        print(f"[辨識] 使用範本比對：{args.templates}")
        rec = MahjongRecognizer("template", templates_dir=args.templates)
    else:
        sys.exit("[錯誤] 請提供 --templates 資料夾或 --model 路徑")

    tile_names = rec.recognize(img, save_debug=args.debug_image)
    print(f"[辨識結果] {' '.join(tile_names)}")
    return tile_names


def main():
    parser = argparse.ArgumentParser(
        description="台式麻將北部算法計分系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 手牌來源
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--hand", "-H", type=str,
                     help="手牌牌名（空白分隔），如：'1萬 2萬 3萬 ...'")
    src.add_argument("--image", "-i", type=str,
                     help="從圖片辨識手牌")

    # 辨識相關
    parser.add_argument("--templates", type=str, default=None,
                        help="範本比對模式的範本圖資料夾")
    parser.add_argument("--model", type=str, default=None,
                        help="CNN 辨識模型路徑（.pt）")
    parser.add_argument("--debug-image", type=str, default=None,
                        help="存檔辨識標注圖（供除錯用）")

    # 胡牌相關
    parser.add_argument("--win-tile", "-w", type=str, default=None,
                        help="胡牌張（最後一張）")
    parser.add_argument("--self-draw", "-s", action="store_true",
                        help="自摸")
    parser.add_argument("--last-tile", action="store_true",
                        help="海底/河底（最後一張牌）")
    parser.add_argument("--after-kong", action="store_true",
                        help="槓上開花")
    parser.add_argument("--robbing-kong", action="store_true",
                        help="搶槓")

    # 明牌
    parser.add_argument("--exposed", type=str, default=None,
                        help="明牌組合（JSON 格式），如：\"[['刻子','中中中']]\"")

    # 遊戲狀態
    parser.add_argument("--round-wind", type=str, default="east",
                        choices=list(WIND_MAP.keys()),
                        help="圈風 (east/south/west/north 或 東/南/西/北)")
    parser.add_argument("--seat-wind", type=str, default="east",
                        choices=list(WIND_MAP.keys()),
                        help="門風/座位風")
    parser.add_argument("--consecutive-wins", type=int, default=0,
                        help="連莊次數（0=非連莊）")

    # 特殊胡牌
    parser.add_argument("--tianhu", action="store_true", help="天胡")
    parser.add_argument("--dihu", action="store_true", help="地胡")
    parser.add_argument("--renhu", action="store_true", help="人胡")
    parser.add_argument("--tiantin", action="store_true", help="天聽")
    parser.add_argument("--ditin", action="store_true", help="地聽")
    parser.add_argument("--dutin", action="store_true", help="獨聽")

    args = parser.parse_args()

    # 1. 取得牌名列表
    if args.image:
        tile_names = recognize_tiles(args)
    else:
        tile_names = args.hand.split()

    print(f"\n手牌：{' '.join(tile_names)}")

    # 2. 解析明牌
    exposed_sets = None
    if args.exposed:
        import json
        raw = json.loads(args.exposed)
        # 支援 [["刻子","中中中"], ...] 或 [["刻子",["中","中","中"]], ...]
        exposed_sets = []
        for item in raw:
            meld_type = item[0]
            tile_list = item[1]
            if isinstance(tile_list, str):
                # "中中中" → ["中","中","中"]
                # 逐字切分（每個漢字一張）
                from mahjong.tiles import TILES
                names = []
                i = 0
                while i < len(tile_list):
                    for length in range(3, 0, -1):
                        candidate = tile_list[i:i + length]
                        if candidate in TILES:
                            names.append(candidate)
                            i += length
                            break
                    else:
                        i += 1
                tile_list = names
            exposed_sets.append((meld_type, tile_list))

    # 3. 建立 Hand
    hand = parse_hand_from_names(
        tile_names,
        exposed_sets=exposed_sets,
        winning_tile_name=args.win_tile,
        is_self_draw=args.self_draw,
        is_last_tile=args.last_tile,
        is_after_kong=args.after_kong,
        is_robbing_kong=args.robbing_kong,
    )

    # 4. 建立遊戲狀態
    state = build_game_state(args)

    # 5. 計分
    result = calculate_score(hand, state)
    print()
    print(result.report())


if __name__ == "__main__":
    main()
