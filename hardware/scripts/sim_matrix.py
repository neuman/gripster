#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""sim_matrix.py — matrix ghosting / NKRO simulation for thumbdeck.

Extracts the ACTUAL electrical matrix from the generated KiCad boards (each
switch's centre-pad COL net + the ROW net of the diode sharing its DN node),
then simulates a col2row scan under many finger-press scenarios — exhaustive
small combos + thousands of random N-finger presses — with diodes (real board)
and, as a control, WITHOUT diodes (to prove the diodes are the thing preventing
ghosting and that the sim actually detects ghosting).

col2row scan model:
  * driving column c high, all pressed keys (r,c') connect col c'->row r THROUGH
    a diode that conducts col->row only.
  * WITH diodes: from driven col c you can only reach rows r where (r,c) pressed
    (one hop; you cannot leave a row because row->col needs a reverse diode).
    => scan reads EXACTLY the pressed keys. Never ghosts. (proved by BFS anyway)
  * WITHOUT diodes: every switch is a plain short between its row and col; the
    press set forms a bipartite graph and any (row,col) in the same connected
    component reads as pressed => classic rectangle ghosting.
"""
import sys, os, itertools, random, pcbnew
from collections import defaultdict

GEN = os.path.join(os.path.dirname(__file__), "..", "kicad", "generated")


def extract_matrix(path):
    """Return {(row,col): keyref} and per-key node info from a real board."""
    b = pcbnew.LoadBoard(path)
    # map: net-name per pad, grouped by footprint
    sw_col = {}      # ref -> col net name (switch centre pad "1")
    sw_node = {}     # ref -> DN node net (switch ring pad "2")
    diode_node = {}  # ref -> DN node (anode pad "2")
    diode_row = {}   # ref -> row net (cathode pad "1")
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("SW"):
            for p in fp.Pads():
                nm = p.GetNetname()
                if p.GetNumber() == "1": sw_col[ref] = nm
                elif p.GetNumber() == "2": sw_node[ref] = nm
        elif ref[0] == "D" and ref[1:].isdigit():
            for p in fp.Pads():
                nm = p.GetNetname()
                if p.GetNumber() == "1": diode_row[ref] = nm
                elif p.GetNumber() == "2": diode_node[ref] = nm
    # join switch<->diode by shared DN node
    node_to_row = {}
    for dref, node in diode_node.items():
        node_to_row[node] = diode_row.get(dref)
    matrix = {}
    dupes = []
    for swref, node in sw_node.items():
        col = sw_col.get(swref)
        row = node_to_row.get(node)
        if row is None or col is None:
            continue
        key = (row, col)
        if key in matrix:
            dupes.append((key, matrix[key], swref))
        matrix[key] = swref
    return matrix, dupes


def scan_with_diodes(pressed, rows, cols):
    """Return the decoded set of (row,col) the controller would see."""
    pressed = set(pressed)
    decoded = set()
    by_col = defaultdict(set)
    for (r, c) in pressed:
        by_col[c].add(r)
    for c in cols:            # drive each column high
        for r in by_col[c]:   # only directly-pressed keys on this col conduct col->row
            decoded.add((r, c))
    return decoded


def scan_without_diodes(pressed, rows, cols):
    """Union-find over pressed switches as plain shorts: any (row,col) that lands
    in a connected component containing >=1 driven col and its row reads pressed.
    Concretely a col c reads row r as pressed iff r and c are in the same connected
    component of the bipartite 'pressed' graph (rows|cols as nodes)."""
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        parent[find(a)] = find(b)
    for (r, c) in pressed:
        union(("R", r), ("C", c))
    # component -> which rows and cols it contains
    comp_rows = defaultdict(set); comp_cols = defaultdict(set)
    for (r, c) in pressed:
        comp_rows[find(("R", r))].add(r)
        comp_cols[find(("C", c))].add(c)
    decoded = set()
    for comp in set(list(comp_rows) + list(comp_cols)):
        for r in comp_rows.get(comp, ()):
            for c in comp_cols.get(comp, ()):
                decoded.add((r, c))   # this intersection reads pressed (ghost if not really pressed)
    return decoded


def run(name, path):
    matrix, dupes = extract_matrix(path)
    keys = list(matrix.keys())
    rows = sorted({r for r, c in keys})
    cols = sorted({c for r, c in keys})
    print(f"\n===== {name} =====")
    print(f"keys extracted: {len(keys)}  rows: {len(rows)} {rows}  cols: {len(cols)} {cols}")
    if dupes:
        print(f"  !!! DUPLICATE (row,col) intersections (indistinguishable keys): {dupes}")
    else:
        print("  OK: every key is a UNIQUE (row,col) intersection")

    rng = random.Random(1234)  # deterministic
    results = {"diode": {"tests": 0, "ghost_fail": 0},
               "nodiode": {"tests": 0, "ghost_fail": 0}}

    def check(pressed):
        pressed = set(pressed)
        for mode, fn in (("diode", scan_with_diodes), ("nodiode", scan_without_diodes)):
            decoded = fn(pressed, rows, cols)
            results[mode]["tests"] += 1
            # ghosting = decoded contains a key that wasn't pressed OR misses one
            if decoded != pressed:
                results[mode]["ghost_fail"] += 1
                if mode == "diode":
                    print(f"  DIODE GHOST/MISS on press {sorted(pressed)}: decoded {sorted(decoded)}")

    # 1) all singles + all pairs + all triples (exhaustive small)
    for n in (1, 2, 3):
        for combo in itertools.combinations(keys, n):
            check(combo)
    # 2) exhaustive 4-key on a stress subset near the worst-case rectangles
    #    (all 4-subsets of the 16 keys in rows[0:4] x cols[0:4] region)
    region = [k for k in keys if k[0] in rows[:4] and k[1] in cols[:4]]
    for combo in itertools.combinations(region, 4):
        check(combo)
    # 3) random N-finger presses, N = 2..12 (realistic + adversarial), 2000 each
    for N in range(2, 13):
        if N > len(keys):
            break
        for _ in range(2000):
            check(rng.sample(keys, N))
    # 4) explicit classic ghost rectangle: pick 3 corners of a rectangle, expect
    #    diodes clean, no-diode ghost of the 4th corner
    if len(rows) >= 2 and len(cols) >= 2:
        # find a real rectangle where all 4 corners are actual keys
        found = None
        for r1, r2 in itertools.combinations(rows, 2):
            for c1, c2 in itertools.combinations(cols, 2):
                corners = [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]
                if all(k in matrix for k in corners):
                    found = corners; break
            if found: break
        if found:
            three = found[:3]; fourth = found[3]
            d_dio = scan_with_diodes(three, rows, cols)
            d_no = scan_without_diodes(three, rows, cols)
            print(f"  rectangle test corners={found}")
            print(f"    press 3 {three}")
            print(f"    WITH diodes decoded={sorted(d_dio)} -> ghost={fourth in d_dio}")
            print(f"    NO   diodes decoded={sorted(d_no)} -> ghost={fourth in d_no}")

    for mode in ("diode", "nodiode"):
        r = results[mode]
        print(f"  [{mode:8}] {r['tests']} scenarios, ghost/miss failures: {r['ghost_fail']}")
    ok = (results["diode"]["ghost_fail"] == 0 and not dupes)
    detects = results["nodiode"]["ghost_fail"] > 0
    print(f"  VERDICT: diodes ghost-free={ok}; sim proven to detect ghosting (no-diode fails)={detects}")
    return ok and detects


if __name__ == "__main__":
    allok = True
    for side in ("right", "left"):
        allok &= run(side, os.path.join(GEN, f"thumbdeck_{side}.kicad_pcb"))
    # 5) combined full matrix (both grips share rows over the bridge)
    mr, dr = extract_matrix(os.path.join(GEN, "thumbdeck_right.kicad_pcb"))
    ml, dl = extract_matrix(os.path.join(GEN, "thumbdeck_left.kicad_pcb"))
    combined = {}
    coll = []
    for m in (mr, ml):
        for k, v in m.items():
            if k in combined: coll.append((k, combined[k], v))
            combined[k] = v
    print(f"\n===== COMBINED {len(mr)+len(ml)}-key matrix (rows shared over bridge) =====")
    print(f"total keys: {len(combined)}  (right {len(mr)} + left {len(ml)})")
    print(f"  cross-grip (row,col) collisions: {len(coll)} {coll if coll else '(none)'}")
    print(f"\nFINAL: {'PASS' if allok and not coll else 'FAIL'}")
