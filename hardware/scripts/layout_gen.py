#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""
layout_gen.py — render one iteration of the split thumb keyboard layout.

Fallback render path (pure Python: matplotlib PNG). The spec's "primary" path is
KiCad `pcbnew` headless; this environment has no KiCad, so we render the shared
geometry from deck.py to PNG. PNG is chosen over SVG because it can be viewed
directly by the iteration loop for the visual acceptance checklist.

Usage:
  python3 layout_gen.py --iter 3 --out ../../renders
  python3 layout_gen.py --iter 3 --params params.json   # override defaults
"""
from __future__ import annotations
import argparse, json, os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, Rectangle, Circle, Wedge
from dataclasses import fields

import deck


def _cfg_from(params: dict | None) -> deck.Config:
    c = deck.Config()
    if params:
        valid = {f.name for f in fields(deck.Config)}
        for k, v in params.items():
            if k in valid:
                setattr(c, k, v)
    return c


def _draw_half(ax, geo, title):
    W, H = geo["board_w"], geo["board_h"]
    # board outline
    poly = Polygon(geo["outline"], closed=True, facecolor="#0b3d2e",
                   edgecolor="#f4d35e", lw=2.2, zorder=1)
    ax.add_patch(poly)
    # thumb arc guide (rmin..rmax from anchor)
    ax_, ay = geo["anchor"]
    rmin, rmax = geo["arc"]["rmin"], geo["arc"]["rmax"]
    for r in (rmin, rmax):
        ax.add_patch(Wedge((ax_, ay), r, 0, 180, width=0.4,
                           facecolor="none", edgecolor="#7fd1ff", ls=":", lw=0.8, zorder=2))
    ax.plot([ax_], [ay], marker="x", color="#7fd1ff", ms=7, zorder=5)
    # keep-outs
    ko_colors = {"usb_c": "#e07a5f", "controller": "#8093f1", "lipo": "#c9ada7",
                 "bridge": "#43aa8b", "antenna": "#f28482"}
    for name, (x, y, w, h) in geo["keepouts"].items():
        ax.add_patch(Rectangle((x, y), w, h, facecolor=ko_colors.get(name, "#888"),
                     alpha=0.55, edgecolor="white", ls="--", lw=1.0, zorder=3))
        ax.text(x + w / 2, y + h / 2, name.replace("_", "-"),
                ha="center", va="center", fontsize=6.5, color="white",
                fontweight="bold", zorder=4)
    # mount holes
    for hole in geo["mount_holes"]:
        ax.add_patch(Circle((hole["x"], hole["y"]), hole["d"] / 2 + 0.6,
                     facecolor="#222", edgecolor="#f4d35e", lw=1.2, zorder=4))
    # keys (keycap width follows k['w'] so the 2u space bar reads correctly)
    c = geo["config"]
    kh = c["key_h"]
    for k in geo["keys"]:
        kw = (k.get("w", 1) - 1) * c["pitch_x"] + c["key_w"]
        x, y = k["x"] - kw / 2, k["y"] - kh / 2
        ax.add_patch(FancyBboxPatch((x, y), kw, kh,
                     boxstyle="round,pad=0.0,rounding_size=1.4",
                     facecolor="#1d1d1d", edgecolor="#f4d35e", lw=1.3, zorder=5))
        ax.text(k["x"], k["y"], k["label"], ha="center", va="center",
                fontsize=7.0, color="#f4f1de", fontweight="bold", zorder=6)
    # non-grid features: trackpad (circle) + cluster switches (D-pad/mouse/pages)
    for f in geo.get("features", []):
        if f["type"] == "trackpad":
            opt = f.get("optional")
            w, h = f["w"], f["h"]
            ax.add_patch(FancyBboxPatch((f["x"] - w / 2, f["y"] - h / 2), w, h,
                         boxstyle="round,pad=0,rounding_size=3", facecolor="none" if opt else "#22333b",
                         edgecolor="#7fd1ff", lw=1.4, ls=":" if opt else "-", zorder=5))
            ax.text(f["x"], f["y"], "trackpad\n(opt)" if opt else "trackpad",
                    ha="center", va="center", fontsize=5.5, color="#7fd1ff", zorder=6)
        elif f["type"] == "dpad":
            # v0.25: the integrated nav pad. Drawn UNDER its five domes because that
            # is the truth — the board still has five discrete switches; the pad is
            # the keymat/lid cap that covers them.
            ax.add_patch(Circle((f["x"], f["y"]), f["d"] / 2, facecolor="#2b2118",
                         edgecolor="#f4a259", lw=1.4, ls="--", zorder=4))
            ax.text(f["x"], f["y"] + f["d"] / 2 - 1.6, "D-pad", ha="center", va="center",
                    fontsize=4.2, color="#f4a259", alpha=0.8, zorder=6)
        elif f["type"] == "hall_nub":
            ad = f.get("aperture_d", 10.0)
            ax.add_patch(Circle((f["x"], f["y"]), ad / 2, facecolor="#22333b",
                         edgecolor="#f4a259", lw=1.4, zorder=5))
            ax.add_patch(Circle((f["x"], f["y"]), 4.25, facecolor="#1d1d1d",
                         edgecolor="#f4a259", lw=1.6, zorder=6))
            ax.text(f["x"], f["y"], "NUB", ha="center", va="center", fontsize=4.2,
                    color="#f4a259", fontweight="bold", zorder=7)
        else:
            ax.add_patch(Circle((f["x"], f["y"]), f["d"] / 2,
                         facecolor="#1d1d1d", edgecolor="#f4a259", lw=1.2, zorder=5))
            ax.text(f["x"], f["y"], f["label"].replace("NAV_", "").replace("MB_", "M"),
                    ha="center", va="center", fontsize=4.6, color="#f4a259",
                    fontweight="bold", zorder=6)
    # silkscreen: half + version, printed along the inner/split (mating) edge
    half = "R" if geo["side"] == "right" else "L"
    if geo["side"] == "right":
        sx, rot, edge_x = 2.6, 90, 0.0
    else:
        sx, rot, edge_x = W - 2.6, -90, W
    ax.text(sx, H * 0.5, f"thumbdeck-{half}  {deck.VERSION}", rotation=rot,
            ha="center", va="center", fontsize=8.5, color="#f4d35e",
            fontweight="bold", zorder=7)
    # mark the flat inner mating reference edge (Backbone clamp interface)
    ax.plot([edge_x, edge_x], [H * 0.30, H * 0.70], color="#7fd1ff", lw=3.5,
            solid_capstyle="butt", alpha=0.7, zorder=2)
    ax.text(edge_x + (5 if geo["side"] == "right" else -5), H * 0.72,
            "flat mating edge", rotation=rot, ha="center", va="center",
            fontsize=6, color="#7fd1ff", zorder=7)
    ax.set_xlim(-4, W + 4)
    ax.set_ylim(-4, H + 4)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, color="#eee")
    ax.set_facecolor("#101418")
    ax.tick_params(colors="#555", labelsize=6)
    for s in ax.spines.values():
        s.set_color("#333")


def render(iter_n: int, out_dir: str, params: dict | None = None) -> str:
    c = _cfg_from(params)
    right = deck.build(deck.Config(**{**c.__dict__, "side": "right"}))
    left = deck.build(deck.Config(**{**c.__dict__, "side": "left"}))

    fig, axes = plt.subplots(1, 2, figsize=(11, 6.2))
    fig.patch.set_facecolor("#101418")
    _draw_half(axes[0], left, f"LEFT  (passive matrix)  {left['board_w']:.0f}x{left['board_h']:.0f}mm")
    _draw_half(axes[1], right, f"RIGHT (MCU: nRF52840+LiPo+USB-C)  {right['board_w']:.0f}x{right['board_h']:.0f}mm")
    fig.suptitle(f"thumbdeck — layout iter {iter_n:02d}   "
                 f"(36-key grid +clusters/half · Snaptron 7mm dome · phone MagSafe · single nRF52840)",
                 fontsize=11.5, color="#f4d35e", y=0.98)
    fig.text(0.5, 0.02, "one controller in the RIGHT grip · LEFT grip passive, wired over the "
             "bridge connector · inner/split edge faces phone · thumb arc dotted",
             ha="center", fontsize=7.5, color="#9aa")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f"iter_{iter_n:02d}.png")
    fig.savefig(png, dpi=130, facecolor="#101418")
    plt.close(fig)

    # dump geometry alongside for the grader
    with open(os.path.join(out_dir, f"iter_{iter_n:02d}.geo.json"), "w") as f:
        json.dump({"left": left, "right": right}, f, indent=2)
    return png


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "renders"))
    ap.add_argument("--params", default=None)
    a = ap.parse_args()
    params = json.load(open(a.params)) if a.params else None
    p = render(a.iter, a.out, params)
    print(p)
