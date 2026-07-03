# thumbdeck — custom wireless split thumb keyboard

A two-piece, **wireless, rechargeable**, thumb-typed keyboard. Two grip-shaped
PCB halves clamp on either side of a phone like a **Backbone One**, reproducing
an **i8+-inspired** QWERTY split down the middle. Each half is self-contained:
its own **nRF52840** controller, LiPo, and USB-C. The halves talk over **BLE**
(no cable between them) and run **ZMK**.

![thumbdeck layout](renders/production.png)

## Status: layout converged & graded — PASS

The autonomous generate→render→grade loop (PROJECT_SPEC §7) converged at
iteration 3 with **functional 100% (16/16)** and **visual 8/8**. See
[`renders/GRADING.md`](renders/GRADING.md) for the rubric and iteration log.

| | value |
|---|---|
| Per-half board | **63 × 108 mm**, 25 keys (5×5), D-shaped grip |
| Controller | XIAO nRF52840 (default) · nice!nano v2 alt |
| Firmware | ZMK split — right = central, left = peripheral |
| Switches | Xiaoyztan 5×5×1.5 mm SMD tact (owned), 1N4148W diodes, `col2row` |
| Wireless | BLE split + USB-C wired HID on the central |

## What's in here

```
docs/            design decisions, connectivity/power, matrix, BOM, assembly, i8+ reference
hardware/
  scripts/       deck.py (geometry) · layout_gen.py (render) · grade.py + final_grade.py
                 (grading) · gen_kicad.py (board) · matrix_map.py (planning aid)
  kicad/         manual KiCad workflow (SCAFFOLD) + generated/ board outline + placement
  footprints/    datasheet-verified switch footprint (TODO)
renders/         iter_NN.png loop history · production.png · fab_view.png · GRADING.md
firmware/
  zmk-config/    ZMK split shield "thumbdeck" (_left + _right) + build.yaml + CI
.github/         GitHub Actions ZMK build
```

## Reproduce the loop

```bash
cd hardware/scripts
python3 layout_gen.py --iter 3      # render both halves -> renders/iter_03.png
python3 grade.py       --iter 3      # objective functional grade
python3 final_grade.py --iter 3      # combined functional + visual verdict
python3 matrix_map.py                # legends <-> ZMK keymap consistency
python3 gen_kicad.py                 # emit .kicad_pcb + DXF + placement CSV
python3 render_fab.py                # fabrication-view sanity render
```
Requires Python 3 + `matplotlib` (no KiCad needed to render or generate the board file).

## Build the firmware

Push this repo and let **GitHub Actions** (`.github/workflows/build.yml`) build
`thumbdeck_left` and `thumbdeck_right` for `seeeduino_xiao_ble`. Artifacts are
`.uf2` files — drag onto each half in bootloader mode. See
[`docs/assembly.md`](docs/assembly.md).

## Before you send boards to a fab — two open `TODO(user)` gates

Per PROJECT_SPEC §5/§10/§13, this handoff does **not** fabricate what it can't
verify. Two steps remain before gerbers:

1. **Datasheet-verified switch footprint** — the generated board marks switch
   placement with a *provisional* footprint. Verify real pad geometry against
   the Xiaoyztan part. See [`hardware/footprints/README.md`](hardware/footprints/README.md).
2. **Copper routing** — open `hardware/kicad/generated/thumbdeck_right.kicad_pcb`
   (real outline + placement), assign the verified footprints, route the matrix,
   export gerbers. See [`hardware/kicad/README.md`](hardware/kicad/README.md).

Everything upstream of those two steps — layout, envelope, keep-outs, mount
features, firmware, BOM — is done and graded.

## License

MIT — see [LICENSE](LICENSE).
