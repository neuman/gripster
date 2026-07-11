# hardware/footprints — thumbdeck footprint library (rev-A)

`thumbdeck.pretty/` is the library the board generator loads (alongside the stock
KiCad libraries). The three custom rev-A footprints below are **as-fabricated** —
they are on the routed, DRC-clean boards and were verified against manufacturer
drawings in 2026-07. Do not edit them casually: `gen_board.py` and the routed
`.kicad_pcb` files depend on their exact geometry.

## `snaptron_7mm_contact` — the production snap-dome footprint

For the Snaptron 7 mm 4-leg dome (SnapForce), pressed (not soldered) onto the pads:

- **Pad 1 = centre contact, Ø2.86 mm** (Snaptron P1 spec) — the column net.
- **Pad 2 = leg ring, 4.4–6.9 mm dia** (T1/W1/N1), drawn as **13 overlapping
  circles spanning 292°** with a **67.5° escape gap** at +y — the corridor the
  column trace uses to reach the centre pad. Worst-case dome rotation keeps
  **3 of 4 legs on the ring**.
- Full solder-mask apertures over both contacts (bare metal for the dome).
- **F.Cu keepout r 3.8:** tracks allowed (they're mask-covered) but **no vias, no
  pour**; plus an **all-layer via keepout r 3.6** — a tented-via bump under the
  dome seat breaks contact, and Freerouting only honours via keepouts that cover
  every layer.
- **No vent hole** — venting comes from the Snaptron retention-tape channels.
- Ring circle angles must match `RING_ANGLES` in `gen_board.py`.

Why not two simple pads: a dome rotated ~45° on the old 2-pad proxy
(`snaptron_7mm_simple`, kept for reference only) lands legs off-copper → **dead
key**. The continuous ring makes rotation irrelevant.

> **Surface finish: ENIG is mandatory.** An old note here claimed HASL was fine —
> that was written for the abandoned soldered-tact-switch design and is **wrong**
> for snap domes: they press on bare pads, and HASL oxidises into rising contact
> resistance within weeks of key cycling. Order ENIG; hard gold is a
> production-volume upgrade only.

## `ffc_afa07_s16fcc` — the bridge ZIF

JUSHUO **AFA07-S16FCC-00** (LCSC C13744): FFC/FPC ZIF, **1.0 mm pitch, 16
positions, side entry, BOTTOM contacts**, slide-lock drawer, 2.5 mm tall. Land
pattern per the customer drawing: 16× 0.6×1.8 mm pads at 1.0 mm + 2 nail pads
2.6×3.0. One per grip, on the inner edge, cable opening toward the spine. Mates
with a **150 mm 16-way type-A** (same-side contacts) jumper — the left grip's
pin→net assignment is generated from ribbon geometry so the straight jumper is
correct by construction.

## `msk12c02_slide` — the power switch

SHOU HAN **MSK12C02** SPDT slide (LCSC C431540): body 8.0×2.8×1.4 mm, knob
protrudes ~1.5 mm from the −y face, 1.6 mm travel. Land per the manufacturer
drawing: 3 signal pads (**pin 2 = common**) + 4 mechanical lug pads + 2× Ø0.85
NPTH locating holes. Wired between cell+ and the VBAT rail; the knob passes
through the 8×2.8 slot in the bottom shell wall.

## Also in the library

| Footprint | Use |
|---|---|
| `nRF52840_E73-2G4M08S1C` | Ebyte E73 module — 13×18 mm, 43 pads (28 castellated + 15 inner, 1.27 mm), **antenna keep-out embedded** (all-layer, crosses the board edge as placed). Pad N = Ebyte datasheet pin N; from marbastlib (see `marbastlib-LICENSE`), verified against the Ebyte User Manual. |
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | full-SMD 16P USB-C (C165948). |
| `snaptron_7mm_simple` | historical 2-pad routing proxy — **not for fab**. |
| `CON_JST_ACH_BM02B` | unused spare (JST ACH 2-pos); the battery connector on the board is the stock-library JST-PH `S2B-PH-SM4-TB`. |
| `../snaptron_7mm_contact_pad.kicad_mod` | earlier standalone draft of the contact footprint, superseded by `thumbdeck.pretty/snaptron_7mm_contact`. |
