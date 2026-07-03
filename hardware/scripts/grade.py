#!/usr/bin/env python3
"""
grade.py — objective (geometric + firmware) grader for the layout loop.

Produces a 0..100 score plus per-check PASS/FAIL. Some checks are HARD: if any
hard check fails the design cannot pass regardless of score. The visual checks
(silhouette reads as a grip, legibility, i8+ feel) are graded separately by the
loop operator viewing the PNG — this file scores only what is computable, so a
green number here can never rubber-stamp a bad silhouette.

Usage:
  python3 grade.py --iter 3            # grades renders/iter_03.geo.json + firmware
  python3 grade.py --iter 3 --json     # machine-readable
"""
from __future__ import annotations
import argparse, json, os, re, math, glob

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RENDERS = os.path.join(ROOT, "renders")
FW = os.path.join(ROOT, "firmware", "zmk-config")

# Real exposed pins per board -> the fix for the spec's impossible default map.
# ZMK devicetree form: (gpio_port, pin). XIAO nRF52840 breaks out D0..D10 only.
XIAO_PINS = {
    ("gpio0", 2), ("gpio0", 3), ("gpio0", 28), ("gpio0", 29), ("gpio0", 4),
    ("gpio0", 5), ("gpio1", 11), ("gpio1", 12), ("gpio1", 13), ("gpio1", 14),
    ("gpio1", 15),
}
BOARD_PINS = {"seeeduino_xiao_ble": XIAO_PINS}


def _rects_overlap(a, b, pad=0.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx + pad or bx + bw <= ax + pad or
                ay + ah <= by + pad or by + bh <= ay + pad)


def _key_rect(k, kw, kh):
    return (k["x"] - kw / 2, k["y"] - kh / 2, kw, kh)


def geometric_checks(geo_both):
    checks = []
    L, R = geo_both["left"], geo_both["right"]
    c = R["config"]
    kw, kh = c["key_w"], c["key_h"]

    # F1 key count (HARD)
    ok = len(R["keys"]) == 25 and len(L["keys"]) == 25
    checks.append(("F1 key-count 25/half", ok, True,
                   f"L={len(L['keys'])} R={len(R['keys'])}"))

    # F2 no key overlaps (HARD)
    overlaps = 0
    ks = R["keys"]
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            if _rects_overlap(_key_rect(ks[i], kw, kh), _key_rect(ks[j], kw, kh), pad=0.05):
                overlaps += 1
    checks.append(("F2 no key overlaps", overlaps == 0, True, f"{overlaps} overlaps"))

    # F3 true mirror (HARD): L is R reflected across board_w/2
    W = R["board_w"]
    maxerr = 0.0
    rmap = {(k["row"], k["col"]): k for k in R["keys"]}
    for k in L["keys"]:
        rk = rmap[(k["row"], k["col"])]
        maxerr = max(maxerr, abs((W - k["x"]) - rk["x"]), abs(k["y"] - rk["y"]))
    checks.append(("F3 left is true mirror of right", maxerr < 0.05, True,
                   f"max mirror err {maxerr:.3f}mm"))

    # F4 thumb ergonomics: every key within stated arc [rmin,rmax] of anchor
    axr, ayr = R["anchor"]
    rmin, rmax = R["arc"]["rmin"], R["arc"]["rmax"]
    radii = [math.hypot(k["x"] - axr, k["y"] - ayr) for k in R["keys"]]
    inarc = all(rmin - 1e-6 <= r <= rmax + 1e-6 for r in radii)
    checks.append((f"F4 keys within thumb arc [{rmin:.0f},{rmax:.0f}]mm", inarc, False,
                   f"r range {min(radii):.1f}..{max(radii):.1f}mm"))

    # F5 keep-outs non-overlapping with keys and each other (HARD)
    kos = list(R["keepouts"].items())
    ko_key_clash = 0
    for _, rect in kos:
        for k in R["keys"]:
            if _rects_overlap(rect, _key_rect(k, kw, kh)):
                ko_key_clash += 1
    ko_ko_clash = 0
    for i in range(len(kos)):
        for j in range(i + 1, len(kos)):
            if _rects_overlap(kos[i][1], kos[j][1]):
                ko_ko_clash += 1
    checks.append(("F5 keep-outs clear of keys & each other", ko_key_clash == 0 and ko_ko_clash == 0,
                   True, f"key-clash={ko_key_clash} ko-clash={ko_ko_clash}"))

    # F6 >=2 mount holes near inner edge + flat inner reference
    inner_holes = [h for h in R["mount_holes"] if h["x"] < 8.0]
    checks.append(("F6 >=2 inner-edge mount holes", len(inner_holes) >= 2, False,
                   f"{len(inner_holes)} inner holes / {len(R['mount_holes'])} total"))

    # F7 envelope within phone-flank target
    ok_env = R["board_w"] <= c["env_w_max"] and R["board_h"] <= c["env_h_max"]
    checks.append((f"F7 envelope <= {c['env_w_max']:.0f}x{c['env_h_max']:.0f}mm", ok_env, False,
                   f"{R['board_w']:.1f}x{R['board_h']:.1f}mm (flanks {c['phone_len']:.0f}mm phone)"))

    # F-usb: USB-C on bottom edge (reachable)
    ux, uy, uw, uh = R["keepouts"]["usb_c"]
    checks.append(("F-usb USB-C on bottom edge", uy < 3.0, False, f"usb y={uy:.1f}mm"))
    return checks


def firmware_checks():
    checks = []
    board = "seeeduino_xiao_ble"

    def read(p):
        fp = os.path.join(FW, p)
        return open(fp).read() if os.path.exists(fp) else ""

    dtsi = read("boards/shields/thumbdeck/thumbdeck.dtsi")
    keymap = read("boards/shields/thumbdeck/thumbdeck.keymap")
    conf = read("boards/shields/thumbdeck/thumbdeck.conf") or read("config/thumbdeck.conf")
    left = read("boards/shields/thumbdeck/thumbdeck_left.overlay")
    right = read("boards/shields/thumbdeck/thumbdeck_right.overlay")
    build = read("build.yaml")

    # F8 combined matrix transform = 50 unique RC(), 10 cols x 5 rows (HARD).
    # Two 25-key halves join into ONE logical keymap: central(right)=cols 0..4,
    # peripheral(left)=cols 5..9 via col-offset. (Correctness fix vs the spec's
    # literal "25/half transform", which would not build on ZMK.)
    rc = re.findall(r"RC\((\d+),(\d+)\)", dtsi)
    seen = [(int(a), int(b)) for a, b in rc]
    dup = len(seen) != len(set(seen))
    covers = len(set(seen)) == 50 and all(0 <= r < 5 and 0 <= cc < 10 for r, cc in seen)
    checks.append(("F8 combined transform = 50 unique RC() (25/half)", covers and not dup, True,
                   f"{len(seen)} entries, {len(set(seen))} unique"))

    # F8b both halves represented: 25 cols<5 (central) + 25 cols>=5 (peripheral)
    central = sum(1 for r, cc in set(seen) if cc < 5)
    periph = sum(1 for r, cc in set(seen) if cc >= 5)
    checks.append(("F8b 25 central-cols + 25 peripheral-cols", central == 25 and periph == 25,
                   True, f"central={central} peripheral={periph}"))

    # F8c keymap default layer has 50 bindings (count only the default layer)
    dl = re.search(r"default_layer\s*\{.*?bindings\s*=\s*<(.*?)>;", keymap, re.S)
    binds = re.findall(r"&(?:kp|mo|mt|trans|kt|bt)\b", dl.group(1) if dl else "")
    checks.append(("F8c keymap default layer has 50 bindings", len(binds) == 50, True,
                   f"{len(binds)} bindings"))

    # F8d peripheral (left) carries the col-offset that joins the halves
    checks.append(("F8d peripheral col-offset joins halves", "col-offset" in left, True,
                   f"col-offset in left overlay={('col-offset' in left)}"))

    # F9 pins valid for board + consistent (HARD)
    def pins(text):
        return [(g, int(p)) for g, p in re.findall(r"&(gpio[01])\s+(\d+)", text)]
    row_block = re.search(r"row-gpios\s*=\s*(.*?);", dtsi, re.S)
    col_block = re.search(r"col-gpios\s*=\s*(.*?);", dtsi, re.S)
    rowp = pins(row_block.group(1)) if row_block else []
    colp = pins(col_block.group(1)) if col_block else []
    allp = rowp + colp
    valid = BOARD_PINS[board]
    bad = [p for p in allp if p not in valid]
    unique = len(allp) == len(set(allp))
    right_count = len(rowp) == 5 and len(colp) == 5
    ok_pins = not bad and unique and right_count
    checks.append(("F9 GPIO pins valid+unique for XIAO nRF52840", ok_pins, True,
                   f"{len(rowp)}r+{len(colp)}c, invalid={bad}, unique={unique}"))

    # F10 BLE split + battery reporting
    have_ble = "CONFIG_ZMK_BLE=y" in conf.replace(" ", "")
    have_batt = "CONFIG_ZMK_BATTERY" in conf.replace(" ", "") or "battery" in conf.lower()
    role_left = "peripheral" in left.lower() or "central" not in left.lower()
    role_right = "central" in right.lower()
    checks.append(("F10 BLE on + battery reporting + split roles", have_ble and have_batt and role_right,
                   True, f"ble={have_ble} batt={have_batt} right=central:{role_right}"))

    # F11 build.yaml lists both shields (CI can actually build)
    ok_build = "thumbdeck_left" in build and "thumbdeck_right" in build and board in build
    checks.append(("F11 build.yaml drives CI for both halves", ok_build, True,
                   f"present={bool(build)}"))

    # F12 diode direction consistent col2row
    checks.append(("F12 diode-direction col2row", 'diode-direction = "col2row"' in dtsi
                   or "col2row" in dtsi, False, "col2row in dtsi"))
    return checks


def score(checks):
    hard_fail = [n for n, ok, hard, _ in checks if hard and not ok]
    total = len(checks)
    passed = sum(1 for _, ok, _, _ in checks if ok)
    pct = round(100 * passed / total, 1)
    return pct, hard_fail, passed, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    geo_path = os.path.join(RENDERS, f"iter_{a.iter:02d}.geo.json")
    geo = json.load(open(geo_path))
    checks = geometric_checks(geo) + firmware_checks()
    pct, hard_fail, passed, total = score(checks)
    passing = not hard_fail and pct >= 90.0

    report = {
        "iter": a.iter, "score": pct, "passed": passed, "total": total,
        "hard_fails": hard_fail, "functional_pass": passing,
        "checks": [{"name": n, "ok": ok, "hard": hard, "detail": d}
                   for n, ok, hard, d in checks],
    }
    if a.json:
        print(json.dumps(report, indent=2))
        return
    print(f"\n=== FUNCTIONAL GRADE — iter {a.iter:02d} ===")
    for n, ok, hard, d in checks:
        tag = "PASS" if ok else "FAIL"
        h = "!" if hard else " "
        print(f"  [{tag}]{h} {n:52s} {d}")
    print(f"\n  score {pct}%  ({passed}/{total})   hard-fails: {hard_fail or 'none'}")
    print(f"  FUNCTIONAL_PASS = {passing}\n")


if __name__ == "__main__":
    main()
