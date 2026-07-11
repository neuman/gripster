# hardware/kicad — generated boards + autonomous fab pipeline (rev-A)

Everything in `generated/` is produced headlessly by the pipeline in
`hardware/scripts/`. **Both boards are fully routed and DRC-clean** (0 violations,
0 unconnected, kicad-cli 9.0.9) and the JLC fab package is exported. Nothing here
is hand-drawn; to change the board, change the model/scripts and regenerate.

## The pipeline

```bash
cd hardware/scripts
python3 gen_board.py                  # placement + full netlist + deterministic USB copper
                                      #   + GND escape vias -> generated/thumbdeck_{right,left}.kicad_pcb
./route.sh right                      # Specctra DSN (In1 marked power) -> Freerouting (-Xss16m)
./route.sh left                       #   -> SES import -> stitch.py (GND vias + zone fill) -> DRC -> renders
python3 gen_fab.py                    # gerbers/BOM/CPL per side; REFUSES to export unless DRC is 0/0
python3 sim_matrix.py                 # 79-key matrix ghosting/NKRO proof (final pass)
```

Requirements: **KiCad 9** (`pcbnew` Python module + `kicad-cli`), a Java runtime
and **freerouting.jar** (paths at the top of `route.sh`). Details and quirks in
[`docs/routing-status.md`](../../docs/routing-status.md).

## What's in `generated/`

| file | what |
|---|---|
| `thumbdeck_right.kicad_pcb` / `thumbdeck_left.kicad_pcb` | routed, DRC-clean 4-layer boards (F.Cu / In1 GND plane / In2 / B.Cu) |
| `thumbdeck_*.kicad_pro/.kicad_prl/.kicad_dru` | project + 0.2 mm rules (via 0.6/0.3) |
| `thumbdeck_*.dsn` / `thumbdeck_*.ses` | Freerouting in/out (kept for reproducibility) |
| `drc_right.json` / `drc_left.json` | DRC results: **0 violations, 0 unconnected** (error severity) |
| `fab/right/`, `fab/left/` | **the order package**: `thumbdeck_*_gerbers.zip` + `bom.csv` + `positions.csv` (JLC format) |
| `thumbdeck_*_placement.csv` | placement summary (ref, value, x, y, rot, side) |

## Ordering

Two **separate** JLCPCB PCBA orders (right + left — don't panelize two different
designs): 4-layer, 1.6 mm FR-4, **ENIG (mandatory — snap-dome contacts)**, assembly
side **bottom**, Standard assembly for the right board (E73 = Extended + X-ray),
Economic OK for the left. Check the DFM preview for part rotations (LED polarity,
SOT-23s, USB-C, E73). Full walkthrough:
[`docs/fabrication-sourcing.md`](../../docs/fabrication-sourcing.md).

## Notes

- The boards are frozen build artifacts — regenerate rather than hand-edit; the
  DRC gate in `gen_fab.py` protects the export either way.
- Opening them in the KiCad 9 GUI is fine for inspection; the pipeline does not
  depend on the GUI for anything.
