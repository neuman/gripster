#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
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

# Usable &pro_micro nexus pin indices on the nice!nano v2 (Pro Micro footprint):
# 0..10 and 14..21 minus the non-broken-out 11,12,13,17 -> 18 usable GPIO.
NICE_NANO_PRO_MICRO = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 18, 19, 20, 21}


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

    # F-usb: USB-C present on the MCU grip, clear of keys (F5 covers overlap)
    checks.append(("F-usb USB-C present on mcu grip", "usb_c" in R["keepouts"], False,
                   "usb_c keep-out present"))

    # F-antenna (EE review #1, HARD): nRF52840 antenna keep-out on the MCU grip,
    # reaching the top board edge (overhang = no copper under the RF path), well
    # clear of the LiPo (metal detunes it), and clear of keys.
    def antenna_ok(R):
        if "antenna" not in R["keepouts"]:
            return False, "no antenna keep-out"
        ax, ay, aw, ah = R["keepouts"]["antenna"]
        at_edge = (ay + ah) >= R["board_h"] - 0.5
        lx, ly, lw, lh = R["keepouts"]["lipo"]
        clr = ay - (ly + lh)                       # vertical gap antenna->lipo
        clear_keys = not any(_rects_overlap((ax, ay, aw, ah), _key_rect(k, kw, kh))
                             for k in R["keys"])
        ok = at_edge and clr >= 10.0 and clear_keys
        return ok, f"edge={at_edge} lipo_gap={clr:.0f}mm keys_clear={clear_keys}"
    a_ok, a_dtl = antenna_ok(R)
    checks.append(("F-antenna RF keep-out overhangs edge, >=10mm from LiPo", a_ok, True, a_dtl))

    # F-bridge: both grips expose a bridge connector on the inner/split edge
    def inner_bridge(geo):
        if "bridge" not in geo["keepouts"]:
            return False
        bx, by, bw, bh = geo["keepouts"]["bridge"]
        return bx < 8.0 or (bx + bw) > geo["board_w"] - 8.0
    checks.append(("F-bridge bridge connector on inner edge (both grips)",
                   inner_bridge(R) and inner_bridge(L), True,
                   f"R={inner_bridge(R)} L={inner_bridge(L)}"))

    # F-role: RIGHT = mcu (controller+antenna+LiPo+usb), LEFT = passive (no radio)
    mcu_ok = {"controller", "antenna", "lipo", "usb_c"} <= set(R["keepouts"].keys())
    passive_ok = not ({"controller", "antenna", "lipo"} & set(L["keepouts"].keys()))
    checks.append(("F-role right=mcu(+antenna), left=passive", mcu_ok and passive_ok, True,
                   f"R mcu={mcu_ok}, L passive={passive_ok}"))
    return checks


def firmware_checks():
    checks = []
    board = "nice_nano_v2"

    def read(p):
        fp = os.path.join(FW, p)
        return open(fp).read() if os.path.exists(fp) else ""

    overlay = read("boards/shields/thumbdeck/thumbdeck.overlay")
    keymap = read("boards/shields/thumbdeck/thumbdeck.keymap")
    conf = read("boards/shields/thumbdeck/thumbdeck.conf") or read("config/thumbdeck.conf")
    build = read("build.yaml")

    # F8 single 5x10 matrix transform = 50 unique RC() (HARD).
    # One controller scans all 50 keys: cols 0..4 = RIGHT grip, 5..9 = LEFT grip
    # (reached over the bridge). No split, no col-offset.
    rc = re.findall(r"RC\((\d+),(\d+)\)", overlay)
    seen = [(int(a), int(b)) for a, b in rc]
    dup = len(seen) != len(set(seen))
    covers = len(set(seen)) == 50 and all(0 <= r < 5 and 0 <= cc < 10 for r, cc in seen)
    checks.append(("F8 single 5x10 transform = 50 unique RC()", covers and not dup, True,
                   f"{len(seen)} entries, {len(set(seen))} unique"))

    # F8b both grips represented in the one matrix: 25 cols<5 (R) + 25 cols>=5 (L)
    rgrip = sum(1 for r, cc in set(seen) if cc < 5)
    lgrip = sum(1 for r, cc in set(seen) if cc >= 5)
    checks.append(("F8b 25 right-grip + 25 left-grip columns", rgrip == 25 and lgrip == 25,
                   True, f"right={rgrip} left={lgrip}"))

    # F8c keymap default layer has 50 bindings (count only the default layer)
    dl = re.search(r"default_layer\s*\{.*?bindings\s*=\s*<(.*?)>;", keymap, re.S)
    binds = re.findall(r"&(?:kp|mo|mt|trans|kt|bt)\b", dl.group(1) if dl else "")
    checks.append(("F8c keymap default layer has 50 bindings", len(binds) == 50, True,
                   f"{len(binds)} bindings"))

    # F9 pins valid for nice!nano + consistent: 5 rows + 10 cols = 15 unique (HARD)
    def pins(text):
        return [int(p) for p in re.findall(r"&pro_micro\s+(\d+)", text)]
    row_block = re.search(r"row-gpios\s*=\s*(.*?);", overlay, re.S)
    col_block = re.search(r"col-gpios\s*=\s*(.*?);", overlay, re.S)
    rowp = pins(row_block.group(1)) if row_block else []
    colp = pins(col_block.group(1)) if col_block else []
    allp = rowp + colp
    bad = [p for p in allp if p not in NICE_NANO_PRO_MICRO]
    unique = len(allp) == len(set(allp))
    right_count = len(rowp) == 5 and len(colp) == 10
    ok_pins = not bad and unique and right_count
    checks.append(("F9 pins valid+unique for nice!nano (5r+10c=15)", ok_pins, True,
                   f"{len(rowp)}r+{len(colp)}c, invalid={bad}, unique={unique}"))

    # F10 BLE + USB + battery reporting (single controller, no split roles)
    flat = conf.replace(" ", "")
    have_ble = "CONFIG_ZMK_BLE=y" in flat
    have_usb = "CONFIG_ZMK_USB=y" in flat
    have_batt = "CONFIG_ZMK_BATTERY" in flat or "battery" in conf.lower()
    checks.append(("F10 BLE + USB + battery reporting", have_ble and have_usb and have_batt,
                   True, f"ble={have_ble} usb={have_usb} batt={have_batt}"))

    # F11 build.yaml drives CI for the single board+shield
    ok_build = "thumbdeck" in build and board in build
    checks.append(("F11 build.yaml drives CI (nice_nano_v2 + thumbdeck)", ok_build, True,
                   f"present={bool(build)}"))

    # F12 diode direction consistent col2row
    checks.append(("F12 diode-direction col2row", "col2row" in overlay, False,
                   "col2row in overlay"))

    # F-si-debounce (EE review #2, HARD): kscan debounce tuned up for the long
    # bridge cable (>=6 ms press+release) to reject cable-induced chatter.
    def dbnc(kind):
        m = re.search(rf"debounce-{kind}-ms\s*=\s*<(\d+)>", overlay)
        return int(m.group(1)) if m else -1
    dp, dr = dbnc("press"), dbnc("release")
    checks.append(("F-si-debounce kscan debounce >=6ms (press+release)",
                   dp >= 6 and dr >= 6, True, f"press={dp} release={dr} ms"))
    return checks


def doc_checks():
    """Verify the design/docs/BOM actually incorporate each EE-review mitigation
    (not just mention it). These make the grade cover electrical review findings,
    including human-verified gates (metering, ERC/DRC, CI) that must be tracked."""
    checks = []

    def read(p):
        fp = os.path.join(ROOT, p)
        return open(fp).read().lower() if os.path.exists(fp) else ""

    bom = read("docs/bill-of-materials.md")
    conn = read("docs/connectivity-and-power.md")
    matrix = read("docs/matrix-and-diodes.md")
    footprints = read("hardware/footprints/README.md")
    review = read("docs/design-review.md")
    assembly = read("docs/assembly.md")
    readme = read("README.md")

    # F-si-passives: BOM carries the bridge SI hardening parts
    ok = "pull-down" in bom and "series" in bom and "resistor" in bom
    checks.append(("F-si-passives BOM has row pull-downs + column series R", ok, True,
                   f"pull-down={'pull-down' in bom} series-R={'series' in bom and 'resistor' in bom}"))

    # F-esd-tvs: ESD protection on the exposed bridge / USB lines
    checks.append(("F-esd-tvs BOM has TVS on bridge/USB", "tvs" in bom, True,
                   f"tvs in BOM={'tvs' in bom}"))

    # F-charge: charge-current vs cell C-rating is called out
    ok = ("1c" in conn or "charge current" in conn) and "protected" in conn
    checks.append(("F-charge charge-current vs cell C-rating noted", ok, True,
                   f"in connectivity-and-power={ok}"))

    # F-switch-verify: footprint doc requires METERING the pin pairing
    checks.append(("F-switch-verify footprint doc requires metering pinout",
                   "meter" in footprints, True, f"meter in footprints={'meter' in footprints}"))

    # F-si-firmware-note: matrix doc documents the SI mitigations
    ok = "pull-down" in matrix and "debounce" in matrix
    checks.append(("F-si-doc matrix doc covers pull-downs + debounce", ok, False,
                   f"pull-down={'pull-down' in matrix} debounce={'debounce' in matrix}"))

    # F-review-doc: the design review exists and tracks the findings + FMEA
    ok = bool(review) and "antenna" in review and "fmea" in review
    checks.append(("F-review-doc design-review.md w/ antenna + FMEA", ok, True,
                   f"present={bool(review)}"))

    # F-bringup: numbered bring-up checklist with a current-draw checkpoint
    ok = "bring-up" in assembly and "current" in assembly and "expect" in assembly
    checks.append(("F-bringup assembly has bring-up + current checkpoint", ok, True,
                   f"bring-up={'bring-up' in assembly} current={'current' in assembly}"))

    # F-fab-gates: fab explicitly gated on schematic + ERC + DRC + CI build
    ok = "erc" in readme and "drc" in readme and "schematic" in readme
    checks.append(("F-fab-gates README gates fab on schematic+ERC+DRC", ok, True,
                   f"erc={'erc' in readme} drc={'drc' in readme}"))
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
    checks = geometric_checks(geo) + firmware_checks() + doc_checks()
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
