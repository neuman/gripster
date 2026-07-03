# hardware/kicad — manual KiCad workflow (SCAFFOLD)

The Section 7 loop produced the converged **placement + board outline**. This is
where that becomes a routed, fabricable board. Steps are manual and **not**
auto-produced (PROJECT_SPEC §10) — no fabricated routing.

## What's already generated for you

`generated/` (from `hardware/scripts/gen_kicad.py`, real geometry):

| file | what |
|---|---|
| `thumbdeck_right.kicad_pcb` / `thumbdeck_left.kicad_pcb` | openable board: Edge.Cuts outline, mount-hole cutouts, keep-out rects (controller/LiPo/USB-C), and a placement cross + `SWn`/`Dn` ref at every converged key centre |
| `thumbdeck_*_outline.dxf` | board edge only, importable into KiCad/CAD |
| `thumbdeck_*_placement.csv` | `ref, value, x_mm, y_mm, rotation, side` for every switch, diode, keep-out |

> The switch footprint in these files is **provisional** (marked on silk). Verify
> it before routing — see `hardware/footprints/README.md`.

## Manual steps to a fab package

1. **Schematic** (`thumbdeck.kicad_sch`): 25 switches + 25 diodes (1N4148W,
   `col2row`) + nRF52840 module + LiPo connector (+ optional power switch), per
   half. Wire the 5×5 matrix on the pins in `docs/matrix-and-diodes.md`.
2. **Assign footprints:** SOD-123 for diodes (standard); the **datasheet-verified**
   switch footprint; the XIAO nRF52840 module footprint; a JST/solder LiPo pad.
3. **Layout:** open the generated `.kicad_pcb` (or import the DXF outline). Place
   each switch at its `SWn` cross, diodes at the `Dn` guides, the controller/LiPo
   in their keep-outs, USB-C at the bottom-edge keep-out. Keep the inner edge flat
   (clamp mating reference) and the 2 inner mount holes clear.
4. **Route** the matrix (rows one layer, cols the other is the easy start), power,
   and USB. Pour grounds. Run **DRC**.
5. **Export gerbers + drill**, generate the JLCPCB fab package (1.6 mm, HASL).
   Optional: BOM + centroid for PCBA.

## Notes

- KiCad is not installed in the generation environment, so the `.kicad_pcb` is
  hand-authored (outline + placement only). Opening it in KiCad 7/8 and running
  DRC is the first thing to do.
- Central = right, peripheral = left by default (firmware decides via which
  shield you flash; the two boards are mirror images).
