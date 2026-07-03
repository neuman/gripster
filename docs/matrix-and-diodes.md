# Matrix, diodes & the split transform

## Scanning & ghosting

Each half is a **5 row × 5 col** matrix = 25 keys, 10 GPIO. One **1N4148W**
diode per key, uniform orientation, **`col2row`**: columns are driven, rows are
read. The per-key diode blocks reverse current so simultaneous presses can't
create a phantom (ghost) key — you can hold any combination and the scan stays
unambiguous.

Pins (XIAO nRF52840, identical on both halves):

| | pins |
|---|---|
| rows (read, pull-down) | `P0.02` `P0.03` `P0.28` `P0.29` `P0.04` (D0–D4) |
| cols (drive) | `P0.05` `P1.11` `P1.12` `P1.13` `P1.14` (D5–D9) |
| spare | `P1.15` (D10) |

## The split transform — two 25-key halves → one 50-key keymap

A ZMK split does **not** keep two separate 25-key maps. Both halves join into one
logical matrix that the **central** applies:

```
logical columns:   0   1   2   3   4  | 5   6   7   8   9
                 └─ RIGHT (central) ─┘ └─ LEFT (peripheral) ─┘
                    no offset             col-offset = 5
```

- `thumbdeck.dtsi` defines a **50-position** transform (`columns=10, rows=5`) and
  the 5×5 kscan.
- The central (right) uses logical cols 0–4 with no offset.
- The peripheral (left) sets `col-offset = <5>` in `thumbdeck_left.overlay`, so
  its local cols 0–4 land in logical cols 5–9. ZMK applies the split offset to
  the **peripheral**, which is why the per-row keymap order is **right-then-left**.

> This is a deliberate correction of PROJECT_SPEC's "transform sized to 25
> keys/half": a literal per-half 25-key transform won't build a working split.

## Keymap ↔ render consistency

`matrix_map.py` reconstructs the expected 50-binding order from the render
legends (`deck.py`) and asserts it equals the ZMK `default_layer` bindings, so
the silk labels and the firmware can't silently diverge. Current status:
**CONSISTENT** (50/50).

## Diode direction sanity

`diode-direction = "col2row"` in the `.dtsi` must match the physical diode
orientation on the PCB (cathode toward the row). When you place the real
footprint in KiCad, keep every diode's cathode oriented the same way and toward
the row net.
