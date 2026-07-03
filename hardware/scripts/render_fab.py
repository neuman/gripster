#!/usr/bin/env python3
"""
render_fab.py — fabrication-view render straight from the converged geometry,
mirroring exactly what gen_kicad.py writes to the .kicad_pcb (Edge.Cuts outline,
mount-hole cutouts, keep-out rects, switch/diode placement crosses + refs).
Lets the loop visually confirm the production board matches the design intent.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "renders"))


def draw(ax, geo, title):
    W, H = geo["board_w"], geo["board_h"]
    ax.add_patch(Polygon(geo["outline"], closed=True, facecolor="#132a13",
                 edgecolor="#ffd60a", lw=2.0))
    for name, (x, y, w, h) in geo["keepouts"].items():
        ax.add_patch(Rectangle((x, y), w, h, facecolor="none",
                     edgecolor="#89c2d9", ls="--", lw=1.1))
        ax.text(x + w / 2, y + h / 2, name.upper().replace("_", "-"),
                ha="center", va="center", fontsize=6, color="#89c2d9")
    for hole in geo["mount_holes"]:
        ax.add_patch(Circle((hole["x"], hole["y"]), hole["d"] / 2,
                     facecolor="#101418", edgecolor="#ffd60a", lw=1.2))
    for idx, k in enumerate(geo["keys"], start=1):
        ax.plot([k["x"] - 1.4, k["x"] + 1.4], [k["y"], k["y"]], color="#e5e5e5", lw=0.8)
        ax.plot([k["x"], k["x"]], [k["y"] - 1.4, k["y"] + 1.4], color="#e5e5e5", lw=0.8)
        ax.text(k["x"], k["y"] + 2.2, f"SW{idx}", ha="center", fontsize=5, color="#adb5bd")
        ax.text(k["x"], k["y"] - 3.0, k["label"], ha="center", fontsize=5.5,
                color="#ffd60a", fontweight="bold")
    side = "R" if geo["side"] == "right" else "L"
    ax.text(3.4, H * 0.5, f"thumbdeck-{side} {deck.VERSION}", rotation=90,
            ha="center", va="center", fontsize=8, color="#ffd60a", fontweight="bold")
    ax.set_xlim(-4, W + 4); ax.set_ylim(-4, H + 4); ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, color="#eee")
    ax.set_facecolor("#0b0f14")
    ax.tick_params(colors="#555", labelsize=6)
    for s in ax.spines.values():
        s.set_color("#333")


def main():
    right = deck.build(deck.Config(side="right"))
    left = deck.build(deck.Config(side="left"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 6.4))
    fig.patch.set_facecolor("#0b0f14")
    draw(axes[0], left, f"LEFT fab view — Edge.Cuts + placement ({left['board_w']:.0f}x{left['board_h']:.0f}mm)")
    draw(axes[1], right, f"RIGHT fab view — Edge.Cuts + placement ({right['board_w']:.0f}x{right['board_h']:.0f}mm)")
    fig.suptitle(f"thumbdeck {deck.VERSION} — FABRICATION VIEW (matches .kicad_pcb)  "
                 "· switch footprint provisional until datasheet-verified",
                 fontsize=11, color="#ffd60a", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "fab_view.png")
    fig.savefig(p, dpi=140, facecolor="#0b0f14")
    print(p)


if __name__ == "__main__":
    main()
