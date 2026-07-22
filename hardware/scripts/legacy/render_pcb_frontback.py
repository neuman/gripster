#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""
render_pcb_frontback.py — FRONT vs BACK fab view, Rii i8+ style:
  FRONT (F.Cu): the 81 snap-dome pads + the vertical COLUMN traces + the keymat.
  BACK  (B.Cu): everything soldered — 81 diodes, the nRF52840 module, charger,
                USB-C, ESD, passives, connectors — plus the horizontal ROW traces.
Domes are coloured by column, diodes by row, so the single 9x10 matrix reads at a
glance. Back panels are mirrored (viewed from the back). Same switch->row/col
assignment as gen_kicad_pcbnew.py.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "renders"))
NCOLS_HALF = 5
COLW = plt.cm.tab10
ROWW = plt.cm.tab20


def _switches(geo, side):
    sw = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
    col_off = 0 if side == "right" else NCOLS_HALF
    out = []
    for i, k in enumerate(sw):
        out.append({"x": k["x"], "y": k["y"], "label": k.get("label", "?"),
                    "row": i // NCOLS_HALF,
                    "col": col_off + (i % NCOLS_HALF)})
    return out


def _outline(ax, geo, mirror=False):
    W = geo["board_w"]
    pts = [[(W - x) if mirror else x, y] for x, y in geo["outline"]]
    ax.add_patch(Polygon(pts, closed=True, facecolor="#0e2a1e", edgecolor="#ffd60a", lw=2.0, zorder=1))
    for h in geo["mount_holes"]:
        hx = (W - h["x"]) if mirror else h["x"]
        ax.add_patch(Circle((hx, h["y"]), h["d"] / 2, facecolor="#101418", edgecolor="#ffd60a", lw=1.2, zorder=6))


def draw_front(ax, geo, side, title):
    _outline(ax, geo)
    for s in _switches(geo, side):
        ax.add_patch(Circle((s["x"], s["y"]), 3.5, facecolor=COLW(s["col"] % 10),
                     edgecolor="#111", lw=0.6, alpha=0.9, zorder=5))
        ax.text(s["x"], s["y"], s["label"], ha="center", va="center", fontsize=4.4,
                color="#111", fontweight="bold", zorder=6)
    ax.text(geo["board_w"] * 0.5, 3.0, "FRONT · domes + COLUMN traces (colour = column)",
            ha="center", fontsize=7.5, color="#ffd60a")
    _frame(ax, geo, title)


def draw_back(ax, geo, side, title):
    _outline(ax, geo, mirror=True)
    W = geo["board_w"]
    for s in _switches(geo, side):
        x = W - s["x"]
        ax.add_patch(Rectangle((x - 1.1, s["y"] - 0.7), 2.2, 1.4, facecolor=ROWW(s["row"] % 20),
                     edgecolor="#111", lw=0.5, zorder=5))
    # back-side SMD blocks: module / power / connectors (the "chips")
    for name, (kx, ky, kw, kh) in geo["keepouts"].items():
        x = W - kx - kw
        ax.add_patch(Rectangle((x, ky), kw, kh, facecolor="#1b2a4a", edgecolor="#8093f1",
                     ls="--", lw=1.0, alpha=0.85, zorder=4))
        ax.text(x + kw / 2, ky + kh / 2, name.upper(), ha="center", va="center",
                fontsize=4.6, color="#cdd6ff", zorder=5)
    ax.text(W * 0.5, 3.0, "BACK · diodes + module/charger/USB-C + ROW traces (colour = row)",
            ha="center", fontsize=7.5, color="#8093f1")
    _frame(ax, geo, title)


def _frame(ax, geo, title):
    ax.set_xlim(-4, geo["board_w"] + 4); ax.set_ylim(-4, geo["board_h"] + 4)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9.5, color="#eee")
    ax.set_facecolor("#0b0f14"); ax.axis("off")


def main():
    right = deck.build(deck.Config(side="right"))
    left = deck.build(deck.Config(side="left"))
    fig, ax = plt.subplots(2, 2, figsize=(12, 12))
    fig.patch.set_facecolor("#0b0f14")
    draw_front(ax[0][0], right, "right", "RIGHT grip — FRONT (MCU board)")
    draw_back(ax[0][1], right, "right", "RIGHT grip — BACK (mirrored)")
    draw_front(ax[1][0], left, "left", "LEFT grip — FRONT (passive)")
    draw_back(ax[1][1], left, "left", "LEFT grip — BACK (mirrored)")
    fig.suptitle(f"thumbdeck {deck.VERSION} — PCB FRONT / BACK (Rii i8+ style: keys+cols front, "
                 "chips+diodes+rows back)", fontsize=12, color="#ffd60a", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "pcb_frontback.png")
    fig.savefig(p, dpi=130, facecolor="#0b0f14"); print(p)


if __name__ == "__main__":
    main()
