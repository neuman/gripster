"""
deck.py — parametric geometry model for the split thumb keyboard (v0.3).

v0.3 architecture change: ONE controller, not two. The RIGHT grip carries the
single nRF52840 (nice!nano v2), the LiPo and the USB-C. The LEFT grip is a
PASSIVE 5x5 matrix (switches + diodes only) wired to the right grip through the
telescoping bridge. No BLE split, no second battery. See docs/design-decisions.

Both grips share the same D-shaped silhouette (symmetric phone clamp) and the
key field is mirrored, but their keep-outs differ by role:
    RIGHT (mcu)     : controller + LiPo + USB-C + bridge connector
    LEFT  (passive) : bridge connector only

Frame: millimetres, per half, origin bottom-left, +x right, +y up. Right grip's
inner/split edge is straight at x=0 (faces the phone / the bridge).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import math

VERSION = "v0.3"

# --- key legends (i8+-inspired QWERTY, split L/R, arrow cluster on right) -----
RIGHT_LEGENDS = [
    ["6", "7", "8", "9", "0"],
    ["Y", "U", "I", "O", "P"],
    ["H", "J", "K", "L", "ENT"],
    ["N", "M", ",", ".", "/"],
    ["SPC", "LFT", "DN", "UP", "RGT"],
]
# col 0 = INNER edge; stored inner->outer so the mirrored render reads naturally
LEFT_LEGENDS = [
    ["5", "4", "3", "2", "1"],
    ["T", "R", "E", "W", "Q"],
    ["G", "F", "D", "S", "A"],
    ["B", "V", "C", "X", "Z"],
    ["SPC", "ALT", "GUI", "CTL", "FN"],
]


@dataclass
class Config:
    rows: int = 5
    cols: int = 5
    pitch_x: float = 9.0
    pitch_y: float = 9.5
    key_w: float = 8.0
    key_h: float = 8.0
    col_stagger: float = 1.3
    arc_bow: float = 0.06
    inner_margin: float = 6.0
    grip_margin: float = 7.0
    outer_bow: float = 6.0
    bottom_strip: float = 28.0
    ctrl_w: float = 33.4          # nice!nano v2 (Pro Micro footprint), laid horizontal
    ctrl_h: float = 18.0
    top_pad: float = 4.0
    phone_len: float = 160.0
    env_w_max: float = 64.0
    env_h_max: float = 112.0
    side: str = "right"


def _key_centers(c: Config):
    field_x0 = c.inner_margin + c.key_w / 2.0
    field_y0 = c.bottom_strip + c.key_h / 2.0 + 4.0
    mid = (c.cols - 1) / 2.0
    keys = []
    for r in range(c.rows):
        for col in range(c.cols):
            x = field_x0 + col * c.pitch_x
            y = field_y0 + (c.rows - 1 - r) * c.pitch_y
            y += col * c.col_stagger
            y += -c.arc_bow * ((col - mid) ** 2) * c.pitch_y * 0.5
            keys.append({"row": r, "col": col,
                         "x": round(x, 3), "y": round(y, 3),
                         "label": RIGHT_LEGENDS[r][col]})
    return keys, field_x0


def _arc(cx, cy, r, a0, a1, n=8):
    return [[round(cx + r * math.cos(math.radians(a)), 3),
             round(cy + r * math.sin(math.radians(a)), 3)]
            for a in [a0 + (a1 - a0) * i / n for i in range(n + 1)]]


def _outline(c: Config, keys):
    xs = [k["x"] for k in keys]
    ys = [k["y"] for k in keys]
    outer_base = max(xs) + c.key_w / 2 + c.grip_margin
    top_keys = max(ys) + c.key_h / 2
    board_h = top_keys + c.top_pad + c.ctrl_h + c.top_pad
    r_in, r_out = 4.0, 14.0

    def outer_x(y):
        t = (y - board_h / 2) / (board_h / 2)
        ease = max(0.0, 1.0 - t * t)
        return outer_base + c.outer_bow * ease

    pts = [[0.0, r_in], [0.0, board_h - r_in]]
    pts += _arc(r_in, board_h - r_in, r_in, 180, 90, 5)
    pts.append([outer_x(board_h) - r_out, board_h])
    pts += _arc(outer_base - r_out, board_h - r_out, r_out, 90, 0, 8)
    n = 20
    for i in range(1, n):
        y = (board_h - r_out) - (board_h - 2 * r_out) * i / n
        pts.append([round(outer_x(y), 3), round(y, 3)])
    pts += _arc(outer_base - r_out, r_out, r_out, 0, -90, 8)
    pts.append([r_in, 0.0])
    pts += _arc(r_in, r_in, r_in, -90, -180, 5)
    board_w = max(p[0] for p in pts)
    return pts, board_w, board_h, outer_base


def _bridge_conn(board_h):
    """FPC/JST connector for the bridge cable, at the inner-BOTTOM corner (cable
    runs along the bottom behind the phone to the other grip). Right grip: inner
    edge at x=0. 10 conductors (5 shared rows + 5 left-grip cols)."""
    return [2.0, 8.0, 12.0, 6.0]


def _keepouts_mcu(c, board_w, board_h, outer_base, keys):
    ys = [k["y"] for k in keys]
    field_bottom = min(ys) - c.key_h / 2
    mid_x = outer_base / 2.0
    ko = {}
    ko["usb_c"] = [round(mid_x - 4.5, 2), 1.0, 9.0, 6.0]
    ko["lipo"] = [round(mid_x - 13.0, 2),
                  round((9.0 + field_bottom) / 2 - 6.5, 2), 26.0, 13.0]
    ko["controller"] = [round(mid_x - c.ctrl_w / 2, 2),
                        round(board_h - c.ctrl_h - c.top_pad, 2), c.ctrl_w, c.ctrl_h]
    ko["bridge"] = _bridge_conn(board_h)
    return ko


def _keepouts_passive(board_h):
    return {"bridge": _bridge_conn(board_h)}


def _mount_holes(board_h, outer_base):
    inset, d = 3.0, 2.2
    return [
        {"x": inset, "y": round(board_h * 0.16, 2), "d": d},
        {"x": inset, "y": round(board_h * 0.84, 2), "d": d},
        {"x": round(outer_base - 4.0, 2), "y": round(board_h * 0.5, 2), "d": d},
    ]


def build(c: Config) -> dict:
    keys, field_x0 = _key_centers(c)
    outline, board_w, board_h, outer_base = _outline(c, keys)
    holes = _mount_holes(board_h, outer_base)
    anchor = [round(outer_base * 0.85, 2), 6.0]
    geo = {
        "side": "right", "role": "mcu",
        "board_w": round(board_w, 3), "board_h": round(board_h, 3),
        "outer_base": round(outer_base, 3),
        "keys": keys, "outline": outline,
        "keepouts": _keepouts_mcu(c, board_w, board_h, outer_base, keys),
        "mount_holes": holes, "anchor": anchor,
        "arc": {"rmin": 22.0, "rmax": 84.0},
        "config": asdict(c),
    }
    if c.side == "left":
        geo = mirror(geo)
    return geo


def mirror(geo: dict) -> dict:
    """Mirror the RIGHT grip across x = board_w/2 to get the LEFT grip: key field
    + outline + mount holes mirror; keep-outs become the PASSIVE set (bridge only,
    on the left grip's inner edge = right side of the board)."""
    W = geo["board_w"]
    m = json.loads(json.dumps(geo))
    m["side"] = "left"
    m["role"] = "passive"
    for k in m["keys"]:
        k["x"] = round(W - k["x"], 3)
        k["label"] = LEFT_LEGENDS[k["row"]][k["col"]]
    m["outline"] = [[round(W - x, 3), y] for x, y in m["outline"]]
    for hole in m["mount_holes"]:
        hole["x"] = round(W - hole["x"], 3)
    m["anchor"] = [round(W - m["anchor"][0], 2), m["anchor"][1]]
    # passive keep-outs: bridge connector on the left grip's inner edge
    bx, by, bw, bh = geo["keepouts"]["bridge"]
    m["keepouts"] = {"bridge": [round(W - bx - bw, 2), by, bw, bh]}
    return m


if __name__ == "__main__":
    import sys
    c = Config(side=sys.argv[1] if len(sys.argv) > 1 else "right")
    print(json.dumps(build(c), indent=2))
