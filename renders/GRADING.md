# Grading system & iteration log

The Section 7 loop converges on a layout that passes **two** gates. A design is
"done" only when both pass — enforced by `hardware/scripts/final_grade.py`.

## The two gates

### 1. Functional grade — `grade.py` (objective, computed)
16 checks over the shared geometry (`deck.py`) and the ZMK config. Some are
**HARD**: any hard fail blocks the pass regardless of score. Pass = no hard
fails **and** score ≥ 90%.

| id | check | hard |
|----|-------|:----:|
| F1 | 25 keys per half | ● |
| F2 | no key overlaps | ● |
| F3 | left is a true mirror of right (≤0.05 mm) | ● |
| F4 | every key within the stated thumb arc | |
| F5 | keep-outs clear of keys and each other | ● |
| F6 | ≥2 inner-edge mount holes | |
| F7 | envelope within phone-flank target | |
| F8 | combined transform = 50 unique `RC()` (25/half) | ● |
| F8b | 25 central-col + 25 peripheral-col positions | ● |
| F8c | keymap default layer = 50 bindings | ● |
| F8d | peripheral `col-offset` joins the halves | ● |
| F9 | GPIO pins valid + unique for XIAO nRF52840 | ● |
| F10 | BLE + battery reporting + split roles | ● |
| F11 | `build.yaml` drives CI for both halves | ● |
| F12 | diode direction `col2row` | |
| F-usb | USB-C on the bottom edge | |

### 2. Visual grade — `renders/visual_scores.json` (operator, from the PNG)
8 items from the spec's visual acceptance checklist (silhouette, mirror, key
field, thumb arc, Backbone interface, keep-outs, silk legibility, envelope),
scored by viewing the render. The computable subset (mirror, overlaps, envelope,
keep-out collision, arc) is **also** verified numerically in `grade.py`, so a
visual pass can never rubber-stamp a bad silhouette.

## Iteration log

| iter | functional | visual | key change |
|:----:|:----------:|:------:|------------|
| 00 | 81.2% — 2 hard fails | — | first render; keep-outs collided with keys; keymap double-counted |
| 01 | 93.8% — 0 hard fails | — | added top/bottom component strips + D-shaped grip; thumb arc fixed |
| 02 | 100% | fail (V3) | envelope tightened to 63 mm; **left half read "5 4 3 2 1"** (mirror reversed column order) |
| 03 | 100% | **8/8 pass** | pre-reversed left legends → reads "1 2 3 4 5 / Q W E R T"; added silk half+version+mating-edge |

## Final verdict (iter 03)

```
FUNCTIONAL : 100.0%  (16/16)  hard-fails: none   -> PASS
VISUAL     : 8/8 checklist items                 -> PASS
OVERALL    : *** PASS ***
```

Reproduce: `cd hardware/scripts && python3 layout_gen.py --iter 3 && python3 final_grade.py --iter 3`

**Kept renders** (bookends of the loop): `iter_01.png` — a genuine failing
predecessor (envelope 67 mm > target, F7 fail, 93.8%); `iter_03.png` — the final
pass. The full step-by-step is this log plus the git commit history; the layout
is fully regenerable from `deck.py`, so intermediate PNGs are reproducible via
`layout_gen.py --params`.

## Honest limits of "confidence"

- **Functional** confidence is *structural*: the ZMK config is internally
  consistent, pins are physically real on the XIAO, the transform/keymap match
  the render. It is **not** a compile — no Zephyr toolchain runs here. The real
  build gate is the GitHub Actions workflow (`.github/workflows/build.yml`); run
  it and confirm green before flashing.
- **Production** confidence covers the converged **placement + board outline**
  (real, in the `.kicad_pcb`/DXF). It does **not** cover the datasheet-verified
  switch footprint or copper routing — both are `TODO(user)` by design
  (PROJECT_SPEC §5/§10/§13: no fabricated dimensions, no fake routing).
