# Grading system & iteration log

The loop converges on a layout that passes **two** gates, enforced by
`hardware/scripts/final_grade.py`. A design is "done" only when both pass.

## The two gates

### 1. Functional grade — `grade.py` (objective, computed)
17 checks over the shared geometry (`deck.py`) and the ZMK config. **HARD** checks
(●) block the pass regardless of score. Pass = no hard fails **and** score ≥ 90%.

| id | check | hard |
|----|-------|:----:|
| F1 | 25 keys per half | ● |
| F2 | no key overlaps | ● |
| F3 | left key field is a true mirror of right (≤0.05 mm) | ● |
| F4 | every key within the stated thumb arc | |
| F5 | keep-outs clear of keys and each other | ● |
| F6 | ≥2 inner-edge mount holes | |
| F7 | envelope within phone-flank target | |
| F-usb | USB-C on the bottom edge (mcu grip) | |
| F-bridge | bridge connector on the inner edge of both grips | ● |
| F-role | right = mcu (controller+LiPo+USB-C), left = passive | ● |
| F8 | single 5×10 transform = 50 unique `RC()` | ● |
| F8b | 25 right-grip + 25 left-grip columns | ● |
| F8c | keymap default layer = 50 bindings | ● |
| F9 | GPIO pins valid + unique for nice!nano (5r+10c=15) | ● |
| F10 | BLE + USB + battery reporting | ● |
| F11 | build.yaml drives CI (nice_nano_v2 + thumbdeck) | ● |
| F12 | diode direction `col2row` | |

### 2. Visual grade — `renders/visual_scores.json` (operator, from the PNG)
8 items from the spec's visual acceptance checklist, scored by viewing the render.
The computable subset (mirror, overlaps, envelope, keep-out collision, arc, bridge,
role) is **also** verified numerically in `grade.py`, so a visual pass can't
rubber-stamp a bad silhouette.

## Iteration log

**Phase v0.2 — two-controller ZMK BLE split** (`renders/iter_03.png`)

| iter | functional | visual | key change |
|:----:|:----------:|:------:|------------|
| 00 | 81.2% — 2 hard fails | — | first render; keep-outs collided with keys; keymap double-counted |
| 01 | 93.8% | — | added component strips + D-grip; thumb arc fixed; envelope still 67 mm |
| 02 | 100% | fail (V3) | envelope tightened to 63 mm; left half read "5 4 3 2 1" (mirror reversed columns) |
| 03 | 100% | 8/8 | pre-reversed left legends; silk half+version+mating-edge → **v0.2 PASS** |

**Phase v0.3 — single controller + wired bridge** (`renders/iter_05.png`)

| iter | functional | visual | key change |
|:----:|:----------:|:------:|------------|
| 05 | 94.1% — 1 hard fail | — | pivot to one nice!nano; passive left grip; bridge connector overlapped inner keys |
| 05′ | 100% (17/17) | 8/8 | moved bridge connector to inner-bottom corner → **v0.3 PASS** |

## Final verdict (v0.3, iter 05)

```
FUNCTIONAL : 100.0%  (17/17)  hard-fails: none   -> PASS
VISUAL     : 8/8 checklist items                 -> PASS
OVERALL    : *** PASS ***
```

Reproduce: `cd hardware/scripts && python3 layout_gen.py --iter 5 && python3 final_grade.py --iter 5`

**Kept renders:** `iter_03.png` (v0.2 two-controller milestone) and `iter_05.png`
(v0.3 single-controller final) — the two architectures side by side in history.
Layout is fully regenerable from `deck.py`.

## Honest limits of "confidence"

- **Functional** confidence is *structural*: the ZMK config is internally
  consistent, pins are physically real on the nice!nano, the transform/keymap
  match the render. It is **not** a compile — no Zephyr toolchain runs here. The
  real build gate is GitHub Actions (`.github/workflows/build.yml`).
- **Production** confidence covers the converged **placement + board outline**
  (real, in the `.kicad_pcb`/DXF). It does **not** cover the datasheet-verified
  switch footprint or copper routing — both `TODO(user)` by design.
