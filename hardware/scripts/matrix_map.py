#!/usr/bin/env python3
"""
matrix_map.py — key -> (row,col) -> half planning aid.

Prints the physical matrix for each half and the combined logical keymap order,
and checks that the render legends (deck.py) agree with the ZMK keymap bindings
so the two never silently drift apart.

Combined logical layout (per row): RIGHT half = logical cols 0..4,
LEFT half = logical cols 5..9 (peripheral col-offset). See docs/matrix-and-diodes.md.
"""
import os, re
import deck

FW = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                     "firmware", "zmk-config", "boards", "shields", "thumbdeck"))

# XIAO nRF52840 exposed pins used by the matrix (rows D0..D4, cols D5..D9)
ROW_PINS = ["P0.02 (D0)", "P0.03 (D1)", "P0.28 (D2)", "P0.29 (D3)", "P0.04 (D4)"]
COL_PINS = ["P0.05 (D5)", "P1.11 (D6)", "P1.12 (D7)", "P1.13 (D8)", "P1.14 (D9)"]


def print_half(name, legends):
    print(f"\n{name} half — physical 5x5 (col0 = inner/split edge):")
    print("        " + "  ".join(f"c{c}" for c in range(5)))
    for r in range(5):
        print(f"  row{r} " + "  ".join(f"{legends[r][c]:>3}" for c in range(5)))


def keymap_default_bindings():
    txt = open(os.path.join(FW, "thumbdeck.keymap")).read()
    dl = re.search(r"default_layer\s*\{.*?bindings\s*=\s*<(.*?)>;", txt, re.S).group(1)
    toks = re.findall(r"&kp\s+(\w+)|&mo\s+(\d+)", dl)
    return [a or f"mo{b}" for a, b in toks]


def main():
    print("=== thumbdeck matrix map ===")
    print("rows:", ROW_PINS)
    print("cols:", COL_PINS)
    print_half("RIGHT (central, logical cols 0..4)", deck.RIGHT_LEGENDS)
    print_half("LEFT  (peripheral, logical cols 5..9)", deck.LEFT_LEGENDS)

    # Expected combined keymap order: per row, right c0..4 then left c0..4
    expected = []
    for r in range(5):
        expected += [deck.RIGHT_LEGENDS[r][c] for c in range(5)]
        expected += [deck.LEFT_LEGENDS[r][c] for c in range(5)]

    binds = keymap_default_bindings()
    # normalise keycodes -> legend tokens for comparison
    kc = {"N0": "0", "N1": "1", "N2": "2", "N3": "3", "N4": "4", "N5": "5",
          "N6": "6", "N7": "7", "N8": "8", "N9": "9", "ENTER": "ENT",
          "COMMA": ",", "DOT": ".", "FSLH": "/", "SPACE": "SPC", "LEFT": "LFT",
          "DOWN": "DN", "UP": "UP", "RIGHT": "RGT", "LCTRL": "CTL", "LGUI": "GUI",
          "LALT": "ALT", "mo1": "FN"}
    norm = [kc.get(b, b) for b in binds]

    ok = len(norm) == 50 and all(
        norm[i].upper() == expected[i].upper() for i in range(min(len(norm), 50)))
    print(f"\nkeymap bindings: {len(norm)} (expected 50)")
    if ok:
        print("CONSISTENT: render legends == ZMK keymap bindings.")
    else:
        print("MISMATCH between render legends and keymap:")
        for i in range(min(len(norm), len(expected))):
            if norm[i].upper() != expected[i].upper():
                print(f"  pos {i:2d}: keymap={norm[i]!r} legend={expected[i]!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
