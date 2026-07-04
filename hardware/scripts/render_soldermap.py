#!/usr/bin/env python3
"""
render_soldermap.py — true 1:1 printable solder/placement map (PDF, A4 portrait).

One page per board. Print at **100% / Actual size** (NOT "fit to page") and the
drawing is life-size: lay physical parts on it, or use it as a drilling/placement
guide. A 50 mm scale bar on each page lets you confirm the print wasn't rescaled.

Positions (switch centres, diodes, mount holes, keep-outs, bridge, controller)
are the converged layout — real. Pad *shapes* are nominal/provisional until the
switch footprint is datasheet-verified (hardware/footprints/README.md); they're
drawn so you can check fit and orientation, not as final copper.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.backends.backend_pdf import PdfPages
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "renders"))
PAGE_W, PAGE_H = 210.0, 297.0     # A4 portrait, mm
MM = 1.0 / 25.4                   # mm -> inch

INK = "#111111"
PAD = "#333333"
GRID = "#999999"
KO = "#666666"


def _axes_1to1(fig, x_mm, y_mm, w_mm, h_mm):
    """Add an axes whose data units are exactly millimetres on the printed page."""
    ax = fig.add_axes([x_mm / PAGE_W, y_mm / PAGE_H, w_mm / PAGE_W, h_mm / PAGE_H])
    ax.set_xlim(0, w_mm)
    ax.set_ylim(0, h_mm)
    ax.axis("off")
    return ax


def _switch(ax, x, y, label):
    # 5x5 body + two 2-terminal pads (top=column, bottom=row via diode)
    ax.add_patch(Rectangle((x - 2.5, y - 2.5), 5.0, 5.0, facecolor="none",
                 edgecolor=INK, lw=0.6))
    ax.add_patch(Rectangle((x - 1.1, y + 1.4), 2.2, 1.3, facecolor=PAD, edgecolor="none"))
    ax.add_patch(Rectangle((x - 1.1, y - 2.7), 2.2, 1.3, facecolor=PAD, edgecolor="none"))
    ax.text(x, y - 0.2, label, ha="center", va="center", fontsize=4.4, color=INK)
    # diode below (SOD-123 nominal), cathode bar toward the row
    ax.add_patch(Rectangle((x - 1.35, y - 5.9), 2.7, 1.5, facecolor="none",
                 edgecolor=INK, lw=0.5))
    ax.add_patch(Rectangle((x - 1.35, y - 5.9), 0.6, 1.5, facecolor=PAD, edgecolor="none"))
    ax.add_patch(Rectangle((x + 0.75, y - 5.9), 0.6, 1.5, facecolor=PAD, edgecolor="none"))


def _draw(ax, geo, ox, oy, is_mcu):
    def P(pt):
        return (pt[0] + ox, pt[1] + oy)
    ax.add_patch(Polygon([P(p) for p in geo["outline"]], closed=True,
                 facecolor="none", edgecolor=INK, lw=1.2))
    # keep-outs
    names = {"controller": "nice!nano v2", "lipo": "LiPo", "usb_c": "USB-C"}
    for name, (x, y, w, h) in geo["keepouts"].items():
        ax.add_patch(Rectangle((x + ox, y + oy), w, h, facecolor="none",
                     edgecolor=KO, ls="--", lw=0.7))
        if name == "bridge":
            ax.text(x + ox + w / 2, y + oy + h + 1.2, "BRIDGE 10-pin",
                    ha="center", va="bottom", fontsize=5, color=INK)
            for i in range(10):
                px = x + ox + (i + 0.5) * (w / 10)
                ax.plot([px], [y + oy + h / 2], marker="s", ms=2.0, color=PAD)
            ax.text(x + ox + w / 2, y + oy - 1.2, "pins 1-5: R0-R4  |  6-10: C5-C9",
                    ha="center", va="top", fontsize=3.6, color=INK)
        else:
            ax.text(x + ox + w / 2, y + oy + h / 2, names.get(name, name),
                    ha="center", va="center", fontsize=6, color=KO)
    # mount holes (drill) + dia
    for hole in geo["mount_holes"]:
        hx, hy = hole["x"] + ox, hole["y"] + oy
        ax.add_patch(Circle((hx, hy), hole["d"] / 2, facecolor="none", edgecolor=INK, lw=0.8))
        ax.plot([hx - 2, hx + 2], [hy, hy], color=INK, lw=0.4)
        ax.plot([hx, hx], [hy - 2, hy + 2], color=INK, lw=0.4)
        ax.text(hx + 2.4, hy, f"ø{hole['d']:.1f}", fontsize=4.5, va="center", color=INK)
    # switches + diodes + refs (legend on the body, SWn small above)
    for idx, k in enumerate(geo["keys"], start=1):
        _switch(ax, k["x"] + ox, k["y"] + oy, k["label"])
        ax.text(k["x"] + ox, k["y"] + oy + 3.3, f"SW{idx}",
                ha="center", fontsize=2.9, color="#888")


def _scale_bar(fig):
    ax = _axes_1to1(fig, 20, 10, 80, 16)
    ax.plot([0, 50], [8, 8], color=INK, lw=1.2)
    for t in range(0, 51, 10):
        ax.plot([t, t], [6.5, 9.5], color=INK, lw=1.0)
        ax.text(t, 4.5, str(t), ha="center", fontsize=5, color=INK)
    ax.text(55, 8, "mm", va="center", fontsize=6, color=INK)
    ax.text(0, 12.5, "SCALE CHECK: this bar must measure 50 mm. If not, reprint at "
            "100% / Actual size (turn OFF 'fit to page').", fontsize=6, color="#a00")


def page(pdf, side, is_mcu):
    geo = deck.build(deck.Config(side=side))
    W, H = geo["board_w"], geo["board_h"]
    fig = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
    fig.patch.set_facecolor("white")
    # board area centred horizontally, above the scale bar
    draw_w, draw_h = W + 10, H + 10
    ax = _axes_1to1(fig, (PAGE_W - draw_w) / 2, (PAGE_H - draw_h) / 2 - 6, draw_w, draw_h)
    _draw(ax, geo, 5, 5, is_mcu)
    name = "RIGHT grip (MCU)" if is_mcu else "LEFT grip (passive)"
    fig.text(0.5, 0.95, f"thumbdeck {deck.VERSION} — 1:1 SOLDER MAP — {name}",
             ha="center", fontsize=12, color=INK, fontweight="bold")
    fig.text(0.5, 0.928, f"{W:.1f} × {H:.1f} mm  ·  print at 100% / Actual size  ·  "
             "pads PROVISIONAL until switch footprint is datasheet-verified",
             ha="center", fontsize=8, color="#555")
    _scale_bar(fig)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "thumbdeck_soldermap.pdf")
    with PdfPages(path) as pdf:
        page(pdf, "right", True)
        page(pdf, "left", False)
    # also a PNG preview of the right page for quick on-screen viewing
    geo = deck.build(deck.Config(side="right"))
    W, H = geo["board_w"], geo["board_h"]
    fig = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
    fig.patch.set_facecolor("white")
    draw_w, draw_h = W + 10, H + 10
    ax = _axes_1to1(fig, (PAGE_W - draw_w) / 2, (PAGE_H - draw_h) / 2 - 6, draw_w, draw_h)
    _draw(ax, geo, 5, 5, True)
    fig.text(0.5, 0.95, f"thumbdeck {deck.VERSION} — 1:1 SOLDER MAP — RIGHT grip (MCU)",
             ha="center", fontsize=12, color=INK, fontweight="bold")
    fig.text(0.5, 0.928, f"{W:.1f} × {H:.1f} mm  ·  print at 100% / Actual size",
             ha="center", fontsize=8, color="#555")
    _scale_bar(fig)
    fig.savefig(os.path.join(OUT, "soldermap_right_preview.png"), dpi=150, facecolor="white")
    plt.close(fig)
    print(path)
    print(os.path.join(OUT, "soldermap_right_preview.png"))


if __name__ == "__main__":
    main()
