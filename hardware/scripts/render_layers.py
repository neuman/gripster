#!/usr/bin/env python3
"""
render_layers.py — the assembly as STACKABLE LAYERS. Five PNGs on an identical
canvas (same size + positioning) so they overlay pixel-for-pixel or flip through
as an animation, back-to-front:

  layer_1_back_shell.png   bottom case: shell, screw bosses, MagSafe + battery
                           pocket in the spine, USB-C cutout
  layer_2_pcb_back.png     PCB back side: module, 81 diodes, charger/USB-C/ESD,
                           connectors, ROW traces, silkscreen refs
  layer_3_pcb_front.png    PCB front side: 81 dome pads, COLUMN traces, mount
                           holes, key silkscreen
  layer_4_keymats.png      one-piece keymats: keycaps + living-hinge strips
  layer_5_front_shell.png  top case: shell with key openings, phone + trackpad
                           windows, screw holes

Whole device (both grips + central spine), front view. Neutral per-layer styling
(no column/row colour-coding). Geometry from deck.product().
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, Rectangle, Circle
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "renders"))
FIGSIZE = (16.0, 7.0)
DPI = 150
BG = "#0b0f14"

INK = "#cfd6dd"      # neutral light
SHELL = "#3a4149"    # case grey
SHELL_HI = "#4c545d"
PCB = "#0e2a1e"      # board green
PCB_ED = "#1f7a52"
SILK = "#e8edf2"
COPPER = "#b87333"


def _bbox(P):
    lx = P["left_origin"][0]
    rx = P["right_origin"][0] + P["right"]["board_w"]
    top = max(P["right"]["board_h"], P["left"]["board_h"]) + 16  # room for trackpad bump
    return lx - 8, rx + 8, -10, top


def _ax(fig, P):
    ax = fig.add_axes([0, 0, 1, 1])
    x0, x1, y0, y1 = _bbox(P)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_facecolor(BG)
    return ax


def _grip_outline(geo, ox, oy):
    return [[x + ox, y + oy] for x, y in geo["outline"]]


def _spine_rect(P):
    g = P["config"]["phone_w"] if False else None
    gap_x0 = P["left_origin"][0] + P["left"]["board_w"]
    gap_x1 = P["right_origin"][0]
    h = max(P["right"]["board_h"], P["left"]["board_h"])
    return gap_x0, 0.0, gap_x1 - gap_x0, h


# ---------- layer 1: back shell ----------
def back_shell(ax, P):
    for side, key in (("left", "left"), ("right", "right")):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        ax.add_patch(Polygon(_grip_outline(geo, ox, oy), closed=True,
                     facecolor=SHELL, edgecolor=SHELL_HI, lw=2.5, zorder=2))
    sx, sy, sw, sh = _spine_rect(P)
    ax.add_patch(FancyBboxPatch((sx, sy), sw, sh, boxstyle="round,pad=0,rounding_size=6",
                 facecolor=SHELL, edgecolor=SHELL_HI, lw=2.5, zorder=1))
    # MagSafe + battery pockets in the spine
    ms = P["magsafe"]
    ax.add_patch(Circle((ms["cx"], ms["cy"]), ms["d"] / 2, facecolor="#2b3239",
                 edgecolor=INK, lw=1.4, zorder=3))
    ax.text(ms["cx"], ms["cy"] + ms["d"] / 2 - 6, "MagSafe pocket", ha="center", fontsize=7, color=INK, zorder=4)
    # v0.18: LiPo 403040 sits in the LEFT grip's back cavity (foam-taped to the
    # floor under the passive PCB) — the sunken phone well displaced it from the spine
    sb = P["battery"]
    ax.add_patch(Rectangle((sb["x"], sb["y"]), sb["w"], sb["h"], facecolor="#2b3239",
                 edgecolor=INK, ls="--", lw=1.2, zorder=4))
    ax.text(sb["x"] + sb["w"] / 2, sb["y"] + 5, f"LiPo {sb['cell']}", ha="center", fontsize=6, color=INK, zorder=4)
    # screw bosses
    for key in ("left", "right"):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        for h in geo["mount_holes"]:
            ax.add_patch(Circle((h["x"] + ox, h["y"] + oy), 2.6, facecolor="#2b3239",
                         edgecolor=INK, lw=1.1, zorder=4))
            ax.add_patch(Circle((h["x"] + ox, h["y"] + oy), h["d"] / 2, facecolor=BG, edgecolor=INK, lw=0.8, zorder=5))
    # USB-C cutout on the right grip outer-bottom
    geo = P["right"]; ox, oy = P["right_origin"]
    ux, uy, uw, uh = geo["keepouts"]["usb_c"]
    ax.add_patch(Rectangle((ux + ox, oy - 1), uw, 3, facecolor=BG, edgecolor=INK, lw=1.2, zorder=5))
    ax.text(ux + ox + uw / 2, oy + 4, "USB-C", ha="center", fontsize=6, color=INK, zorder=5)


# ---------- PCB helpers ----------
def _pcb(ax, geo, ox, oy):
    ax.add_patch(Polygon(_grip_outline(geo, ox, oy), closed=True,
                 facecolor=PCB, edgecolor=PCB_ED, lw=2.0, zorder=2))
    for h in geo["mount_holes"]:
        ax.add_patch(Circle((h["x"] + ox, h["y"] + oy), h["d"] / 2, facecolor=BG, edgecolor=PCB_ED, lw=1.0, zorder=6))


def _meander(ax, x, y, w, h, n=6):
    """A fat serpentine PCB antenna trace inside a rect."""
    seg = w / n; pts = []
    for i in range(n + 1):
        xi = x + i * seg; top = (i % 2 == 0)
        pts += [(xi, y + (h if top else 0)), (xi, y + (0 if top else h))]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=COPPER, lw=2.4,
            solid_capstyle="round", solid_joinstyle="round", zorder=4)


def _via(ax, x, y):
    ax.add_patch(Circle((x, y), 0.7, facecolor=BG, edgecolor=COPPER, lw=0.5, zorder=6))


def pcb_front(ax, P):
    # FRONT = vertical COLUMN traces + inner-margin row feeders + trackpad + antenna.
    # Layers only ever connect through vias (never cross on the same copper layer).
    for key in ("left", "right"):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        _pcb(ax, geo, ox, oy)
        keys = geo["keys"]
        cols, rows = {}, {}
        for k in keys:
            cols.setdefault(k["col"], []).append(k); rows.setdefault(k["row"], []).append(k)
        collect_y = min(k["y"] for k in keys) - 7
        for c, ks in cols.items():                       # vertical columns over the keys
            x = ks[0]["x"] + ox
            ax.plot([x, x], [collect_y + oy, max(k["y"] for k in ks) + oy + 4],
                    color=COPPER, lw=1.5, alpha=0.85, zorder=3)
        fx = 3.2 + ox                                    # inner-margin row feeders (front)
        for r, ks in rows.items():
            ry = ks[0]["y"] + oy
            ax.plot([fx, fx], [collect_y + oy, ry], color="#d18a4a", lw=1.0, alpha=0.7, zorder=3)
            _via(ax, fx, ry)                             # feeder -> back row
        allk = list(keys) + [f for f in geo.get("features", []) if f["type"] == "key"]
        for k in allk:                                   # dome pad + per-key via
            ax.add_patch(Circle((k["x"] + ox, k["y"] + oy), 3.5, facecolor="#caa46a",
                         edgecolor="#edd7b0", lw=0.8, zorder=5))
            _via(ax, k["x"] + ox + 2.6, k["y"] + oy - 2.6)
            ax.text(k["x"] + ox, k["y"] + oy, k.get("label", "").replace("NAV_", "").replace("MB_", "M"),
                    ha="center", va="center", fontsize=4.0, color="#3a2d10", fontweight="bold", zorder=6)
        for f in geo.get("features", []):
            if f["type"] == "trackpad":                  # PCB-integrated cap pad (front copper)
                tw, th = f["w"], f["h"]
                ax.add_patch(Rectangle((f["x"] + ox - tw / 2, f["y"] + oy - th / 2), tw, th,
                             facecolor="#8a6a3a", edgecolor=COPPER, lw=1.2, hatch="xx", alpha=0.5, zorder=4))
                ax.text(f["x"] + ox, f["y"] + oy, "cap. trackpad\n(front copper)", ha="center",
                        va="center", fontsize=5, color="#f1e2c8", zorder=6)
        if "antenna" in geo["keepouts"]:                 # module antenna keep-out at the edge
            axk, ay, aw, ah = geo["keepouts"]["antenna"]
            ax.add_patch(Rectangle((axk + ox, ay + oy), aw, ah, facecolor="none",
                         edgecolor=COPPER, ls=":", lw=1.0, hatch="//", alpha=0.5, zorder=4))
            ax.text(axk + ox + aw / 2, ay + oy + ah + 1, "E73 antenna keep-out (all layers)", ha="center",
                    va="bottom", fontsize=4.2, color=COPPER, zorder=6)
        ax.text(ox + geo["board_w"] * 0.5, oy - 4,
                "FRONT copper: vertical COLUMNS · inner row-feeders · dome pads   ● = via to back",
                ha="center", fontsize=5.2, color=COPPER, zorder=7)


def pcb_back(ax, P):
    # BACK = horizontal ROW traces + diodes + all chips. Rows and columns cross only
    # through vias, so nothing shorts (Rii i8+ topology).
    for key in ("left", "right"):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        _pcb(ax, geo, ox, oy)
        keys = geo["keys"]
        rows = {}
        for k in keys:
            rows.setdefault(k["row"], []).append(k)
        for r, ks in rows.items():                       # horizontal rows, to the inner via column
            ry = ks[0]["y"] + oy
            ax.plot([3.2 + ox, max(k["x"] for k in ks) + ox + 4], [ry, ry],
                    color=COPPER, lw=1.5, alpha=0.85, zorder=3)
            _via(ax, 3.2 + ox, ry)
        allk = list(keys) + [f for f in geo.get("features", []) if f["type"] == "key"]
        for k in allk:                                   # diode + per-key via
            ax.add_patch(Rectangle((k["x"] + ox - 1.1, k["y"] + oy - 0.7), 2.2, 1.4,
                         facecolor="#2b2b2b", edgecolor=SILK, lw=0.4, zorder=5))
            _via(ax, k["x"] + ox + 2.6, k["y"] + oy - 2.6)
        ko = geo["keepouts"]
        def cen(n):
            x, y, w, h = ko[n]; return (x + ox + w / 2, y + oy + h / 2)
        if "controller" in ko:                           # short LOCAL power traces (bottom cluster only)
            for a, b in (("controller", "charger"), ("charger", "usb_c")):
                axx, ayy = cen(a); bxx, byy = cen(b)
                ax.plot([axx, bxx], [ayy, byy], color=COPPER, lw=1.2, alpha=0.7, zorder=3)
            mcx, mcy = cen("controller")
            ax.plot([mcx, 3.2 + ox], [mcy, mcy], color=COPPER, lw=1.0, alpha=0.5, zorder=3)  # -> row via column
        if "antenna" in ko:                              # all-layer keep-out under the module antenna
            axk, ay, aw, ah = ko["antenna"]
            ax.add_patch(Rectangle((axk + ox, ay + oy), aw, ah, facecolor="none",
                         edgecolor=COPPER, ls=":", lw=1.0, hatch="//", alpha=0.5, zorder=4))
            ax.text(axk + ox + aw / 2, ay + oy + ah / 2, "antenna\nkeep-out", ha="center",
                    va="center", fontsize=3.4, color=COPPER, zorder=5)
        refs = {"controller": "U1 Ebyte E73", "usb_c": "J1 USB-C",
                "charger": "U2 + pwr", "bridge": "J2 FFC-16"}
        for name, (kx, ky, kw, kh) in ko.items():
            if name == "antenna":
                continue
            ax.add_patch(Rectangle((kx + ox, ky + oy), kw, kh, facecolor="#20303f",
                         edgecolor="#7f98c0", lw=1.0, zorder=4))
            ax.text(kx + ox + kw / 2, ky + oy + kh / 2, refs.get(name, name.upper()),
                    ha="center", va="center", fontsize=4.0, color="#cdd6ff", zorder=5)
        ax.text(ox + geo["board_w"] * 0.5, oy - 4,
                "BACK copper: horizontal ROWS · diodes · chips   layers join ONLY through vias (●) — no crossings",
                ha="center", fontsize=5.2, color=COPPER, zorder=7)


# ---------- layer 4: keymats ----------
def keymats(ax, P):
    for key in ("left", "right"):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        pitch = geo["config"]["pitch_x"]; kw0 = geo["config"]["key_w"]; kh0 = geo["config"]["key_h"]
        grid = {(k["row"], k["col"]): k for k in geo["keys"]}
        feats = [f for f in geo.get("features", []) if f["type"] == "key"]

        def strip(a, b):
            ax.plot([a["x"] + ox, b["x"] + ox], [a["y"] + oy, b["y"] + oy],
                    color="#8a8f96", lw=2.5, alpha=0.55, zorder=3, solid_capstyle="round")

        def dist(a, b):
            return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5

        # grid neighbours
        for (r, c), k in grid.items():
            for dr, dc in ((0, 1), (1, 0)):
                n = grid.get((r + dr, c + dc))
                if n:
                    strip(k, n)
        # cluster living-hinges — every feature key ties into the web: to its nearest
        # grid key (bridges the cluster to the main field) AND its nearest other feature.
        gk = list(geo["keys"])
        for f in feats:
            strip(f, min(gk, key=lambda k: dist(f, k)))
            others = [o for o in feats if o is not f]
            if others:
                strip(f, min(others, key=lambda o: dist(f, o)))
        # keycaps (grid = w-aware incl. 2u space; feature keys = single)
        for k in list(geo["keys"]) + feats:
            w = (k.get("w", 1) - 1) * pitch + kw0
            ax.add_patch(FancyBboxPatch((k["x"] + ox - w / 2, k["y"] + oy - kh0 / 2), w, kh0,
                         boxstyle="round,pad=0,rounding_size=1.6", facecolor="#d7dade",
                         edgecolor="#9aa0a7", lw=0.9, zorder=5))
            ax.text(k["x"] + ox, k["y"] + oy, k.get("label", "").replace("NAV_", "").replace("MB_", "M"),
                    ha="center", va="center", fontsize=4.2, color="#20242a", fontweight="bold", zorder=6)


# ---------- layer 5: front shell ----------
def front_shell(ax, P):
    for key in ("left", "right"):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        ax.add_patch(Polygon(_grip_outline(geo, ox, oy), closed=True,
                     facecolor=SHELL_HI, edgecolor=INK, lw=2.5, zorder=2))
    sx, sy, sw_, sh = _spine_rect(P)
    # spine is SOLID (the phone MagSafe-mounts to its OUTSIDE, it is not a window)
    ax.add_patch(FancyBboxPatch((sx, sy), sw_, sh, boxstyle="round,pad=0,rounding_size=6",
                 facecolor=SHELL_HI, edgecolor=INK, lw=2.5, zorder=1))
    # MagSafe N52 ring applied to the OUTSIDE of the front shell (top of the stack);
    # the phone mates onto it. Drawn last / on top.
    ms = P["magsafe"]
    ax.add_patch(Circle((ms["cx"], ms["cy"]), ms["d"] / 2, facecolor="none",
                 edgecolor="#43aa8b", lw=6, alpha=0.9, zorder=7))
    ax.add_patch(Circle((ms["cx"], ms["cy"]), ms["d"] / 2 - 4, facecolor="none",
                 edgecolor="#43aa8b", lw=2, alpha=0.5, zorder=7))
    ax.text(ms["cx"], ms["cy"], "MagSafe ring\n(applied on top\nof front shell)", ha="center",
            va="center", fontsize=7, color="#43aa8b", zorder=8)
    # faint phone outline showing where it mounts
    ph = P["phone"]
    ax.add_patch(FancyBboxPatch((ph["x"], ph["y"]), ph["w"], ph["h"],
                 boxstyle="round,pad=0,rounding_size=6", facecolor="none", edgecolor=INK,
                 ls=(0, (4, 3)), lw=1.0, alpha=0.5, zorder=6))
    ax.text(ph["x"] + 4, ph["y"] + ph["h"] - 4, "phone mounts here", ha="left",
            va="top", fontsize=6.5, color=INK, alpha=0.6, zorder=6)
    # key openings + trackpad window + screw holes
    for key in ("left", "right"):
        geo = P[key]; ox, oy = P[f"{key}_origin"]
        sw = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
        pitch = geo["config"]["pitch_x"]; kw0 = geo["config"]["key_w"]; kh0 = geo["config"]["key_h"]
        for k in sw:
            w = (k.get("w", 1) - 1) * pitch + kw0
            ax.add_patch(FancyBboxPatch((k["x"] + ox - w / 2, k["y"] + oy - kh0 / 2), w, kh0,
                         boxstyle="round,pad=0,rounding_size=1.6", facecolor=BG,
                         edgecolor=INK, lw=0.7, zorder=4))
        for f in geo.get("features", []):
            if f["type"] == "trackpad":
                ax.add_patch(FancyBboxPatch((f["x"] + ox - f["w"] / 2, f["y"] + oy - f["h"] / 2),
                             f["w"], f["h"], boxstyle="round,pad=0,rounding_size=3", facecolor=BG,
                             edgecolor="#7fd1ff", ls=":", lw=1.4, zorder=4))
                ax.text(f["x"] + ox, f["y"] + oy, "trackpad\nwindow (opt)", ha="center",
                        va="center", fontsize=5.5, color="#7fd1ff", zorder=5)
        for h in geo["mount_holes"]:
            ax.add_patch(Circle((h["x"] + ox, h["y"] + oy), h["d"] / 2 + 0.4,
                         facecolor=BG, edgecolor=INK, lw=0.9, zorder=5))


LAYERS = [
    ("layer_1_back_shell", back_shell, "1 · BACK SHELL"),
    ("layer_2_pcb_back", pcb_back, "2 · PCB BACK (module, diodes, chips, rows)"),
    ("layer_3_pcb_front", pcb_front, "3 · PCB FRONT (domes, columns)"),
    ("layer_4_keymats", keymats, "4 · KEYMATS"),
    ("layer_5_front_shell", front_shell, "5 · FRONT SHELL"),
]


def main():
    P = deck.product(deck.Config())
    os.makedirs(OUT, exist_ok=True)
    for name, fn, label in LAYERS:
        fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
        fig.patch.set_facecolor(BG)
        ax = _ax(fig, P)
        fn(ax, P)
        ax.text(0.012, 0.965, f"thumbdeck {deck.VERSION}  ·  {label}", transform=ax.transAxes,
                fontsize=11, color="#f4d35e", fontweight="bold", va="top")
        p = os.path.join(OUT, f"{name}.png")
        fig.savefig(p, dpi=DPI, facecolor=BG)
        plt.close(fig)
        print(p)


if __name__ == "__main__":
    main()
