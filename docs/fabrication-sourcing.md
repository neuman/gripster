# Fabrication & sourcing — rev-A (v0.15)

**Recommendation: JLCPCB turnkey PCBA, two separate orders (right + left), 4-layer,
ENIG, single-sided bottom assembly.** The fab package is already exported — nothing
to draw, route or export yourself:

```
hardware/kicad/generated/fab/right/  thumbdeck_right_gerbers.zip + bom.csv + positions.csv
hardware/kicad/generated/fab/left/   thumbdeck_left_gerbers.zip  + bom.csv + positions.csv
```

Rough cost target **~$150–250 delivered for 5 sets** of both boards assembled
(indicative 2026 figures — **re-quote at order time**; the E73 price and stock move).

## Placing the two orders

For each board: upload the `*_gerbers.zip`, choose PCBA, then upload `bom.csv` and
`positions.csv` (they're already in JLC's column format).

| Option | Right board | Left board |
|---|---|---|
| Layers / material | **4-layer**, 1.6 mm FR-4 | same |
| Surface finish | **ENIG — mandatory** (snap domes press on bare pads; HASL oxidises within weeks of key cycling) | same |
| Assembly | **Standard** (forced: the E73 is an Extended part that needs X-ray inspection) | **Economic** is fine (42 diodes + one FFC connector) |
| Assembly side | **Bottom** (all parts are on the back; the front must stay bare for the domes) | Bottom |
| Panelize? | **No.** Two different designs — panelizing them costs more than two small orders. | No |

### Why two orders, not one panel

Earlier drafts assumed "panelize L+R into one panel, pay setup once". Quoted for
real: a mixed panel of two distinct designs triggers JLC's multi-design surcharges
and a bigger stencil, and the left board no longer shares the right board's Standard
assembly requirement. Two separate orders — the trivial left one on Economic — comes
out cheaper.

## DFM preview checklist (before paying)

Expect one DFM confirmation hold on the right board: **the E73 module body
overhangs the top board edge by ~0.75 mm by design** (its antenna must clear
the PCB). Reply "proceed as designed" — the overhang is intentional and the
shell has a matching wall relief. (v0.17 moved the E73 to the top zone with the
antenna pointing up off the top edge; the shell was regenerated 2026-07-14 — the
relieved top wall stays **closed** at 1.9 mm over the antenna span, so the module
tip has ≥0.5 mm clearance and the antenna radiates through thin PETG, not a hole.)


`gen_fab.py` exports KiCad-native rotations; JLC's library orientation can differ
per part. In the DFM/component preview, verify and rotate if needed:

1. **Charge LED D80 polarity** — the classic JLC 180° flip. Cathode toward the
   MCP73831 STAT side.
2. **SOT-23-5 / SOT-23-6 rotation** (U2 MCP73831, U3 USBLC6-2SC6).
3. **USB-C (J1)** seated on the pad pattern, shell at the board edge.
4. **E73 (U1) orientation** — antenna edge pointing off the top board edge.
5. Confirm every part is placed in the **single-pass SMT assembly** — nothing is
   hand-soldered. (The USB-C shell's plated stakes and the FFC/slide-switch
   locating pegs are the only through-board features, and they go on in the same
   pass; if the preview asks for a separate THT/hand-solder step, something is
   wrong.)

## Key parts (LCSC numbers as ordered)

| Part | LCSC | Tier | Notes |
|---|---|---|---|
| Ebyte E73-2G4M08S1C | **C356849** | **Extended + X-ray, stock VOLATILE** (observed from ~1000 down to ~20 units within days) | **Check jlcpcb.com/parts for C356849 and reserve/backorder the modules BEFORE anything else.** Forces Standard assembly on the right board. Backup: Holyiot 18010 — requires a footprint change (rev-B). |
| USB-C 16P full-SMD | C165948 | Extended | |
| MCP73831T-2ACI/OT | C424093 | Extended | Don't sub -2ATI (different Vreg behaviour). |
| USBLC6-2SC6 | C7519 | Extended | |
| FFC ZIF AFA07-S16FCC-00 | C13744 | Extended | One per board. |
| JST-PH S2B-PH-SM4-TB | C295747 | Extended | |
| MSK12C02 slide switch | C431540 | Extended | |
| TS-1187A reset tact | C318884 | Extended | |
| 1N4148WS SOD-323 | C2128 | **Basic** | 79 across both boards. |
| Red LED 0603 | C2286 | Basic | |
| All R/C (0402/0805) | C25900, C25905, C26083, C11702, C52923, C1525, C1779 | **Basic** | The 4.7 µF is deliberately **0805 25 V** (C1779) — a 0402 4µ7 derates to ~1 µF at 5 V bias. |

## What stays manual (either fab house)

Snap domes are mechanical spring contacts — they oxidise/warp in reflow, so no
house machine-places them. Your steps after delivery: press the **79 domes** under
the Snaptron retention array, print shells + keymats, foam-tape the battery into
the **left grip before its board goes in**, seat the FFC jumper in its floor
channel before the center panel goes on (4 border screws), close the shell.
PCBWay can quote manual dome-sheet application, but it
roughly doubles the cost — pressing them yourself is a calm 20-minute job.

## Cost shape (5× each board, assembled)

Flat fees dominate at qty 5: 4-layer PCB + ENIG, one Standard assembly setup +
stencil (right), one Economic setup (left), Extended-feeder fees, E73 X-ray, parts
(~$6 × 5 for the E73 dominates), shipping. Per-board cost only falls with volume.
**Both orders exclude** the domes + retention array, LiPo, printed parts, M2
hardware and the FFC jumper — see [bill-of-materials.md](bill-of-materials.md).

## Caveats

- **E73 stock is volatile** (~1000 → ~20 units observed within days): check
  jlcpcb.com/parts for **C356849** and **reserve/backorder the modules before
  anything else**. The Holyiot 18010 backup requires a footprint change (rev-B).
- **ENIG is mandatory** — state it explicitly; don't let a quote default to HASL.
- Selective hard gold on dome pads is a production-volume upgrade; plain ENIG is
  fine for a personal build.
- Rotations: trust the DFM preview over the CPL numbers (see checklist above).
