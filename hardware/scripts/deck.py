# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman

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

VERSION = "v0.20"

# --- key legends (i8+-inspired QWERTY, split L/R, arrow cluster on right) -----
# v0.6: grown to 6 cols x 6 rows/half (~36/half) to match the sketch + the
# Rii i8+, which the user thumb-types daily (57mm half @ ~9.5mm pitch). At our
# tighter 8.5x8.8 pitch a 6x6 half is only 51x53mm — smaller than the i8+ half,
# so reach is proven; edge legends below are PROVISIONAL (best read of the
# sketch — nav cluster / trackpad / arrows not yet placed). col 0 = INNER edge.
# v0.13: bottom row = a DOUBLE-WIDE (2u) space bar at the inner edge, then 4 keys.
# The MENU key is dropped and the row shifts over one (5 keycaps span the 6-unit width).
# v0.16 (Rii-follow): ENTER is a DOUBLE-WIDE key at the outer end of the H-row,
# like the i8+. The apostrophe key gives up its physical spot (5 caps span the
# 6-unit width); SQT moves to FN+; in the keymap.
# v0.20 (mirrored modifiers): the 147mm phone gap means a thumb can never reach
# the opposite grip, so any modifier+same-side-key chord needs that modifier on
# BOTH grips (Ctrl+Z/X/C/V/A/S are all left-grip letters). Both grips now end in
# the identical stack — CTL at the bottom-outside corner, SHF directly above it,
# ALT beside Space (the Rii's own Alt|Space|AltGr grammar; AGR was already RAlt).
# Backslash gives up its cap: BSLH moves to FN+], PIPE to FN+[ (direct bindings,
# no Shift — same demotion pattern as SQT on FN+;). No sticky/one-shot behaviors:
# chords are plain holds; rare triples use the corner CTL+SHF bridge or a
# cross-hand reach.
RIGHT_LEGENDS = [
    ["F6", "F7", "F8", "F9", "F10", "DEL"],
    ["6",  "7",  "8",  "9",  "0",   "BSP"],
    ["Y",  "U",  "I",  "O",  "P",   ";"],
    ["H",  "J",  "K",  "L",  "ENT"],          # ENT = 2u (Rii-style wide Enter)
    ["N",  "M",  ",",  ".",  "/",   "SHF"],
    ["SPC", "ALT", "[", "]",  "CTL"],         # SPC = 2u; v0.20: AGR->ALT, \->CTL
]

# double-wide keycaps (one dome under the cap centre, like the i8+)
WIDE_KEYS = {"SPC": 2, "ENT": 2}
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
    # v0.17: RECTANGULAR keys (Rii i8+ chiclet feel) to shrink the key-field HEIGHT — the
    # user thumb-types an i8+ daily and its keys are ~9x7mm, wider than tall. Ours go 8.5w
    # x 7.0h, so H-pitch 10.0 / V-pitch 9.0 keep a printable gutter both ways (1.5mm X,
    # 2.0mm Y >= the 1.5mm PETG-FDM minimum). The 7mm domes (contact courtyard r3.9) still
    # clear at 9.0 V-pitch — 1.2mm courtyard gap, pads/via-keepouts non-overlapping. This
    # drops the 6-row field 55.5 -> 52.0mm; with the chin cut + module-to-top it takes the
    # grip 114.5 -> ~99mm (Rii i8+ ~97mm). See docs/design-decisions.md.
    pitch_x: float = 10.0
    pitch_y: float = 9.0
    key_w: float = 8.5
    key_h: float = 7.0
    col_stagger: float = 0.0      # ortholinear (was 1.3 arc-stagger through v0.4)
    arc_bow: float = 0.0          # ortholinear (was 0.06 through v0.4)
    # v0.15: 6 -> 8 so the 16-pin FFC ZIF bridge connector (6.7mm deep) fits on the
    # inner edge without touching the key field (dome courtyards start at margin+0.1).
    # v0.19: grip_margin 7.0 -> 8.5 — with the outer bow deleted (GBC straight edge)
    # the outer M3 boss column (Ø7.5 @ edge-4.2) needs ~1mm the bow used to provide,
    # and +0.5 more is the routing-congestion relief (at 8.0 Freerouting left 1-3
    # nets open on every attempt; the bow's 0-6mm lane is gone). FACE cheek is a
    # constant ~11.4mm — still ~4.5mm tighter than the old bow apex.
    inner_margin: float = 8.0
    grip_margin: float = 8.5
    outer_bow: float = 0.0        # DEAD since v0.19 (GBC straight outer edge); kept for history
    # v0.19 (feedback item 2): the phone well gets closing END WALLS extending up from
    # the center panel — the spine gap grows by (well_end_wall + 0.35 well x-clearance)
    # per side so there is material between the phone's ends and the panel edges.
    well_end_wall: float = 1.6
    # v0.10: LiPo moved to the central SPINE (behind the MagSafe ring), so the grip
    # bottom zone only needs USB-C + charger + bridge — shrinks the grip height so it
    # no longer dwarfs the phone (target ~grip = phone_short + ~2x12mm overhang, i8+-like).
    # v0.15: 14 -> 19: the E73 sat antenna-down at the bottom EDGE, which needed the full
    # 18mm module length below the key field plus a passive lane above it.
    # v0.17: 19 -> 7. The E73 + the WHOLE power front-end moved to the TOP zone (the
    # vacated trackpad space); antenna now points UP off the top edge — away from the palm
    # that cradles the bottom, and off the far edge from the centred phone/LiPo.
    # The bottom strip now only carries the FFC-bridge exit + one mount boss + the JST, so
    # the "chin" below the space row is ~9mm (was ~23mm) — Rii-like. It can be trimmed
    # further (~5mm) by moving the JST up to the top cluster, at the cost of a tighter bottom
    # shell wall; kept at 7 for a comfortable printable wall + bottom keymat screw.
    bottom_strip: float = 7.0
    # v0.9 (PCBA sourcing): MCU module is the **Ebyte E73-2G4M08S1C** nRF52840
    # (JLC C356849) — the Raytac MDBT50Q was out of stock / not reliably
    # JLC-placeable. The E73 is in the JLC library, is the community-standard
    # ZMK nRF52840 module, and machine-places (Extended, X-ray). On the BACK.
    # Still a certified radio: no FCC/RED cert, RF match, crystals or Zephyr port.
    ctrl_w: float = 13.0          # Ebyte E73-2G4M08S1C module width (13 x 18 mm)
    ctrl_h: float = 18.0          # module length; ceramic-antenna end faces the BOTTOM edge
    antenna_h: float = 5.0        # module antenna zone: no-copper keep-out (all layers), at the board edge
    usb_gap: float = 6.0          # access gap
    top_pad: float = 4.0
    phone_len: float = 160.0
    env_w_max: float = 64.0
    env_h_max: float = 126.0      # taller: vertical module + antenna overhang
    side: str = "right"
    # --- v0.7: phone target + MagSafe centre-mount + cluster/trackpad features ---
    # v0.18: placeholder iPhone dims (71.6 x 147.6) replaced with the user's REAL
    # phone — Samsung Galaxy S25 Ultra, 162.8 x 77.6 x 8.2 mm — worn in a typical
    # thin case (case_t per side/back). The spine gap is sized to the CASED phone,
    # and the v0.18 sunken panel puts the cased screen surface FLUSH with the grip
    # lids' keyboard face. Device width follows the phone's length by construction
    # (grips flank the phone) — the S25U is 15.2mm longer than the old placeholder.
    target: str = "phone"         # phone MagSafe-mounts to the centre (not a Pi)
    orientation: str = "landscape"  # phone held LANDSCAPE between the grips (Steam-Deck style)
    phone_w: float = 77.6         # phone SHORT dimension (S25 Ultra 77.6mm, bare)
    phone_h: float = 162.8        # phone LONG dimension (S25 Ultra 162.8mm, bare) — spans the grips in landscape
    phone_t: float = 8.2          # phone THICKNESS (S25 Ultra 8.2mm, bare)
    case_t: float = 1.2           # typical thin case: added per side AND behind the back
    magsafe_d: float = 56.0       # MagSafe magnet ring outer diameter (N52 arc array)
    # v0.11: trackpad = a PCB-INTEGRATED capacitive pad (copper on the front, ~34x26mm
    # so it fits the grip's upper zone with no overhang) driven by an Azoteq IQS7211E
    # controller on the BACK. Unlike a Cirque FFC module this is turnkey-friendly (just
    # copper + one SMD chip) and any size we want. Needs the community Azoteq ZMK driver.
    trackpad_w: float = 34.0
    trackpad_h: float = 26.0
    cluster_pitch: float = 8.5    # D-pad / mouse-button spacing
    feat_key_d: float = 7.0       # cluster switch = same 7mm dome


def _key_centers(c: Config, legends):
    """Ortholinear grid, laid out inner->outer by cumulative COLUMN UNITS so a wide
    key (2u space, 2u Enter) shifts the rest of its row over. Each key carries a
    'w' (width in units); the dome/switch stays single, only the keycap is wide.
    Grids may differ per side (the right H-row has 5 caps: HJKL + 2u ENT)."""
    field_x0 = c.inner_margin + c.key_w / 2.0
    field_y0 = c.bottom_strip + c.key_h / 2.0 + 2.0   # v0.17: +4 -> +2 (chin trimmed)
    keys = []
    for r in range(c.rows):
        colpos = 0.0
        for slot, lab in enumerate(legends[r]):
            w = WIDE_KEYS.get(lab, 1)
            xc = field_x0 + (colpos + (w - 1) / 2.0) * c.pitch_x
            y = field_y0 + (c.rows - 1 - r) * c.pitch_y
            keys.append({"row": r, "col": slot, "w": w,
                         "x": round(xc, 3), "y": round(y, 3), "label": lab})
            colpos += w
        assert colpos <= c.cols, f"row {r} spans {colpos} units > {c.cols}"
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
    # v0.17: the upper grip zone now carries ALL the SMD electronics on the BACK (E73 +
    # power front-end, relocated up from the old bottom strip) with the front-face cluster
    # stacked over them (LEFT: D-pad + mouse buttons / RIGHT: PgUp-PgDn at the outer corner).
    # Height is driven by the D-pad plus-cluster (2*cluster_pitch + key + margins), which
    # also comfortably clears the 18mm E73 body hanging antenna-up from the top edge
    # (ctrl_h + usb_gap). NAV_D still clears the F-row below it.
    upper_zone = max(2 * c.cluster_pitch + c.feat_key_d + 10.0, c.ctrl_h + c.usb_gap)
    board_h = top_keys + upper_zone + 2.0
    # v0.19: Game-Boy-Color silhouette — the outer parabolic bow is GONE (it was the
    # widest part of the cheek; the user found it blocks thumb reach to the edge-adjacent
    # keys). The outer edge is now STRAIGHT at outer_base, so the cheek is a constant
    # grip_margin, and the outline is a rectangle with GBC-style corners: tucked top
    # (r 8.0 — antenna/E73-pinned, cannot go rounder) and a soft r 11.0 bottom corner,
    # plus a 1.0mm parabolic bottom CROWN (the GBC's gently convex bottom edge).
    r_in, r_out_top, r_out_bot = 4.0, 8.0, 11.0
    crown = 1.0

    pts = [[0.0, r_in], [0.0, board_h - r_in]]
    pts += _arc(r_in, board_h - r_in, r_in, 180, 90, 5)
    pts.append([outer_base - r_out_top, board_h])
    pts += _arc(outer_base - r_out_top, board_h - r_out_top, r_out_top, 90, 0, 8)
    pts.append([outer_base, board_h - r_out_top])
    pts.append([outer_base, r_out_bot])
    pts += _arc(outer_base - r_out_bot, r_out_bot, r_out_bot, 0, -90, 8)
    # bottom crown: shallow parabola sagging `crown` below y=0 between the corner-arc
    # tangent points (chord spacing ~3mm >= the 0.3mm DSN floor; endpoints snapped
    # exactly to the arc ends so no micro-segments are emitted)
    x1, x0 = outer_base - r_out_bot, r_in
    n = 16
    for i in range(1, n):
        x = x1 - (x1 - x0) * i / n
        t = (x - (x0 + x1) / 2) / ((x1 - x0) / 2)
        pts.append([round(x, 3), round(-crown * (1.0 - t * t), 3)])
    pts.append([r_in, 0.0])
    pts += _arc(r_in, r_in, r_in, -90, -180, 5)
    board_w = max(p[0] for p in pts)
    return pts, board_w, board_h, outer_base


def _bridge_conn(board_h):
    """Static internal harness connector — a 16-pin 1.0mm-pitch FFC ZIF (SMT, ~2mm
    tall, bottom contacts) rotated VERTICAL at the INNER edge; the 16-way type-A FFC
    jumper exits toward the spine and runs flat across (behind the phone, at back-
    cavity level) to the other grip's connector. 9 rows + 5 left cols + 2 GND.
    Low on the board so the ribbon clears the spine battery above it. Power stays
    in this grip. [x, y, w, h] advisory box in deck mm."""
    return [0.5, 12.5, 6.5, 21.0]


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
    # v0.17: ALL electronics live in the TOP zone now (the vacated trackpad space), so the
    # chin can be trimmed. Layout mirrors the old bottom cluster, flipped to the top edge
    # (matches gen_board.py place_components): E73 antenna-UP at the top edge (inner-ish),
    # USB-C mouth flush with the top edge, ESD inline, charger + battery-cap + LED +
    # power/reset switches beside them, FFC bridge + JST-PH battery on the inner edge,
    # passive lane (SWD / spare-GPIO / row pulldowns / divider) just below the module.
    # LiPo is in the spine (deck.product), not here.
    # Advisory boxes track gen_board.place_components' 180-deg + DX cluster rotation:
    # E73 antenna-UP at the CENTRE-top edge, USB-C mouth beside it, charger/power cluster
    # toward the inner-top, divider at the outer-top. (JST is placed separately in the chin.)
    top = board_h
    ko["controller"] = [50.0, top - 18.0, c.ctrl_w, c.ctrl_h]  # Ebyte E73, antenna-up at the centre-top edge
    ko["antenna"] = [48.0, top - 1.0, 17.0, 6.5]              # module antenna keep-out, crossing the TOP edge
    ko["usb_c"] = [30.75, top - 9.5, 9.5, 9.5]                # J1 mouth flush with the top edge
    ko["charger"] = [15.0, top - 11.0, 16.0, 9.0]           # U2/U3 + caps + LED + switches, inner-top
    ko["bridge"] = _bridge_conn(board_h)
    return ko


def _keepouts_passive(board_h):
    return {"bridge": _bridge_conn(board_h)}


_BOSS_R = 4.0        # shell standoff-boss radius the holes must assume (Ø7.5 M3 + margin)
_DOME_COURT_R = 3.9  # snap-dome contact courtyard radius

def _mount_holes(board_h, outer_base, bottom_strip, outline):
    """5x M3 (v0.19: countersunk face screws), clamping the keymat perimeter evenly
    (i8+ uses screws all round the membrane for consistent dome feel). Inner column
    on the straight inner edge; outer column on the now-STRAIGHT outer edge at a
    fixed pull-in. Every hole keeps >=2.5mm hole-edge to the board edge and
    >=_BOSS_R+_DOME_COURT_R c-c to any dome (asserted in build())."""
    inset, d = 4.2, 3.4
    ocol = round(outer_base - 4.2, 2)     # hole-edge to board edge = 4.2 - d/2 = 2.5
    # v0.19 placements (M3 bosses are fatter than the old M2's — centers re-tuned):
    # H3 y 72.0 clears the PGDN dome FOOTPRINT BBOX by >=4.0 (the gen_board gate
    # measures bbox corners, stricter than disc c-c — y 74.5 failed it at 3.07);
    # H4 y 19.4 sits above the bottom-corner tangent (r11 + crown); H5 y 68.0
    # clears the E73/charger zone above it AND the mirrored left grip's
    # mouse-button column (c-c 8.55 after the v0.19 cluster re-anchor).
    return [
        {"x": 4.6, "y": 6.0, "d": d},                          # bottom-inner (in the trimmed chin; nudged off the inner edge for wall)
        {"x": inset, "y": round(board_h * 0.42, 2), "d": d},   # inner-mid
        {"x": inset, "y": 72.0, "d": d},                       # top-inner (inner edge, left of the E73 body)
        {"x": ocol, "y": 19.4, "d": d},                        # bottom-outer
        {"x": ocol, "y": 68.0, "d": d},                        # top-outer (below the PgUp/PgDn cluster)
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
        # inner edge at x=0; grip body toward +x. (The PCB-integrated trackpad was
        # DROPPED for v1 — pointer duty goes to ZMK mouse keys; the I2C pins are
        # broken out to spare pads for a rev-B trackpad. No feature emitted.)
        # v0.17: the E73 + power cluster now fill the OUTER/centre of this top zone (module
        # antenna at the outer-top edge, farthest from the phone = best RF), so PgUp/PgDn
        # move to the INNER-top corner — clear of the module body and its back-side
        # diodes/vias, still an easy up-and-in flick for the right thumb.
        ix = c.inner_margin + 3.0
        feats.append({"type": "key", "label": "PGUP", "x": round(ix, 2), "y": round(geo["board_h"] - 6.5, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "PGDN", "x": round(ix, 2), "y": round(geo["board_h"] - 17.5, 2), "d": c.feat_key_d})
    else:
        # left grip: inner edge at x=W; grip body toward -x (mirrored)
        # v0.19: the cluster is anchored to the INNER edge (where the key field lives)
        # instead of outer_base — the old ob-relative formulas silently dragged the
        # cluster 5mm when the outer edge came in for the GBC outline, planting the
        # mouse-button dome courtyard inside the mirrored top-outer M3 boss (c-c 6.96
        # < 7.9). Offsets 32.3 / 62.5 reproduce the proven v0.17 positions exactly.
        cx = W - 32.3                                 # D-pad centre (inner-ish)
        feats.append({"type": "key", "label": "NAV_OK", "x": round(cx, 2), "y": round(cy_lo, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "NAV_U", "x": round(cx, 2), "y": round(cy_lo + p, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "NAV_D", "x": round(cx, 2), "y": round(cy_lo - p, 2), "d": c.feat_key_d})
        # v0.19c: LEFT arrow on the physical LEFT. On the left grip +x = toward the
        # inner/screen edge = physical RIGHT, so NAV_L must sit at cx-p (toward the
        # outer edge) and NAV_R at cx+p. Through v0.19b these were swapped, printing
        # the left/right arrow glyphs (and routing the keycodes) reversed.
        feats.append({"type": "key", "label": "NAV_L", "x": round(cx - p, 2), "y": round(cy_lo, 2), "d": c.feat_key_d})  # -x = toward outer = physical left
        feats.append({"type": "key", "label": "NAV_R", "x": round(cx + p, 2), "y": round(cy_lo, 2), "d": c.feat_key_d})  # +x = toward inner/screen = physical right
        # v0.19b: 62.5 -> 57.25 from the inner edge (17.75 from the outer). At 12.5
        # from the outer edge the buttons sat ON the grid column-6 line: COL6 had to
        # thread the top dome's ring-escape gap and then squeeze past the mirrored
        # H5 boss keepout — Freerouting left SW42 (MB_R) open on EVERY attempt. In
        # the between-column gutter the approach is free (and 17.75 is within 0.8mm
        # of the proven v0.17 position).
        ox = W - 57.25                                # mouse buttons inboard of the outer edge
        feats.append({"type": "key", "label": "MB_L", "x": round(ox, 2), "y": round(cy_lo + 5.5, 2), "d": c.feat_key_d})
        feats.append({"type": "key", "label": "MB_R", "x": round(ox, 2), "y": round(cy_lo - 5.5, 2), "d": c.feat_key_d})
    return feats


def build(c: Config) -> dict:
    # each side lays out its OWN legend grid (inner->outer); mirror() then flips
    # the left grip's frame without relabelling
    keys, field_x0 = _key_centers(c, RIGHT_LEGENDS if c.side == "right" else LEFT_LEGENDS)
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
    # v0.19 envelope asserts — the margins are deliberately tight (2.5mm hole-edge,
    # boss-vs-dome-courtyard exact) so they must fail LOUDLY, not by re-derivation:
    allk = list(geo["keys"]) + [f for f in geo["features"] if f["type"] == "key"]
    for h in geo["mount_holes"]:
        for k in allk:
            cc = math.hypot(k["x"] - h["x"], k["y"] - h["y"])
            assert cc >= _BOSS_R + _DOME_COURT_R - 1e-6, \
                f"{geo['side']}: hole ({h['x']},{h['y']}) c-c {cc:.2f} to key {k['label']} < {_BOSS_R + _DOME_COURT_R}"
    return geo


def product(c: Config) -> dict:
    """Whole-assembly geometry for the product view: both grips placed with the
    phone + MagSafe ring between them. Right grip inner edge at x=0; left grip
    mirrored to the left of the phone. Returns a single scene in product mm."""
    right = build(Config(**{**c.__dict__, "side": "right"}))
    left = build(Config(**{**c.__dict__, "side": "left"}))
    # LANDSCAPE: the phone's LONG side spans horizontally between the grips; its
    # SHORT side is vertical (centred on the grip midline). Portrait swaps these.
    # v0.18: all phone geometry is the CASED envelope (bare + 2*case_t per axis) —
    # the pocket/gap must fit the phone as worn, and the flush-screen z-stack is
    # computed from the cased thickness (deck3d).
    if c.orientation == "landscape":
        span_x, span_y = max(c.phone_w, c.phone_h), min(c.phone_w, c.phone_h)
    else:
        span_x, span_y = min(c.phone_w, c.phone_h), max(c.phone_w, c.phone_h)
    span_x += 2 * c.case_t
    span_y += 2 * c.case_t
    # v0.19: gap = cased phone + 0.35/side well x-clearance + well_end_wall/side +
    # 0.3/side panel-lid reveal — the extra material closes the well's x-ends
    # (feedback item 2: the old span_x+0.6 put the phone ends exactly AT the panel
    # edges, leaving open slots into the grip cavities)
    gap = span_x + 2 * (0.35 + c.well_end_wall + 0.3)
    rx = gap / 2.0
    lx = -gap / 2.0 - left["board_w"]
    cy = right["board_h"] / 2.0
    return {
        "right": right, "left": left,
        # origins rounded to 3 decimals to MATCH build()'s board_w precision —
        # at 2 decimals a 3rd-decimal board_w (v0.17: 79.493) shifts the left
        # grip's inner edge 0.003mm off the seam and deck3d's frame assert trips
        "right_origin": [round(rx, 3), 0.0],
        "left_origin": [round(lx, 3), 0.0],
        "phone": {"w": span_x, "h": span_y,
                  "x": round(-span_x / 2, 2), "y": round(cy - span_y / 2, 2)},
        "magsafe": {"cx": 0.0, "cy": round(cy, 2), "d": c.magsafe_d},
        # v0.18: the LiPo moved OUT of the spine — the sunken phone well (screen
        # flush with the lids) leaves only ~0.5mm under its floor slab, so no
        # standard cell fits behind the ring any more. The cell is now a 403040
        # (4.0 x 30 x 40, ~450-500mAh) in the LEFT grip's back cavity, foam-taped
        # to the floor UNDER the passive PCB (the only parts there are diodes,
        # 1.16mm deep, and the FFC ZIF at the inner edge — 5.1mm of free depth vs
        # 0.24mm in the right cavity where the mated JST-PH lives). Leads run
        # along the spine's bottom border (outside the phone well) to J3 on the
        # right board. Grip-local rect on the LEFT grip, converted to product mm.
        "battery": {"cell": "403040", "t": 4.0, "grip": "left",
                    "w": 30.0, "h": 40.0,
                    "x": round(lx + 22.0, 2), "y": 13.0},
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
        k["x"] = round(W - k["x"], 3)   # labels already come from LEFT_LEGENDS
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
