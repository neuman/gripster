> **Authoritative status:** see [`docs/evaluation.md`](evaluation.md). The scan/ghosting principles below are correct; MCU/pin details in the v0.3 section are stale (now E73, 9×10, 79 keys).

# Matrix, diodes & the single-controller scan

> **v0.8 update.** The matrix grew to **9 rows × 10 columns** (~81 keys: 6×6/grip +
> clusters), scanned by a **Raytac MDBT50Q-1MV2 module** (not a nice!nano). Diodes
> are **SOD-323** on the **back** of the board (no room front at 8.5 mm pitch),
> `col2row`, cathode → row. Right grip = COL0–4, left = COL5–9 (over the JST-GH
> harness), ROW0–8 shared. Still a ZMK **unibody** kscan, **not** a split — do not
> set `CONFIG_ZMK_SPLIT`/`col-offset`. GPIO budget ~23 (19 matrix + 2 I²C + 1
> Cirque DR-IRQ + 1 batt ADC), well within the module's ~48. Keep the external
> **4.7 kΩ row pull-downs** + **column series R**. The v0.3 text below still describes
> the scan/ghosting principles correctly; only the dimensions and MCU changed.

## Scanning & ghosting

thumbdeck is **one** 5 row × 10 column matrix scanned by a single nRF52840 — no
split. One **1N4148W** diode per key, uniform orientation, **`col2row`**: columns
are driven, rows are read. The per-key diode blocks reverse current so any combo
of simultaneous presses stays unambiguous (no ghosting).

- Logical **columns 0–4 = RIGHT grip** (wired locally to the MCU).
- Logical **columns 5–9 = LEFT grip** (reached over the bridge cable).
- **Rows 0–4** are shared across both grips (they run over the bridge too).

## Pins (nice!nano v2, `&pro_micro` nexus)

| | pins | notes |
|---|---|---|
| rows (read, pull-down) | `4 5 6 7 8` | shared, cross the bridge |
| cols 0–4 (drive, right grip) | `9 10 14 15 16` | local |
| cols 5–9 (drive, left grip) | `18 19 20 21 1` | cross the bridge |
| spare | `0 2 3` | `2/3` = I²C, free for the MCP23017 bridge-expander option |

15 of the nice!nano's ~18 usable GPIO. `grade.py` (F9) checks every pin is in the
real `pro_micro` set and that there are exactly 5 rows + 10 cols, all unique.

## No split transform — just one matrix

The `default_transform` in `thumbdeck.overlay` is a single 50-position map
(`columns=10, rows=5`). There is **no** central/peripheral, **no** `col-offset`,
**no** BLE bond between halves — the left grip's switches are simply columns 5–9
of the one matrix. Per-row keymap order is RIGHT grip (cols 0–4) then LEFT grip
(cols 5–9), matching the wiring.

> This is the v0.3 simplification over v0.2's ZMK BLE split. The 50-key keymap
> content is unchanged; what's gone is all the split machinery.

## Keymap ↔ render consistency

`matrix_map.py` rebuilds the expected 50-binding order from the render legends
(`deck.py`) and asserts it equals the ZMK `default_layer` bindings. Status:
**CONSISTENT (50/50)**.

## Bridge signal integrity (EE review #2)

The matrix scan crosses a long, flexing bridge cable, which is the design's main
electrical risk. Mitigations, all in the design now:

- **External 4.7 kΩ row pull-downs** at the MCU — the nRF's internal ~13 kΩ pull
  is too weak over the cable capacitance and would leave rows stale-high
  (phantom presses). External stronger pull-downs fix this.
- **100–330 Ω series resistors** on each driven column — slow the edges, damp
  ringing, cut crosstalk into adjacent sense rows.
- **Raised debounce** — `debounce-press-ms`/`debounce-release-ms` = 8 ms in the
  kscan, to reject cable-induced chatter.
- **Shielded / ground-interleaved flex**, flex-rated for the telescoping motion,
  strain-relieved at both connectors.
- **TVS** on the exposed bridge conductors (ESD).

## Diode direction sanity

`diode-direction = "col2row"` must match the physical diodes (cathode toward the
row). Keep every diode's cathode oriented the same way toward its row net — on
both grips, since the rows are shared across the bridge.
