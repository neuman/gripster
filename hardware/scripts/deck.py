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

VERSION = "v0.13"

# --- key legends (i8+-inspired QWERTY, split L/R, arrow cluster on right) -----
# v0.6: grown to 6 cols x 6 rows/half (~36/half) to match the sketch + the
# Rii i8+, which the user thumb-types daily (57mm half @ ~9.5mm pitch). At our
# tighter 8.5x8.8 pitch a 6x6 half is only 51x53mm — smaller than the i8+ half,
# so reach is proven; edge legends below are PROVISIONAL (best read of the
# sketch — nav cluster / trackpad / arrows not yet placed). col 0 = INNER edge.
# v0.13: bottom row = a DOUBLE-WIDE (2u) space bar at the inner edge, then 4 keys.
# The MENU key is dropped and the row shifts over one (5 keycaps span the 6-unit width).
RIGHT_LEGENDS = [
    ["F6", "F7", "F8", "F9", "F10", "DEL"],
    ["6",  "7",  "8",  "9",  "0",   "BSP"],
    ["Y",  "U",  "I",  "O",  "P",   ";"],
    ["H",  "J",  "K",  "L",  "'",   "ENT"],
    ["N",  "M",  ",",  ".",  "/",   "SHF"],
    ["SPC", "AGR", "[", "]",  "\\"],          # SPC = 2u; MEN dropped
]
# stored inner->outer so the mirrored render reads naturally
LEFT_LEGENDS = [
    ["F5", "F4", "F3", "F2", "F1", "ESC"],
    ["5",  "4",  "3",  "2",  "1",  "`"],
    ["T",  "R",  "E",  "W",  "Q",  "TAB"],
    ["G",  "F",  "D",  "S",  "A",  "CAP"],
    ["B",  "V",  "C",  "X",  "Z",  "SHF"],
    ["SPC", "ALT", "WIN", "FN", "CTL"],        # SPC = 2u; MEN dropped
]

# --- non-grid features per grip (digitized from the sketch, see
#     hardware/layout/keymat.json). LEFT grip: 4-way D-pad + OK + 2 mouse
#     buttons. RIGHT grip: Cirque trackpad + PgUp/PgDn. These are switches
#     (except the trackpad pad) that join the same scanned matrix. --------------
LEFT_FEATURES = ["NAV_U", "NAV_D", "NAV_L", "NAV_R", "NAV_OK", "MB_L", "MB_R"]
RIGHT_FEATURES = ["PGUP", "PGDN"]


@dataclass
class Config:
    rows: int = 6
    cols: int = 6
    # v0.5: switch = Snaptron 7mm double-sided snap dome (footprint extracted from
    # PocketMage V3.4, hardware/footprints/snaptron_7mm_contact_pad.kicad_mod).
    # Pitch + ortholinear grid adopted verbatim from PocketMage's proven keyboard:
    # 8.5mm X, 8.8mm Y, no column stagger / arc bow. The 7mm dome courtyard is
    # ~8.3mm, so 8.5mm X is about as tight as the domes physically pack.
    # v0.13: pitch bumped 8.5/8.8 -> 9.5mm so the inter-key GAP is ~1.5mm (pitch - key_w),
    # i.e. ~3-4 perimeters of wall at a 0.4mm nozzle — the minimum for a reliable PETG-FDM
    # keymat + shell. (At 8.5mm the wall was only ~0.5mm = unprintable in PETG; resin/SLA
    # or a 0.25mm nozzle would be needed to go tighter.) 9.5mm also matches the i8+ pitch.
    pitch_x: float = 9.5
    pitch_y: float = 9.5
    key_w: float = 8.0
    key_h: float = 8.0
    col_stagger: float = 0.0      # ortholinear (was 1.3 arc-stagger through v0.4)
    arc_bow: float = 0.0          # ortholinear (was 0.06 through v0.4)
    inner_margin: float = 6.0
    grip_margin: float = 7.0
    outer_bow: float = 6.0
    # v0.10: LiPo moved to the central SPINE (behind the MagSafe ring), so the grip
    # bottom zone only needs USB-C + charger + bridge — shrinks the grip height so it
    # no longer dwarfs the phone (target ~grip = phone_short + ~2x12mm overhang, i8+-like).
    bottom_strip: float = 14.0
    # v0.9 (PCBA sourcing): MCU module is the **Ebyte E73-2G4M08S1C** nRF52840
    # (JLC C356849) — the Raytac MDBT50Q was out of stock / not reliably
    # JLC-placeable. The E73 is in the JLC library, is the community-standard
    # ZMK nRF52840 module, and machine-places (Extended, X-ray). On the BACK.
    # Still a certified radio: no FCC/RED cert, RF match, crystals or Zephyr port.
    ctrl_w: float = 20.5          # Ebyte E73-2G4M08S1C module width
    ctrl_h: float = 12.0          # module length; PCB-antenna end faces outer-top corner
    antenna_h: float = 5.0        # module antenna zone: no-copper keep-out, >=15mm from magnets
    usb_gap: float = 6.0          # access gap
    top_pad: float = 4.0
    phone_len: float = 160.0
    env_w_max: float = 64.0
    env_h_max: float = 126.0      # taller: vertical module + antenna overhang
    side: str = "right"
    # --- v0.7: phone target + MagSafe centre-mount + cluster/trackpad features ---
    target: str = "phone"         # phone MagSafe-mounts to the centre (not a Pi)
    orientation: str = "landscape"  # phone held LANDSCAPE between the grips (Steam-Deck style)
    phone_w: float = 71.6         # phone SHORT dimension (e.g. iPhone 15 71.6mm)
    phone_h: float = 147.6        # phone LONG dimension (147.6mm) — spans the grips in landscape
    magsafe_d: float = 56.0       # MagSafe magnet ring outer diameter (N52 arc array)
    # v0.11: trackpad = a PCB-INTEGRATED capacitive pad (copper on the front, ~34x26mm
    # so it fits the grip's upper zone with no overhang) driven by an Azoteq IQS7211E
    # controller on the BACK. Unlike a Cirque FFC module this is turnkey-friendly (just
    # copper + one SMD chip) and any size we want. Needs the community Azoteq ZMK driver.
    trackpad_w: float = 34.0
    trackpad_h: float = 26.0
    cluster_pitch: float = 8.5    # D-pad / mouse-button spacing
    feat_key_d: float = 7.0       # cluster switch = same 7mm dome


def _key_centers(c: Config):
    """Ortholinear grid, laid out inner->outer by cumulative COLUMN UNITS so a wide
    key (the bottom-row 2u space) shifts the rest of its row over. Each key carries a
    'w' (width in units); the dome/switch stays single, only the keycap is 2u."""
    field_x0 = c.inner_margin + c.key_w / 2.0
    field_y0 = c.bottom_strip + c.key_h / 2.0 + 4.0
    keys = []
    for r in range(c.rows):
        colpos = 0.0
        for slot, lab in enumerate(RIGHT_LEGENDS[r]):
            w = 2 if (r == c.rows - 1 and slot == 0) else 1
            xc = field_x0 + (colpos + (w - 1) / 2.0) * c.pitch_x
            y = field_y0 + (c.rows - 1 - r) * c.pitch_y
            keys.append({"row": r, "col": slot, "w": w,
                         "x": round(xc, 3), "y": round(y, 3), "label": lab})
            colpos += w
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
    # upper grip zone sized for the D-pad / mouse / page-key cluster + the SMD module
    # behind it. The OPTIONAL trackpad is NOT sized in here (it overhangs the top as a
    # shoulder bump when populated) so the base grip stays short.
    # upper zone must fully clear the D-pad plus-cluster (2*cluster_pitch + key +
    # top/bottom margins) so NAV_D doesn't collide with the F-row below it.
    upper_zone = max(2 * c.cluster_pitch + c.feat_key_d + 10.0, c.ctrl_h + c.usb_gap)
    board_h = top_keys + upper_zone + 2.0
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
    """Static internal harness connector — rotated VERTICAL at the INNER edge so the
    flex exits toward the spine and runs straight across (behind the phone) to the
    other grip's mirror connector at the same height. Latching JST-GH (signals only,
    ~22-24 conductors: 9 rows + 5 left cols + interleaved GND). ~5mm wide x 18mm tall,
    low so the flex clears the spine battery above it. Power stays in this grip."""
    return [1.5, 12.0, 5.0, 18.0]


def _right_edge_x(y, outline):
    """Right-edge x of the (right-grip) outline at height y — so components can be
    clamped inside the rounded/bowed silhouette instead of hanging off it."""
    xs = []
    n = len(outline)
    for i in range(n):
        x1, y1 = outline[i]; x2, y2 = outline[(i + 1) % n]
        if (y1 <= y <= y2) or (y2 <= y <= y1):
            xs.append(max(x1, x2) if y1 == y2 else x1 + (y - y1) / (y2 - y1) * (x2 - x1))
    return max(xs) if xs else 0.0


def _keepouts_mcu(c, board_w, board_h, outer_base, outline, keys):
    ko = {}
    def clamp_right(y, h, w, margin=2.5):
        re = min(_right_edge_x(y, outline), _right_edge_x(y + h, outline),
                 _right_edge_x(y + h / 2, outline)) - margin
        return round(re - w, 2)
    # ALL electronics live in the BOTTOM zone (clear of the rounded top corner + the
    # trackpad above). Module + charger inner-bottom, USB-C + antenna clamped to the
    # outer-bottom edge. LiPo is in the spine (deck.product), not here.
    ko["controller"] = [8.0, 2.0, c.ctrl_w, c.ctrl_h]                 # Ebyte E73, inner-bottom
    ko["charger"] = [round(8.0 + c.ctrl_w + 2.0, 2), 2.5, 5.0, 3.5]
    ko["usb_c"] = [clamp_right(1.0, 4.5, 9.0), 1.0, 9.0, 4.5]          # port at outer-bottom edge
    # PCB MEANDER antenna (front copper, ground cut-out), outer-bottom, far from the
    # centre magnets; short RF run from the module. Drawn as a squiggle, not a box.
    ko["antenna"] = [clamp_right(7.5, 6.0, 13.0), 7.5, 13.0, 6.0]
    ko["bridge"] = _bridge_conn(board_h)
    return ko


def _keepouts_passive(board_h):
    return {"bridge": _bridge_conn(board_h)}


def _mount_holes(board_h, outer_base, bottom_strip, outline):
    """5x M2, clamping the keymat perimeter evenly (i8+ uses screws all round the
    membrane for consistent dome feel). Inner column on the straight inner edge; the
    two outer holes are clamped inside the bowed/rounded outer edge (with M2-boss
    clearance) so they never fall off a corner."""
    inset, d = 3.2, 2.2
    def ox(y):
        e = min(_right_edge_x(y, outline), _right_edge_x(y - 3, outline),
                _right_edge_x(y + 3, outline))
        return round(e - 4.5, 2)                        # 4.5mm = M2 boss + wall
    return [
        {"x": inset, "y": round(bottom_strip * 0.5, 2), "d": d},  # bottom-inner (BELOW the bridge connector)
        {"x": inset, "y": round(board_h * 0.50, 2), "d": d},   # inner-mid
        {"x": inset, "y": round(board_h * 0.86, 2), "d": d},   # top-inner
        {"x": ox(board_h * 0.28), "y": round(board_h * 0.28, 2), "d": d},  # bottom-outer
        {"x": ox(board_h * 0.72), "y": round(board_h * 0.72, 2), "d": d},  # top-outer
    ]


def _features(geo: dict, c: Config) -> list:
    """Non-grid front-face features in the FINAL (post-mirror) grip frame. The
    upper grip zone (above the key field) carries them: RIGHT = Cirque trackpad
    (front) with the MCU behind it + PgUp/PgDn at the outer corner; LEFT = 4-way
    D-pad + OK (inner) + two stacked mouse buttons (outer)."""
    ys = [k["y"] for k in geo["keys"]]
    field_top = max(ys) + c.key_h / 2
    W = geo["board_w"]
    ob = geo["outer_base"]
    p = c.cluster_pitch
    feats = []
    # clusters are CENTRED in the upper zone (which is now sized to fit them) so the
    # D-pad's bottom key clears the F-row and its top key clears the board edge.
    cy_lo = (field_top + geo["board_h"]) / 2.0        # upper-zone mid
    if geo["side"] == "right":
        # inner edge at x=0; grip body toward +x. PCB-integrated capacitive trackpad
        # (IQS7211E), sized to fit the upper zone with NO overhang.
        feats.append({"type": "trackpad", "label": "IQS7211E pad",
                      "x": round(ob * 0.40, 2), "y": round((field_top + geo["board_h"]) / 2, 2),
                      "w": c.trackpad_w, "h": c.trackpad_h})
        ox = ob - 8.5                                 # page keys inboard of the outer edge
        feats.append({"type": "key", "label": "PGUP", "x": round(ox, 2), "y": round(cy_lo + 5.5, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "PGDN", "x": round(ox, 2), "y": round(cy_lo - 5.5, 2), "d": c.feat_key_d})
    else:
        # left grip: inner edge at x=W; grip body toward -x (mirrored)
        cx = W - ob * 0.44                            # D-pad centre (inner-ish)
        feats.append({"type": "key", "label": "NAV_OK", "x": round(cx, 2), "y": round(cy_lo, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "NAV_U", "x": round(cx, 2), "y": round(cy_lo + p, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "NAV_D", "x": round(cx, 2), "y": round(cy_lo - p, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "NAV_L", "x": round(cx + p, 2), "y": round(cy_lo, 2), "d": c.feat_key_d})  # +x = toward inner/screen
        feats.append({"type": "key", "label": "NAV_R", "x": round(cx - p, 2), "y": round(cy_lo, 2), "d": c.feat_key_d})
        ox = W - ob + 11.0                            # mouse buttons inboard of the outer edge
        feats.append({"type": "key", "label": "MB_L", "x": round(ox, 2), "y": round(cy_lo + 5.5, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "MB_R", "x": round(ox, 2), "y": round(cy_lo - 5.5, 2), "d": c.feat_key_d})
    return feats


def build(c: Config) -> dict:
    keys, field_x0 = _key_centers(c)
    outline, board_w, board_h, outer_base = _outline(c, keys)
    holes = _mount_holes(board_h, outer_base, c.bottom_strip, outline)
    anchor = [round(outer_base * 0.85, 2), 6.0]
    geo = {
        "side": "right", "role": "mcu",
        "board_w": round(board_w, 3), "board_h": round(board_h, 3),
        "outer_base": round(outer_base, 3),
        "keys": keys, "outline": outline,
        "keepouts": _keepouts_mcu(c, board_w, board_h, outer_base, outline, keys),
        "mount_holes": holes, "anchor": anchor,
        "arc": {"rmin": 22.0, "rmax": 84.0},
        "config": asdict(c),
    }
    if c.side == "left":
        geo = mirror(geo)
    geo["features"] = _features(geo, c)
    return geo


def product(c: Config) -> dict:
    """Whole-assembly geometry for the product view: both grips placed with the
    phone + MagSafe ring between them. Right grip inner edge at x=0; left grip
    mirrored to the left of the phone. Returns a single scene in product mm."""
    right = build(Config(**{**c.__dict__, "side": "right"}))
    left = build(Config(**{**c.__dict__, "side": "left"}))
    # LANDSCAPE: the phone's LONG side spans horizontally between the grips; its
    # SHORT side is vertical (centred on the grip midline). Portrait swaps these.
    if c.orientation == "landscape":
        span_x, span_y = max(c.phone_w, c.phone_h), min(c.phone_w, c.phone_h)
    else:
        span_x, span_y = min(c.phone_w, c.phone_h), max(c.phone_w, c.phone_h)
    gap = span_x                         # centre gap = phone horizontal extent
    rx = gap / 2.0
    lx = -gap / 2.0 - left["board_w"]
    cy = right["board_h"] / 2.0
    return {
        "right": right, "left": left,
        "right_origin": [round(rx, 2), 0.0],
        "left_origin": [round(lx, 2), 0.0],
        "phone": {"w": span_x, "h": span_y,
                  "x": round(-span_x / 2, 2), "y": round(cy - span_y / 2, 2)},
        "magsafe": {"cx": 0.0, "cy": round(cy, 2), "d": c.magsafe_d},
        # LiPo sits INSIDE the spine, directly BEHIND the MagSafe ring (centred on it),
        # sandwiched between the back shell and front shell. The N52 ring is applied to
        # the OUTSIDE of the front shell (top of the stack); the phone mates to it.
        # Short wire to the right-grip charger; does NOT cross the left bridge.
        "spine_battery": {"w": 52.0, "h": 36.0, "x": -26.0, "y": round(cy - 18.0, 2)},
        "config": asdict(c),
    }


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
