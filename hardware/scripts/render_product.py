#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""
render_product.py — whole-assembly PRODUCT view: both grips flanking the phone,
MagSafe ring in the centre, front-face features (keys, D-pad, mouse buttons,
trackpad, page keys) drawn to scale. This is the "what it is" diagram, as
opposed to the per-grip PCB fab views. Geometry from deck.product().
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, Rectangle, Circle
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "renders"))


def _draw_grip(ax, geo, ox, oy):
    pitch = geo["config"]["pitch_x"]
    kw0 = geo["config"]["key_w"]
    kh = geo["config"]["key_h"]
    # outline
    pts = [[x + ox, y + oy] for x, y in geo["outline"]]
    ax.add_patch(Polygon(pts, closed=True, facecolor="#0b3d2e",
                 edgecolor="#f4d35e", lw=2.2, zorder=2))
    # grid keys (2u space bar follows k['w'])
    for k in geo["keys"]:
        kw = (k.get("w", 1) - 1) * pitch + kw0
        x, y = k["x"] + ox - kw / 2, k["y"] + oy - kh / 2
        ax.add_patch(FancyBboxPatch((x, y), kw, kh,
                     boxstyle="round,pad=0,rounding_size=1.4",
                     facecolor="#1d1d1d", edgecolor="#f4d35e", lw=1.1, zorder=5))
        ax.text(k["x"] + ox, k["y"] + oy, k["label"], ha="center", va="center",
                fontsize=5.6, color="#f4f1de", fontweight="bold", zorder=6)
    # features
    for f in geo.get("features", []):
        if f["type"] == "trackpad":
            opt = f.get("optional")
            w, h = f["w"], f["h"]
            ax.add_patch(FancyBboxPatch((f["x"] + ox - w / 2, f["y"] + oy - h / 2), w, h,
                         boxstyle="round,pad=0,rounding_size=3", facecolor="none" if opt else "#22333b",
                         edgecolor="#7fd1ff", lw=1.5, ls=":" if opt else "-", zorder=5))
            ax.text(f["x"] + ox, f["y"] + oy, "trackpad\n(opt)" if opt else "trackpad",
                    ha="center", va="center", fontsize=5.5, color="#7fd1ff", zorder=6)
        elif f["type"] == "hall_nub":
            ad = f.get("aperture_d", 10.0)
            ax.add_patch(Circle((f["x"] + ox, f["y"] + oy), ad / 2, facecolor="#22333b",
                         edgecolor="#f4a259", lw=1.4, zorder=5))
            ax.add_patch(Circle((f["x"] + ox, f["y"] + oy), 4.25, facecolor="#1d1d1d",
                         edgecolor="#f4a259", lw=1.6, zorder=6))
            ax.text(f["x"] + ox, f["y"] + oy, "NUB", ha="center", va="center",
                    fontsize=4.2, color="#f4a259", fontweight="bold", zorder=7)
        else:
            ax.add_patch(Circle((f["x"] + ox, f["y"] + oy), f["d"] / 2,
                         facecolor="#1d1d1d", edgecolor="#f4a259", lw=1.2, zorder=5))
            ax.text(f["x"] + ox, f["y"] + oy,
                    f["label"].replace("NAV_", "").replace("MB_", "M"),
                    ha="center", va="center", fontsize=4.4, color="#f4a259",
                    fontweight="bold", zorder=6)
    # internal-component annotations (dashed) — MCU/LiPo/USB-C
    role_labels = {"controller": "Ebyte E73\n(nRF52840)", "lipo": "LiPo", "usb_c": "USB-C",
                   "antenna": "ANT", "bridge": "bridge (FFC-20 ZIF)", "charger": "chg"}
    for name, (x, y, w, h) in geo["keepouts"].items():
        if name not in role_labels:
            continue
        ax.add_patch(Rectangle((x + ox, y + oy), w, h, facecolor="none",
                     edgecolor="#8093f1", ls=(0, (3, 2)), lw=0.9, alpha=0.7, zorder=4))
        ax.text(x + ox + w / 2, y + oy + h / 2, role_labels[name], ha="center",
                va="center", fontsize=4.6, color="#8093f1", zorder=4)


def render(iter_tag="product"):
    c = deck.Config()
    P = deck.product(c)
    fig, ax = plt.subplots(figsize=(13, 6.6))
    fig.patch.set_facecolor("#101418")
    ax.set_facecolor("#101418")

    # phone
    ph = P["phone"]
    ax.add_patch(FancyBboxPatch((ph["x"], ph["y"]), ph["w"], ph["h"],
                 boxstyle="round,pad=0,rounding_size=6", facecolor="#05070a",
                 edgecolor="#e0e0e0", lw=2.0, zorder=3))
    ax.add_patch(FancyBboxPatch((ph["x"] + 2, ph["y"] + 6), ph["w"] - 4, ph["h"] - 12,
                 boxstyle="round,pad=0,rounding_size=4", facecolor="#0c1a24",
                 edgecolor="#22333b", lw=1.0, zorder=3))
    ax.text(ph["x"] + ph["w"] / 2, ph["y"] + ph["h"] - 3, "PHONE (screen)",
            ha="center", va="center", fontsize=7, color="#7fd1ff", zorder=4)
    # v0.18: LiPo 403040 under the LEFT grip's PCB (the sunken phone well leaves
    # no cell-height space in the spine any more)
    sb = P["battery"]
    ax.add_patch(Rectangle((sb["x"], sb["y"]), sb["w"], sb["h"], facecolor="none",
                 edgecolor="#c9ada7", ls="--", lw=1.2, zorder=7))
    ax.text(sb["x"] + sb["w"] / 2, sb["y"] - 2, f"LiPo {sb['cell']}\n(under LEFT PCB)",
            ha="center", va="top", fontsize=6, color="#c9ada7", zorder=7)
    # magsafe ring
    ms = P["magsafe"]
    ax.add_patch(Circle((ms["cx"], ms["cy"]), ms["d"] / 2, facecolor="none",
                 edgecolor="#43aa8b", ls=":", lw=2.2, zorder=4))
    ax.add_patch(Circle((ms["cx"], ms["cy"]), ms["d"] / 2 - 3, facecolor="none",
                 edgecolor="#43aa8b", ls=":", lw=1.2, alpha=0.6, zorder=4))
    ax.text(ms["cx"], ms["cy"], "MagSafe\nN52 ring\n(behind phone)", ha="center",
            va="center", fontsize=6.5, color="#43aa8b", zorder=5)

    _draw_grip(ax, P["left"], *P["left_origin"])
    _draw_grip(ax, P["right"], *P["right_origin"])

    # overall dimension
    total_w = P["right_origin"][0] + P["right"]["board_w"] - P["left_origin"][0]
    ax.set_title("thumbdeck — PRODUCT view  ·  phone MagSafe-mounted centre, two dome-key grips  "
                 f"·  ~{total_w:.0f} mm wide  ·  {deck.VERSION}",
                 fontsize=11.5, color="#f4d35e", pad=12)
    ax.annotate("", xy=(P["right_origin"][0] + P["right"]["board_w"], -8),
                xytext=(P["left_origin"][0], -8),
                arrowprops=dict(arrowstyle="<->", color="#9aa"))
    ax.text(0, -12, f"{total_w:.0f} mm overall", ha="center", color="#9aa", fontsize=8)
    ax.text(0, P["right"]["board_h"] + 6,
            "LEFT grip: QWERT-half + D-pad/OK + mouse L/R      RIGHT grip: YUIOP-half + PgUp/PgDn (pointer = ZMK mouse keys)",
            ha="center", color="#9aa", fontsize=7.5)

    lx = P["left_origin"][0]
    ax.set_xlim(lx - 8, P["right_origin"][0] + P["right"]["board_w"] + 8)
    ax.set_ylim(-18, P["right"]["board_h"] + 12)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{iter_tag}.png")
    fig.savefig(p, dpi=140, facecolor="#101418")
    plt.close(fig)
    print(p)
    return p


if __name__ == "__main__":
    render()
