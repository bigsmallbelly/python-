"""
台式麻將北部算法計分器 - Flask Web App
執行: python app.py
瀏覽: http://localhost:5000
"""
from __future__ import annotations

from flask import Flask, render_template, request, make_response

from mahjong.tiles import Wind, GameState
from mahjong.hand_parser import parse_hand_from_names
from mahjong.scorer import calculate_score

app = Flask(__name__)

WIND_MAP = {
    "east": Wind.EAST, "south": Wind.SOUTH,
    "west": Wind.WEST, "north": Wind.NORTH,
}
SEAT_MAP = {"east": 1, "south": 2, "west": 3, "north": 4}


def _bool(val: str) -> bool:
    return val in ("1", "true", "on", "yes")


@app.route("/")
def index():
    return render_template("index.html", result=None, form={})


@app.route("/score", methods=["POST"])
def score():
    f = request.form

    # ── 讀取表單 ──────────────────────────────────────────────────────────
    hand_str      = f.get("hand", "").strip()
    win_tile      = f.get("win_tile", "").strip() or None
    win_method    = f.get("win_method", "discard")   # self_draw / discard / robbing
    is_menqing    = _bool(f.get("menqing", "0"))
    is_dutin      = _bool(f.get("dutin", "0"))
    is_after_kong = _bool(f.get("after_kong", "0"))
    is_last_tile  = _bool(f.get("last_tile", "0"))
    is_tianhu     = _bool(f.get("tianhu", "0"))
    is_dihu       = _bool(f.get("dihu", "0"))
    is_dealer     = _bool(f.get("is_dealer", "0"))
    consec        = int(f.get("consecutive_wins", 0) or 0)
    round_wind    = WIND_MAP.get(f.get("round_wind", "east"), Wind.EAST)
    seat_wind     = WIND_MAP.get(f.get("seat_wind", "east"), Wind.EAST)
    seat_number   = int(f.get("seat_number", 1) or 1)

    is_self_draw   = (win_method == "self_draw")
    is_robbing     = (win_method == "robbing")

    # 保留表單值以便重新顯示
    form_vals = dict(f)
    form_vals["is_dealer"] = is_dealer
    form_vals["menqing"]   = is_menqing
    form_vals["dutin"]     = is_dutin
    form_vals["after_kong"]= is_after_kong
    form_vals["last_tile"] = is_last_tile
    form_vals["tianhu"]    = is_tianhu
    form_vals["dihu"]      = is_dihu

    # ── 解析手牌 ──────────────────────────────────────────────────────────
    tile_names = hand_str.split() if hand_str else []

    try:
        hand = parse_hand_from_names(
            tile_names,
            winning_tile_name=win_tile,
            is_self_draw=is_self_draw,
            is_last_tile=is_last_tile,
            is_after_kong=is_after_kong,
            is_robbing_kong=is_robbing,
        )
        # 門清狀態由使用者勾選（有時系統無法自動判定）
        object.__setattr__(hand, 'is_fully_concealed', is_menqing) \
            if hasattr(hand, '__dataclass_fields__') else None
        hand = hand.__class__(
            melds=hand.melds,
            pair=hand.pair,
            flowers=hand.flowers,
            winning_tile=hand.winning_tile,
            is_self_draw=hand.is_self_draw,
            is_last_tile=hand.is_last_tile,
            is_after_kong=hand.is_after_kong,
            is_robbing_kong=hand.is_robbing_kong,
            is_fully_concealed=is_menqing,
        )
    except ValueError as e:
        result = {"error": f"牌名錯誤：{e}", "tiles": tile_names}
        resp = make_response(render_template("index.html", result=result, form=form_vals))
        return resp

    # ── 遊戲狀態 ──────────────────────────────────────────────────────────
    state = GameState(
        round_wind=round_wind,
        seat_wind=seat_wind,
        seat_number=seat_number,
        is_dealer=is_dealer,
        consecutive_wins=consec,
        tianhu=is_tianhu,
        dihu=is_dihu,
        dutin=is_dutin,
    )

    # ── 計分 ──────────────────────────────────────────────────────────────
    score_result = calculate_score(hand, state)

    result = {
        "total":   score_result.total,
        "details": score_result.details,
        "tiles":   tile_names,
        "error":   None,
    }

    # AJAX 時只回傳結果片段；一般 GET 回傳完整頁面
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or True:
        resp = make_response(render_template("index.html", result=result, form=form_vals))
        return resp


if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\n  本機：  http://localhost:5000")
    print(f"  區網：  http://{local_ip}:5000  ← 手機用這個\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
