#!/usr/bin/env python3
"""
matrix_map.py — key -> (row,col) -> half planning aid.

Prints the physical matrix for each half and the combined logical keymap order,
and checks that the render legends (deck.py) agree with the ZMK keymap bindings
so the two never silently drift apart.

Single 5x10 matrix on one controller (v0.3): RIGHT grip = logical cols 0..4
(local), LEFT grip = cols 5..9 (over the bridge cable). See docs/matrix-and-diodes.md.
"""
import os, re
import deck

FW = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                     "firmware", "zmk-config", "boards", "shields", "thumbdeck"))

# nice!nano v2 &pro_micro pins used by the single 5x10 matrix.
ROW_PINS = ["pro_micro 4", "pro_micro 5", "pro_micro 6", "pro_micro 7", "pro_micro 8"]
COL_PINS = ["pro_micro 9", "pro_micro 10", "pro_micro 14", "pro_micro 15", "pro_micro 16",
            "pro_micro 18*", "pro_micro 19*", "pro_micro 20*", "pro_micro 21*", "pro_micro 1*"]


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
    print("=== thumbdeck matrix map (single 5x10 controller) ===")
    print("rows (shared, cross bridge):", ROW_PINS)
    print("cols (0-4 right/local, 5-9 left/*=over bridge):")
    for c in COL_PINS:
        print("   ", c)
    print_half("RIGHT grip (logical cols 0..4, local)", deck.RIGHT_LEGENDS)
    print_half("LEFT  grip (logical cols 5..9, over bridge)", deck.LEFT_LEGENDS)

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
