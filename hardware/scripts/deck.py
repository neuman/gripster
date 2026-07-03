"""
deck.py — parametric geometry model for one half of the split thumb keyboard.

Pure geometry + a config dataclass, shared by layout_gen.py (render),
grade.py (score) and gen_kicad.py (board) so there is one source of truth.

Coordinate frame (millimetres), per half, origin at bottom-left of the board
bounding box, +x right, +y up. Generated for the RIGHT half (central, inner /
split edge straight at x=0 on the LEFT, facing the phone). The LEFT half is a
mirror across x = board_w/2, which is what makes the "true mirror" check real.

Vertical stack (bottom -> top):
    [ bottom strip: USB-C on the edge + LiPo ]
    [ 5x5 key field, fanned into a thumb arc  ]
    [ top strip: nRF52840 controller module   ]
D-shaped silhouette: flat inner edge (mates a clamp), bowed + rounded outer edge.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import math

# --- key legends (i8+-inspired QWERTY, split L/R, arrow cluster on right) -----
RIGHT_LEGENDS = [
    ["6", "7", "8", "9", "0"],
    ["Y", "U", "I", "O", "P"],
    ["H", "J", "K", "L", "ENT"],
    ["N", "M", ",", ".", "/"],
    ["SPC", "LFT", "DN", "UP", "RGT"],
]
# Column 0 = INNER (split/center) edge. The left half is drawn by mirroring the
# right half, which reverses column order on screen, so these are stored
# inner->outer (5..1, T..Q) precisely so the mirrored render reads naturally
# left->right as "1 2 3 4 5", "Q W E R T", etc.
LEFT_LEGENDS = [
    ["5", "4", "3", "2", "1"],
    ["T", "R", "E", "W", "Q"],
    ["G", "F", "D", "S", "A"],
    ["B", "V", "C", "X", "Z"],
    ["SPC", "ALT", "GUI", "CTL", "FN"],
]

VERSION = "v0.2"


@dataclass
class Config:
    rows: int = 5
    cols: int = 5
    pitch_x: float = 9.0
    pitch_y: float = 9.5
    key_w: float = 8.0
    key_h: float = 8.0
    col_stagger: float = 1.3      # +y per column moving outward (thumb fan)
    arc_bow: float = 0.06         # bows the field rows into a shallow arc
    inner_margin: float = 6.0     # inner straight edge -> nearest key
    grip_margin: float = 7.0      # nearest key -> outer bulge base
    outer_bow: float = 6.0        # extra convex bulge at mid-height (grip feel)
    bottom_strip: float = 28.0    # reserved below keys: USB-C + LiPo
    ctrl_w: float = 21.0          # XIAO nRF52840 module footprint
    ctrl_h: float = 17.8
    top_pad: float = 4.0          # gap between top key row and controller
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
            y += col * c.col_stagger                                  # thumb fan
            y += -c.arc_bow * ((col - mid) ** 2) * c.pitch_y * 0.5    # arc bow
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
    r_in = 4.0        # inner corner radius (small -> flat mating edge reads)
    r_out = 14.0      # outer corner radius (large -> grip)

    def outer_x(y):
        # convex bow, peaks at mid-height, never below outer_base (keys stay in)
        t = (y - board_h / 2) / (board_h / 2)
        ease = max(0.0, 1.0 - t * t)
        return outer_base + c.outer_bow * ease

    pts = []
    # inner straight edge, bottom -> top
    pts.append([0.0, r_in])
    pts.append([0.0, board_h - r_in])
    # inner-top corner
    pts += _arc(r_in, board_h - r_in, r_in, 180, 90, 5)
    # top edge to outer-top corner
    pts.append([outer_x(board_h) - r_out, board_h])
    pts += _arc(outer_base - r_out, board_h - r_out, r_out, 90, 0, 8)
    # outer bowed edge, top -> bottom (sampled)
    n = 20
    for i in range(1, n):
        y = (board_h - r_out) - (board_h - 2 * r_out) * i / n
        pts.append([round(outer_x(y), 3), round(y, 3)])
    # outer-bottom corner
    pts += _arc(outer_base - r_out, r_out, r_out, 0, -90, 8)
    # bottom edge back to inner-bottom corner
    pts.append([r_in, 0.0])
    pts += _arc(r_in, r_in, r_in, -90, -180, 5)
    board_w = max(p[0] for p in pts)
    return pts, board_w, board_h, outer_base


def _keepouts(c, board_w, board_h, outer_base, keys):
    ys = [k["y"] for k in keys]
    field_bottom = min(ys) - c.key_h / 2
    mid_x = outer_base / 2.0
    ko = {}
    usb_w, usb_h = 9.0, 6.0
    ko["usb_c"] = [round(mid_x - usb_w / 2, 2), 1.0, usb_w, usb_h]
    li_w, li_h = 26.0, 13.0
    ko["lipo"] = [round(mid_x - li_w / 2, 2),
                  round((9.0 + field_bottom) / 2 - li_h / 2, 2), li_w, li_h]
    ctl_w, ctl_h = c.ctrl_w, c.ctrl_h
    ko["controller"] = [round(mid_x - ctl_w / 2, 2),
                        round(board_h - ctl_h - c.top_pad, 2), ctl_w, ctl_h]
    return ko


def _mount_holes(c, board_w, board_h, outer_base):
    inset, d = 3.0, 2.2
    return [
        {"x": inset, "y": round(board_h * 0.16, 2), "d": d},          # inner low
        {"x": inset, "y": round(board_h * 0.84, 2), "d": d},          # inner high
        {"x": round(outer_base - 4.0, 2), "y": round(board_h * 0.5, 2), "d": d},
    ]


def build(c: Config) -> dict:
    keys, field_x0 = _key_centers(c)
    outline, board_w, board_h, outer_base = _outline(c, keys)
    keepouts = _keepouts(c, board_w, board_h, outer_base, keys)
    holes = _mount_holes(c, board_w, board_h, outer_base)
    anchor = [round(outer_base * 0.85, 2), 6.0]     # thumb base: bottom-outer
    geo = {
        "side": "right",
        "board_w": round(board_w, 3),
        "board_h": round(board_h, 3),
        "outer_base": round(outer_base, 3),
        "keys": keys,
        "outline": outline,
        "keepouts": keepouts,
        "mount_holes": holes,
        "anchor": anchor,
        "arc": {"rmin": 22.0, "rmax": 84.0},
        "config": asdict(c),
    }
    if c.side == "left":
        geo = mirror(geo)
    return geo


def mirror(geo: dict) -> dict:
    W = geo["board_w"]
    m = json.loads(json.dumps(geo))
    m["side"] = "left"
    for k in m["keys"]:
        k["x"] = round(W - k["x"], 3)
        k["label"] = LEFT_LEGENDS[k["row"]][k["col"]]
    m["outline"] = [[round(W - x, 3), y] for x, y in m["outline"]]
    for name, (x, y, w, h) in m["keepouts"].items():
        m["keepouts"][name] = [round(W - x - w, 2), y, w, h]
    for hole in m["mount_holes"]:
        hole["x"] = round(W - hole["x"], 3)
    m["anchor"] = [round(W - m["anchor"][0], 2), m["anchor"][1]]
    return m


if __name__ == "__main__":
    import sys
    c = Config(side=sys.argv[1] if len(sys.argv) > 1 else "right")
    print(json.dumps(build(c), indent=2))
