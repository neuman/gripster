# thumbdeck — custom wireless split thumb keyboard

A two-piece, **wireless, rechargeable**, thumb-typed keyboard. Two grip-shaped
PCBs clamp on either side of a phone like a **Backbone One**, reproducing an
**i8+-inspired** QWERTY split down the middle. **One nRF52840** (nice!nano v2)
in the right grip runs the whole thing over **ZMK**; the left grip is a passive
matrix wired across the telescoping bridge.

![thumbdeck layout](renders/production.png)

## Status: v0.3 layout converged & graded — PASS

The autonomous generate→render→grade loop converged with **functional 100%
(17/17)** and **visual 8/8**. See [`renders/GRADING.md`](renders/GRADING.md).

| | value |
|---|---|
| Per-grip board | **63 × 108 mm**, 25 keys (5×5), D-shaped grip |
| Controller | **one nice!nano v2** (nRF52840) in the right grip |
| Left grip | **passive** 5×5 matrix, wired over the bridge (10 conductors) |
| Firmware | ZMK, single non-split shield `thumbdeck` on `nice_nano_v2` |
| Matrix | single 5×10, `col2row`, 1N4148W diodes |
| Wireless | BLE, or USB-C wired HID — one device, no inter-half pairing |
| Power | one LiPo, one USB-C charge |

> **Architecture note (v0.3):** this replaces v0.2's two-controller BLE split
> with a single controller + a wired bridge — how real Backbone-style controllers
> actually work. Simpler in every dimension (one battery, one charge, half the
> BOM, simpler firmware). Rationale in
> [`docs/design-decisions.md`](docs/design-decisions.md).

## What's in here

```
docs/            design decisions, connectivity/power, matrix, BOM, assembly, i8+ reference
hardware/
  scripts/       deck.py (geometry) · layout_gen.py (render) · grade.py + final_grade.py
                 (grading) · gen_kicad.py (board) · matrix_map.py (planning aid)
  kicad/         manual KiCad workflow (SCAFFOLD) + generated/ board outline + placement
  footprints/    datasheet-verified switch footprint (TODO)
renders/         iter_NN.png loop history · production.png · fab_view.png ·
                 wiring_schematic.png (matrix) · wiring_assembly_{left,right}.png
                 (solder pads + bridge pinout) · thumbdeck_soldermap.pdf
                 (1:1 printable, lay parts on it) · GRADING.md
firmware/
  zmk-config/    single ZMK shield "thumbdeck" + build.yaml + CI
.github/         GitHub Actions ZMK build
```

## Reproduce the loop

```bash
cd hardware/scripts
python3 layout_gen.py --iter 5      # render both grips -> renders/iter_05.png
python3 grade.py       --iter 5      # objective functional grade (17 checks)
python3 final_grade.py --iter 5      # combined functional + visual verdict
python3 matrix_map.py                # legends <-> ZMK keymap consistency
python3 gen_kicad.py                 # emit .kicad_pcb + DXF + placement CSV
python3 render_fab.py                # fabrication-view sanity render
```
Requires Python 3 + `matplotlib` (no KiCad needed to render or generate the board file).

## Build the firmware

Push and let **GitHub Actions** (`.github/workflows/build.yml`) build one
`thumbdeck` image for `nice_nano_v2`. Drag the `.uf2` onto the (single) nice!nano
in bootloader mode. See [`docs/assembly.md`](docs/assembly.md).

## Before you send boards to a fab — two open `TODO(user)` gates

Per PROJECT_SPEC §5/§10/§13, this handoff does **not** fabricate what it can't
verify:

1. **Datasheet-verified switch footprint** — the generated board marks switch
   placement with a *provisional* footprint. See
   [`hardware/footprints/README.md`](hardware/footprints/README.md).
2. **Copper routing** — open `hardware/kicad/generated/thumbdeck_right.kicad_pcb`
   (MCU board) and `thumbdeck_left.kicad_pcb` (passive), assign the verified
   footprints, route the matrix + bridge connector, export gerbers. See
   [`hardware/kicad/README.md`](hardware/kicad/README.md).

Everything upstream — layout, envelope, keep-outs, mount/bridge features,
firmware, BOM — is done and graded.

## License

MIT — see [LICENSE](LICENSE).
