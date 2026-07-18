#!/usr/bin/env python3
"""
verify_geometry.py — v0.17 deck geometry sanity check.

Builds both grips via deck.build(deck.Config(side=s)) and asserts there are no
impossible overlaps in the parametric model:

  (1) board dims are 79.5 x 97.0 mm on BOTH sides;
  (2) no two dome/key centres (geo["keys"] + feature keys of type 'key') are
      closer than 7.8 mm — the Snaptron 7mm contact courtyard is r3.9, so a
      centre distance < 7.8 mm means the two courtyards overlap. Reports the
      minimum spacing found. (Grid neighbours are 9.0mm in Y / 10.0mm in X, so
      this only ever trips on a TRUE overlap, e.g. a feature key dropped on a
      grid key.)
  (3) every mount hole (geo["mount_holes"]) is >= 7.9 mm c-c from every key/feature
      centre (M2 boss clearance). Reports the minimum.
  (4) the "chin" = min(key y) - key_h/2 is ~9 mm (accepted band 6..12).

Prints a single-line JSON verdict:
    {"check":"geometry","pass":<bool>,"detail":"dims=.. min_key_spacing=.. min_hole_key=.. chin=.."}
"""
from __future__ import annotations
import json
import math
import os
import sys

# deck.py lives beside this script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deck  # noqa: E402

# --- thresholds -------------------------------------------------------------
DIM_W, DIM_H = 75.0, 97.0      # expected board dims (mm; v0.19 GBC-boxy, crown excluded)
DIM_TOL = 0.1                  # rounding tolerance on dims
MIN_KEY_SPACING = 7.8          # < this => Snaptron r3.9 courtyards overlap
MIN_HOLE_KEY = 7.9             # hole centre -> key centre: M3 boss r4.0 + dome courtyard r3.9 (v0.19)
CHIN_LO, CHIN_HI = 6.0, 12.0   # accepted chin band (target ~9 mm)


def _key_points(geo: dict):
    """All dome/switch centres: grid keys + feature switches of type 'key'."""
    pts = [(k["x"], k["y"]) for k in geo["keys"]]
    pts += [(f["x"], f["y"]) for f in geo.get("features", [])
            if f.get("type") == "key"]
    return pts


def _min_pair_dist(pts):
    best = math.inf
    best_pair = None
    n = len(pts)
    for i in range(n):
        xi, yi = pts[i]
        for j in range(i + 1, n):
            xj, yj = pts[j]
            d = math.hypot(xi - xj, yi - yj)
            if d < best:
                best = d
                best_pair = (i, j)
    return best, best_pair


def _min_hole_key(geo: dict, pts):
    best = math.inf
    for h in geo["mount_holes"]:
        for (x, y) in pts:
            d = math.hypot(h["x"] - x, h["y"] - y)
            if d < best:
                best = d
    return best


def check_side(side: str):
    c = deck.Config(side=side)
    geo = deck.build(c)
    key_h = geo["config"]["key_h"]

    pts = _key_points(geo)
    min_spacing, pair = _min_pair_dist(pts)
    min_hk = _min_hole_key(geo, pts)
    min_key_y = min(k["y"] for k in geo["keys"])
    chin = min_key_y - key_h / 2.0

    res = {
        "side": side,
        "board_w": geo["board_w"],
        "board_h": geo["board_h"],
        "dims_ok": (abs(geo["board_w"] - DIM_W) <= DIM_TOL
                    and abs(geo["board_h"] - DIM_H) <= DIM_TOL),
        "n_key_pts": len(pts),
        "min_key_spacing": round(min_spacing, 3),
        "min_key_pair": pair,
        "min_hole_key": round(min_hk, 3),
        "chin": round(chin, 3),
        "spacing_ok": min_spacing >= MIN_KEY_SPACING,
        "hole_ok": min_hk >= MIN_HOLE_KEY,
        "chin_ok": CHIN_LO <= chin <= CHIN_HI,
    }
    return res


def main():
    results = [check_side(s) for s in ("right", "left")]

    dims_ok = all(r["dims_ok"] for r in results)
    min_spacing = min(r["min_key_spacing"] for r in results)
    min_hole_key = min(r["min_hole_key"] for r in results)
    # chin identical on both sides (mirror preserves y); report the max deviation-safe value
    chin = results[0]["chin"]
    chin_ok = all(r["chin_ok"] for r in results)
    spacing_ok = all(r["spacing_ok"] for r in results)
    hole_ok = all(r["hole_ok"] for r in results)

    overall = bool(dims_ok and spacing_ok and hole_ok and chin_ok)

    # human-readable per-side breakdown to stderr for debugging
    for r in results:
        print(f"[{r['side']:>5}] board={r['board_w']}x{r['board_h']} "
              f"dims_ok={r['dims_ok']} keypts={r['n_key_pts']} "
              f"min_key_spacing={r['min_key_spacing']} (pair {r['min_key_pair']}) "
              f"min_hole_key={r['min_hole_key']} chin={r['chin']}",
              file=sys.stderr)

    dims_str = (f"{results[0]['board_w']}x{results[0]['board_h']}"
                if dims_ok else
                "|".join(f"{r['side']}:{r['board_w']}x{r['board_h']}" for r in results))
    detail = (f"dims={dims_str} "
              f"min_key_spacing={round(min_spacing, 3)} "
              f"min_hole_key={round(min_hole_key, 3)} "
              f"chin={round(chin, 3)}")

    verdict = {"check": "geometry", "pass": overall, "detail": detail}
    print(json.dumps(verdict))
    return verdict


if __name__ == "__main__":
    v = main()
    sys.exit(0 if v["pass"] else 1)
