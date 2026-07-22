#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""
render_wiring.py — assembly + wiring views that show WHERE to solder each switch
and diode, and exactly what the bridge cable carries.

Produces:
  renders/wiring_assembly.png : both boards, physical placement, every switch drawn
     with its two solder pads + its diode + ref, and the 10-pin bridge connector
     called out with per-pin net assignment.
  renders/wiring_schematic.png: the logical 5x10 matrix (rows R0-R4 x cols C0-C9),
     switch+diode per node, the RIGHT/LEFT board split, and the bridge connector
     carrying the 5 shared rows + the 5 left-grip columns.

Honesty: this is connectivity + component placement (a ratsnest/assembly view),
NOT final routed copper. Copper traces are drawn in KiCad (the TODO(user) gate);
this tells you every solder point and which net it belongs to.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyBboxPatch
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "renders"))

PAD = "#d98a3d"       # copper pad
ROW_C = "#e07a5f"     # row nets
COL_C = "#5aa9e6"     # column nets
DIODE = "#c9ada7"
SW_EDGE = "#ffd60a"
BRIDGE = "#43aa8b"

# nice!nano pin map for the callout
ROW_PINS = [4, 5, 6, 7, 8]
RCOL_PINS = [9, 10, 14, 15, 16]      # right grip cols C0..C4
LCOL_PINS = [18, 19, 20, 21, 1]      # left grip cols C5..C9 (over bridge)


def _switch(ax, x, y, ref, colnet, rownet, diode_ref):
    """Draw a switch (2 pads) + its diode at (x,y) with net labels."""
    # switch body
    ax.add_patch(FancyBboxPatch((x - 2.6, y - 2.6), 5.2, 5.2,
                 boxstyle="round,pad=0,rounding_size=0.8",
                 facecolor="#1d1d1d", edgecolor=SW_EDGE, lw=1.0, zorder=4))
    # top pad -> column net ; bottom pad -> diode -> row net
    ax.add_patch(Rectangle((x - 1.3, y + 1.9), 2.6, 1.5, facecolor=PAD,
                 edgecolor="#5a3c1a", lw=0.4, zorder=5))          # col pad
    ax.add_patch(Rectangle((x - 1.3, y - 3.4), 2.6, 1.5, facecolor=PAD,
                 edgecolor="#5a3c1a", lw=0.4, zorder=5))          # row/diode pad
    # diode below, cathode bar toward the row bus
    ax.add_patch(Rectangle((x - 1.6, y - 6.4), 3.2, 1.4, facecolor=DIODE,
                 edgecolor="#333", lw=0.4, zorder=4))
    ax.plot([x + 1.0, x + 1.0], [y - 6.4, y - 5.0], color="#333", lw=1.2, zorder=5)  # cathode bar
    ax.text(x, y + 0.1, ref, ha="center", va="center", fontsize=6.4,
            color="#eee", zorder=6)
    ax.text(x + 2.4, y - 5.7, diode_ref, ha="left", va="center", fontsize=5.2,
            color="#9a8", zorder=6)


def _draw_board(ax, geo, title, is_mcu):
    W, H = geo["board_w"], geo["board_h"]
    ax.add_patch(Polygon(geo["outline"], closed=True, facecolor="#0f241a",
                 edgecolor=SW_EDGE, lw=1.8, zorder=1))
    # context keep-outs (faint)
    for name, (x, y, w, h) in geo["keepouts"].items():
        c = BRIDGE if name == "bridge" else "#3a4a55"
        ax.add_patch(Rectangle((x, y), w, h, facecolor="none", edgecolor=c,
                     ls="--", lw=1.0, zorder=2))

    # column buses (vertical, constant x per column) + labels
    cols = {}
    for k in geo["keys"]:
        cols.setdefault(k["col"], []).append(k)
    for c, ks in cols.items():
        x = ks[0]["x"]
        ys = [kk["y"] for kk in ks]
        ax.plot([x, x], [min(ys) + 3.0, max(ys) + 3.0], color=COL_C, lw=1.0,
                alpha=0.6, zorder=3)
        # logical column number: right grip 0..4, left grip 5..9
        cn = c if is_mcu else c + 5
        ax.text(x, max(ys) + 4.5, f"C{cn}", ha="center", fontsize=5.5,
                color=COL_C, fontweight="bold", zorder=6)

    # row buses (through diode cathodes, follows the fan) + labels
    rows = {}
    for k in geo["keys"]:
        rows.setdefault(k["row"], []).append(k)
    for r, ks in sorted(rows.items()):
        ks = sorted(ks, key=lambda kk: kk["x"])
        xs = [kk["x"] for kk in ks]
        ys = [kk["y"] - 6.4 for kk in ks]
        ax.plot(xs, ys, color=ROW_C, lw=1.0, alpha=0.7, zorder=3)
        lx = xs[0] if is_mcu else xs[-1]
        ax.text(lx + (-4 if is_mcu else 4), ys[0 if is_mcu else -1],
                f"R{r}", ha="center", fontsize=5.5, color=ROW_C,
                fontweight="bold", zorder=6)

    # switches + diodes
    for idx, k in enumerate(geo["keys"], start=1):
        cn = k["col"] if is_mcu else k["col"] + 5
        _switch(ax, k["x"], k["y"], f"SW{idx}\n{k['label']}", cn, k["row"], f"D{idx}")

    # bridge connector: 10 labelled pins along the connector
    bx, by, bw, bh = geo["keepouts"]["bridge"]
    labels = [f"R{i}" for i in range(5)] + [f"C{i}" for i in range(5, 10)]
    for i, lab in enumerate(labels):
        px = bx + (i + 0.5) * (bw / 10)
        ax.add_patch(Rectangle((px - 0.35, by + 1), 0.7, bh - 2, facecolor=BRIDGE,
                     edgecolor="#1a3a2c", lw=0.3, zorder=5))
        ax.text(px, by - 1.4, lab, ha="center", va="top", fontsize=3.7,
                color=BRIDGE, rotation=90, zorder=6)
    ax.text(bx + bw / 2, by + bh + 1.5, "BRIDGE (10-pin)", ha="center",
            fontsize=5.5, color=BRIDGE, fontweight="bold", zorder=6)

    if is_mcu:
        cx, cy, cw, ch = geo["keepouts"]["controller"]
        ax.text(cx + cw / 2, cy + ch / 2, "nice!nano v2\n(controller)",
                ha="center", va="center", fontsize=6, color="#8093f1",
                fontweight="bold", zorder=6)

    ax.set_xlim(-8, W + 8)
    ax.set_ylim(-8, H + 6)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, color="#eee")
    ax.set_facecolor("#0b0f14")
    ax.axis("off")


def _pinout_lines():
    lines = ["BRIDGE CABLE — 10 conductors (right grip <-> left grip):"]
    for i in range(5):
        lines.append(f"  pin {i+1}:  R{i}  (row, shared)     -> nice!nano pro_micro {ROW_PINS[i]}")
    for i in range(5):
        lines.append(f"  pin {i+6}: C{i+5}  (left-grip col)   -> nice!nano pro_micro {LCOL_PINS[i]}")
    lines.append("Right-grip cols C0-C4 -> pro_micro " + ",".join(map(str, RCOL_PINS))
                 + "  (local, NOT on the bridge)")
    return "\n".join(lines)


def assembly():
    """One legible image per board so every solder pad + ref is readable."""
    paths = []
    for side, is_mcu, name in (("right", True, "RIGHT grip (MCU)"),
                               ("left", False, "LEFT grip (passive)")):
        geo = deck.build(deck.Config(side=side))
        fig, ax = plt.subplots(figsize=(8.5, 12))
        fig.patch.set_facecolor("#0b0f14")
        role = ("switches + diodes + nice!nano + LiPo + USB-C + bridge" if is_mcu
                else "25 switches + 25 diodes + bridge (no chip, no battery)")
        _draw_board(ax, geo, f"{name} — {role}", is_mcu)
        fig.suptitle(f"thumbdeck v0.3 — ASSEMBLY: {name}\n"
                     "copper pad = solder point · blue = column net · orange = row net · green = bridge",
                     fontsize=11, color=SW_EDGE, y=0.98)
        fig.text(0.5, 0.015, _pinout_lines(), ha="center", va="bottom", fontsize=7.2,
                 color="#bcd", family="monospace",
                 bbox=dict(boxstyle="round", facecolor="#101820", edgecolor="#2a3a44"))
        fig.tight_layout(rect=[0, 0.12, 1, 0.95])
        p = os.path.join(OUT, f"wiring_assembly_{side}.png")
        fig.savefig(p, dpi=160, facecolor="#0b0f14")
        plt.close(fig)
        paths.append(p)
    return paths


def schematic():
    fig, ax = plt.subplots(figsize=(15, 7.5))
    fig.patch.set_facecolor("#0b0f14")
    dx, dy = 3.2, 3.0
    x0, y0 = 2, 2
    gap = 1.6  # extra gap between right (C0-4) and left (C5-9) blocks

    def colx(c):
        return x0 + c * dx + (gap if c >= 5 else 0)

    # row buses R0..R4
    for r in range(5):
        yy = y0 + (4 - r) * dy
        ax.plot([colx(0) - 1.2, colx(9) + 1.2], [yy, yy], color=ROW_C, lw=1.4, zorder=1)
        ax.text(colx(0) - 2.2, yy, f"R{r}", ha="right", va="center",
                color=ROW_C, fontsize=9, fontweight="bold")
        ax.text(colx(9) + 2.2, yy, f"R{r}", ha="left", va="center",
                color=ROW_C, fontsize=8)
    # column buses C0..C9 + nodes
    R = deck.RIGHT_LEGENDS
    L = deck.LEFT_LEGENDS
    for c in range(10):
        xx = colx(c)
        ax.plot([xx, xx], [y0 - 1.2, y0 + 4 * dy + 1.2], color=COL_C, lw=1.4, zorder=1)
        ax.text(xx, y0 + 4 * dy + 2.0, f"C{c}", ha="center", color=COL_C,
                fontsize=9, fontweight="bold")
        for r in range(5):
            yy = y0 + (4 - r) * dy
            # node: switch (box) + diode (line to row bus)
            ax.add_patch(Rectangle((xx - 0.55, yy + 0.25), 1.1, 0.9,
                         facecolor="#1d1d1d", edgecolor=SW_EDGE, lw=0.9, zorder=3))
            ax.plot([xx, xx], [yy + 0.25, yy], color=DIODE, lw=1.6, zorder=2)  # diode
            ax.plot([xx - 0.5, xx + 0.5], [yy + 0.05, yy + 0.05], color="#333", lw=1.2, zorder=3)
            lab = (R[r][c] if c < 5 else L[r][c - 5])
            ax.text(xx, yy + 0.7, lab, ha="center", va="center", fontsize=5.2,
                    color="#eee", zorder=4)

    # right / left board split
    split = (colx(4) + colx(5)) / 2
    ax.axvline(split, color="#556", ls=":", lw=1.2)
    ax.text((colx(0) + colx(4)) / 2, y0 - 3.4, "RIGHT grip board  (C0-C4, local)",
            ha="center", color="#8093f1", fontsize=9, fontweight="bold")
    ax.text((colx(5) + colx(9)) / 2, y0 - 3.4, "LEFT grip board  (C5-C9, over bridge)",
            ha="center", color="#89c2d9", fontsize=9, fontweight="bold")

    # bridge connector straddling the split: carries R0-4 + C5-9
    ax.add_patch(FancyBboxPatch((split - 1.4, y0 - 6.6), 2.8, 2.0,
                 boxstyle="round,pad=0.1", facecolor="#0f241a", edgecolor=BRIDGE, lw=1.6))
    ax.text(split, y0 - 5.6, "BRIDGE\n10-pin", ha="center", va="center",
            color=BRIDGE, fontsize=7, fontweight="bold")
    for r in range(5):
        yy = y0 + (4 - r) * dy
        ax.plot([split, split], [y0 - 4.6, yy], color=ROW_C, lw=0.8, alpha=0.5, zorder=0)
    for c in range(5, 10):
        ax.plot([colx(c), colx(c)], [y0 - 1.2, y0 - 4.6], color=COL_C, lw=0.8, alpha=0.5, zorder=0)
        ax.plot([colx(c), split], [y0 - 4.6, y0 - 4.6], color=COL_C, lw=0.8, alpha=0.5, zorder=0)

    # controller on the right side
    ax.add_patch(FancyBboxPatch((colx(0) - 1.4, y0 + 4 * dy + 3.2), colx(4) - colx(0) + 2.8, 2.2,
                 boxstyle="round,pad=0.1", facecolor="#141826", edgecolor="#8093f1", lw=1.4))
    ax.text((colx(0) + colx(4)) / 2, y0 + 4 * dy + 4.3, "nice!nano v2 — scans all 50 keys",
            ha="center", va="center", color="#8093f1", fontsize=8.5, fontweight="bold")

    ax.text(split, y0 + 4 * dy + 6.2,
            "One controller, one 5x10 matrix. Cols 0-4 wired on the right board; "
            "cols 5-9 + all 5 rows reach the left board through the bridge.",
            ha="center", fontsize=8, color="#9aa")

    ax.set_xlim(colx(0) - 6, colx(9) + 6)
    ax.set_ylim(y0 - 8, y0 + 4 * dy + 7.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("#0b0f14")
    fig.suptitle("thumbdeck v0.3 — MATRIX SCHEMATIC (logical)  ·  each node = switch + diode (col2row)",
                 fontsize=12, color=SW_EDGE, y=0.97)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(OUT, "wiring_schematic.png")
    fig.savefig(p, dpi=150, facecolor="#0b0f14")
    plt.close(fig)
    return p


if __name__ == "__main__":
    for p in assembly():
        print(p)
    print(schematic())
