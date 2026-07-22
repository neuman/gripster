# Grading system & iteration log — HISTORICAL (v0.4 era, superseded)

> **Historical record.** This describes the v0.4 auto-grader for the abandoned
> **50-key nice!nano** design. None of it reflects rev-A / v0.19 (78 keys, one
> E73 module, routed 4-layer boards) — the "PASS" verdict below is a pass of that
> old geometry/config grader, **not** a statement about the current design or
> about any physical hardware. Current status lives in
> [`docs/evaluation.md`](../../docs/evaluation.md); the scripts referenced below
> are archived in `hardware/scripts/legacy/`.

Two gates, enforced by `hardware/scripts/legacy/final_grade.py`. Done only when
both pass. As of v0.4 the grade also encodes the **EE design-review** findings
(see `../../docs/design-review.md`) so the design is held to them, not just
reminded of them.

> Scope caveat: the grade covers **geometry + config/doc structure**. It is *not*
> electrical sign-off — no compile, no DRC/ERC, no RF sim. Passing is necessary,
> not sufficient. Human-verified fab gates are listed in the design review.

## Gate 1 — functional grade (`grade.py`, 27 checks)

HARD checks (●) block the pass regardless of score. Pass = no hard fails and ≥90%.

**Geometry** F1 keys=25/half ● · F2 no overlap ● · F3 true mirror ● · F4 thumb arc ·
F5 keep-outs clear ● · F6 inner mount holes · F7 envelope · F-usb USB present ·
**F-antenna** RF keep-out overhangs edge + ≥10 mm from LiPo + clear of keys ● ·
F-bridge connector on both inner edges ● · F-role right=mcu(+antenna)/left=passive ●

**Firmware** F8 5×10 transform=50 ● · F8b 25+25 grips ● · F8c keymap 50 ● ·
F9 nice!nano pins valid ● · F10 BLE+USB+battery ● · F11 build.yaml ● · F12 col2row ·
**F-si-debounce** kscan debounce ≥6 ms ●

**Docs/BOM (EE review encoded)** F-si-passives row pull-downs + column series R ● ·
F-esd-tvs TVS on bridge/USB ● · F-charge charge-current vs cell noted ● ·
F-switch-verify meter the pinout ● · F-si-doc matrix doc SI · F-review-doc
design-review.md + FMEA ● · F-bringup bring-up + current checkpoints ● ·
F-fab-gates README gates fab on schematic+ERC+DRC ●

## Gate 2 — visual grade (`renders/visual_scores.json`, 9 items)
Silhouette, mirror, key field, thumb arc, bridge/Backbone interface, keep-outs by
role, silk legibility, envelope, **+ V9 antenna overhang**. Computable items are
also verified numerically in `grade.py`.

## Iteration log

| phase | iter | result | key change |
|---|:---:|---|---|
| v0.2 two-controller BLE split | 00→03 | PASS (16/16, 8/8) | converged split layout; left legends fixed |
| v0.3 single controller + wired bridge | 05 | PASS (17/17, 8/8) | one nice!nano; passive left; bridge connector |
| **v0.4 EE-hardening** | 06 | 92.6% → **PASS (27/27, 9/9)** | antenna keep-out (F-antenna), bridge SI (debounce + BOM pull-downs/series-R/TVS), charge-current, metering + bring-up + ERC/DRC gates. Fixed: antenna/controller touching edge (float overlap) → 0.6 mm gap; `series res` substring in BOM check |

## Final verdict (v0.4, iter 06)

```
FUNCTIONAL : 100.0%  (27/27)  hard-fails: none   -> PASS
VISUAL     : 9/9 checklist items                 -> PASS
OVERALL    : *** PASS ***
```

Reproduce: `cd hardware/scripts/legacy && python3 ../layout_gen.py --iter 6 && python3 final_grade.py --iter 6`

**Kept renders:** `iter_03.png` (v0.2), `iter_05.png` (v0.3), `iter_06.png` (v0.4 final).

## What the grade still does NOT prove (human gates — `../../docs/design-review.md`)
Compile (ZMK CI), DRC/ERC, RF performance, the metered switch pinout, mechanical
flex, and the real bridge-cable flex life. Those gate a fab order; the grade doesn't.
