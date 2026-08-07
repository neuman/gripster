# Routing — autonomous route + validate pipeline (rev-A)

**State: DONE. Both boards are fully routed and DRC-clean.** `kicad-cli 9.0.9`,
error severity: **0 violations, 0 unconnected items** on `thumbdeck_right` and
`thumbdeck_left` (both re-routed and re-verified 2026-08-07 for the **v0.27**
20-way bridge + on-ribbon battery — see the v0.27 note below; previously
2026-07-17 for the v0.19 GBC outline; results in
`hardware/kicad/generated/drc_{right,left}.json`, a local build artifact — it is
git-ignored, regenerate with `route.sh`). The fab package (gerbers, JLC BOM, CPL)
is written to `hardware/kicad/generated/fab/` by `gen_fab.py` and is likewise not
committed. Note that DRC-clean means **no design rule is violated** — it is not a
statement that the circuit is correct, and neither board has been fabricated. There is **no
finish-in-the-GUI step left** — the loop below converges headlessly.

> Older revisions of this file described KiCad-7 headless limitations (no
> `kicad-cli` DRC, no zone fill from Python) and a manual GUI finishing checklist.
> Those constraints are **gone**: the environment runs **KiCad 9**, which does both
> headlessly. Do not resurrect them.

> **v0.27 (2026-08-07):** the bridge went **16-way → 20-way** (JUSHUO
> AFA07-S20FCC-00, LCSC C262352) and the four extra conductors carry the cell, so
> the separate battery cable — and the right board's J3 — are gone; the left board
> gains **J4** (JST-PH) and **F1** (0.75 A PPTC, LCSC C84140). J2 moved to deck y
> **28.5** on both boards and `deck.py`'s inner-mid mount hole is frozen at
> **46.0** (its Ø8 boss disc was what capped the connector's pin count). Both
> boards were re-generated and **re-routed from scratch to 0/0**. Counts after the
> change: **right = 75 nets, 114 footprints, 30 GND escape vias; left = 60 nets**
> (was 58 — `VCELL_RAW` and `VBAT_CELL` are new there). The E73 pad→net table
> below is **unchanged**: all 14 matrix signals keep their conductors, so the
> firmware is untouched.

## The pipeline

```
gen_board.py  ->  route.sh <side>  ->  (stitch.py inside route.sh)  ->  DRC gate  ->  gen_fab.py
```

```bash
cd hardware/scripts
python3 gen_board.py        # placement + netlist + fixed USB copper + GND escape vias
./route.sh right 100 5      # DSN -> Freerouting -> SES -> stitch -> DRC -> renders; retries
./route.sh left  100 5      #   until 0 unconnected, max 5 attempts
python3 gen_fab.py          # refuses to export unless DRC is 0/0
```

> **v0.27 — the loop actually loops now, and the 20-way needs it.** Freerouting runs
> multithreaded (`-mt 4`), so the same copper does not give the same result twice, and
> the wider bridge connector put the inner corridor close enough to the edge that a run
> lands on 0 or 1 open nets more or less at random — observed 0/0, then `ROW6` open on
> the right and `COL6` on the left, on *identical* input. `route.sh` now takes a third
> argument, `max_attempts` (default 5), and re-runs from the **pristine** generated board
> each time. Restarting from the pristine file is the whole trick: retrying on top of an
> already-imported SES lets the previous attempt's tracks ride through the DSN as fixed
> wires, so the router just inherits the same dead end. If it still fails it exits 1 with
> the count, rather than handing `gen_fab.py` a board that will be refused anyway.
>
> The 16-way closed in 30 passes; budget **100** for the 20-way.

### Stage by stage

1. **`gen_board.py`** — places every footprint (all SMT, all on B.Cu), builds the
   full netlist, and pre-draws two things autorouters can't produce:
   - **Deterministic USB copper.** The USB-C's data pads are interleaved same-net
     pairs (B6 A7 A6 B7). D− is joined by a copper bar; D+ hops via In2.Cu, plus
     fixed In2 runs to the module's USB pads. This exact-geometry copper rides
     through the DSN as *fixed wires*.
   - **GND escape vias.** Every small-part GND pad gets a pre-placed via to the
     In1 GND plane (**30** on the right board since v0.27) before routing. Without
     them, Freerouting starves trying to reach GND pads on outer layers and the
     loop never converges to 0/0.
2. **`route.sh <side>`** — the autonomous loop:
   - Exports a Specctra **DSN** from `pcbnew`.
   - **Marks In1.Cu as a `power` layer** in the DSN. KiCad exports all four layers
     as `signal`, and zones aren't in the DSN — Freerouting would otherwise
     happily perforate the solid GND plane with signal traces. This one rewrite
     keeps In1 a plane.
   - **Injects a real `power` netclass** (v0.27) into the same DSN: `VBAT_CELL`,
     `VCELL_RAW` and `VBAT` are pulled out of KiCad's flat `kicad_default` class
     and given **0.4 mm** width. This is where `gen_board.py`'s `PWR = 0.4`
     actually gets applied — KiCad 9 exposes no netclass setter on
     `BOARD_DESIGN_SETTINGS` via SWIG, so until v0.27 that constant was **dead
     code** and `VBAT_CELL` shipped at 0.2 mm (~336 mΩ, a third of the whole
     charge loop). It matters now that the cell crosses the bridge: the ribbon and
     F1's ≤0.45 Ω both add to the same loop, and widening buys ~170 mΩ back —
     more than the ribbon costs. **0.5 mm was tried first and does not route**:
     Freerouting could not close `VBAT_CELL` through the inner corridor at that
     width (2 open items, plus a knock-on `COL4`). 0.4 mm costs ~34 mΩ more than
     0.5 and converges; F1 dominates the loop either way. Keep `PWR` and
     `route.sh`'s `PWR_W` in sync.
   - Runs **Freerouting** headless with **`-Xss16m`** (the router's recursive
     maze expansion overflows the default JVM thread stack on this board's ~160
     nets) and a 15-minute timeout.
   - Imports the SES back and saves. There is deliberately **no gap-closing
     post-pass**: KiCad's own connectivity + DRC `unconnected_items` is the
     arbiter (an earlier union-find "bridger" drew blind shorts).
3. **`stitch.py`** — obstacle-aware GND stitching, then zone fill:
   - Adds stitch vias tying the F/B GND pour islands to the In1 plane, checking
     every candidate against non-GND tracks **on any layer** (a through-via
     crosses all layers), drilled holes, via-keepout rule areas (dome keepouts,
     the E73 antenna zone) and non-GND pads.
   - Orphaned islands get a via straight into the solid plane.
   - Fills all zones and saves.
4. **DRC gate** — `kicad-cli pcb drc --severity-error`, JSON summarized (violation
   types + open nets). The loop is only "done" at **0 violations / 0 unconnected**.
5. **`gen_fab.py`** — exports 4-layer gerbers + Excellon, JLC-format `bom.csv` and
   `positions.csv` per side. **Hard-gated:** it re-runs DRC and refuses to export
   anything if the board isn't clean. It also normalizes CPL rotations to the
   0..360 range, and silk text is kept ≥0.8 mm.

## Board facts

- **75.0 × 97.0 mm** per grip (v0.19: GBC-boxy straight outer edge; v0.17's chin
  cut + top-zone electronics retained), **4-layer**: F.Cu (signal) / **In1.Cu
  (solid GND plane, never routed through)** / In2.Cu (signal) / B.Cu (signal).
  Note the v0.17 route is
  tighter than rev-A — and tighter again at 75.0 mm in v0.19 — the module (top) and the FFC bridge (inner-bottom) put the
  bridge nets across the board (14 matrix + GND + `VBAT_CELL` since v0.27, over a
  20-position ZIF), so `route.sh`'s route-until-clean loop may need a
  few passes to hit 0/0.
- 1.6 mm FR-4, **ENIG** (dome contacts), 0.2 mm clearance/track rules, via 0.6/0.3.
- All parts on **B.Cu** → single-sided reflow, no hand-soldered parts (the USB-C
  shell's plated stakes and the FFC/slide-switch locating pegs are the only
  through-board features, all placed in the same single-pass JLC assembly).

## Design quirks the route depends on

- **Snap-dome escape gap.** The production `snaptron_7mm_contact` footprint is a
  2.86 mm centre pad inside a continuous leg ring (4.4–6.9 mm dia, 13 overlapping
  circles spanning 292°) with a **67.5° gap** — the *only* corridor through which
  the column trace can reach the centre pad. Worst-case dome rotation still lands
  3 of 4 legs on the ring. Each dome also carries an F.Cu pour keepout (r 3.8) and
  an all-layer via keepout (r 3.6) that both the router and the stitcher honour.
- **E73 antenna keep-out.** The module sits antenna-**up** at the centre of the
  **top** board edge (v0.17); the all-layer keep-out covers the antenna area and
  crosses the board edge (~3 mm on-board strip + the off-board extension), and the
  on-board region is verified copper-free on all 4 layers. It's a rule area in the
  footprint, so Freerouting (via the DSN) and stitch.py both avoid it.
- **COL9 on pad 18 (P0.04/AIN2)**, not pad 11 (P0.00/XL1) — the XTAL pins stay
  free even though firmware runs the LF clock from the internal RC.
- **J2's deck y is a joint constraint with the enclosure, not a routing choice**
  (v0.27). The lower bound is the clamp's lane plan — the 21 mm ribbon rides a
  walled channel between the two extension springs, which needs y ≥ 28.20; the
  upper bound is this file's own `assert_clear_of_bosses`, since the inner-mid
  mount hole's Ø8 boss disc is what caps the connector's length (26.85 mm land,
  4.08 mm to the boss against a 4.00 gate). **28.5** satisfies both, and
  `deck3d.py --check-lanes` asserts it against the placement export — lane y vs
  J2's slot centre to 0.25 mm, and ribbon width vs J2's body so a wrong pin count
  fails loudly. The old numbers (lane 26.5, connector 24.5) were two independent
  values that a comment merely *claimed* were equal; nothing compared them.

## E73 pad → net (as routed; pad N = Ebyte datasheet pin N)

| Pad | Net | | Pad | Net |
|--:|---|---|--:|---|
| 1 | ROW0 | | 28 | COL0 |
| 2 | ROW1 | | 30 | COL1 |
| 6 | ROW2 | | 32 | COL2 |
| 12 | ROW3 | | 33 | COL3 |
| 14 | ROW4 | | 34 | COL4 |
| 16 | ROW5 | | 35 | COL5 |
| 17 | ROW6 | | 3 | COL6 |
| 20 | ROW7 | | 9 | COL7 |
| 22 | ROW8 | | 10 | COL8 |
| 7 | VBAT_SENSE (AIN0) | | 18 | COL9 (P0.04/AIN2) |
| 15 | SDA → TP6 | | 4 | SCL → TP7 |
| 8 | TP_INT → TP8 | | 26 | RESET |
| 19 | 3V3 (REG0 out) | | 23 | VBAT (VDDH) |
| 27 | VBUS | | 29/31 | USB D−/D+ |
| 37/39 | SWDIO/SWDCLK | | 5/21/24 | GND |

SWD + power are on silk-labelled test pads **TP1–5** (SWDIO / SWDCLK / RESET /
3V3 / GND); the spare I²C breakout is **TP6–8** (SDA / SCL / INT) for a rev-B
trackpad or expansion.

## Verification artifacts

| File | What |
|---|---|
| `hardware/kicad/generated/drc_right.json` / `drc_left.json` | 0 violations, 0 unconnected (error severity) |
| `hardware/kicad/generated/fab/{right,left}/` | gerbers.zip + bom.csv + positions.csv (JLC format) |
| `renders/routed_{right,left}_2d.svg`, `routed_*_top/bottom.png` | flat copper + 3D renders from the routed boards |
| `hardware/scripts/sim_matrix.py` | 78 unique (row,col) keys, 0 collisions, 0 ghost/miss failures — final pass |
