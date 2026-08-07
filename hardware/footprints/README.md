# hardware/footprints — thumbdeck footprint library (rev-A)

`thumbdeck.pretty/` is the library the board generator loads (alongside the stock
KiCad libraries). The custom footprints below are **as-fabricated** — they are on
the routed, DRC-clean boards and were verified against manufacturer drawings in
2026-07 (the 20-way ZIF in 2026-08). Do not edit them casually: `gen_board.py` and
the routed `.kicad_pcb` files depend on their exact geometry.

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

## `ffc_afa07_s20fcc` — the bridge ZIF (current, v0.27)

JUSHUO **AFA07-S20FCC-00** (LCSC **C262352**, JLC **Extended**): FFC/FPC ZIF,
**1.0 mm pitch, 20 positions, side entry, BOTTOM contacts**, slide-lock drawer,
2.5 mm tall, 0.3 mm FFC, tin plating. Land pattern per the customer drawing —
same family rule as the 16-way (nail pad = `(N−1)/2 × pitch + 2.35`): 20×
0.6×1.8 mm pads at 1.0 mm + 2 nail pads 2.6×3.0, land 26.85 mm long. One per
grip, on the inner edge at deck y **28.5**, cable opening toward the spine.
Mates with a **20-way, 1.0 mm pitch, TYPE-A (contacts on the SAME side at both
ends)** jumper, **≥240 mm** (the v0.24 clamp span is variable, so the ribbon
carries a rolling service loop) — the left grip's pin→net assignment is generated
from ribbon geometry, so the straight jumper is correct by construction.

Since v0.27 this ribbon carries the **battery as well as the matrix**: the four
extra conductors over the 16-way are `NC | VBAT_CELL | VBAT_CELL | NC`, which is
what deleted the separate 2-wire power cable. Two consequences the geometry
alone won't tell you:

- **Buy 20-way, and buy TYPE-A. Do not use a leftover 16-way ribbon.** A 17.0 mm
  16-way ribbon drops into this 21.0 mm housing with **4.0 mm of independent slop
  at each end** — up to a 4-position shift. The conductor order is chosen so the
  worst achievable shift lands VBAT on a *column* (one dead MCU pin) rather than
  on GND (a dead cell short), but that is a last line of defence, not a licence.
  The silk names the width and the type for the same reason.
- **The cell path is fused on the cell side** (F1, a 0.75 A-hold PPTC on the left
  board) because a 1.0 mm-pitch FFC conductor is only 0.0245 mm² — see
  [`docs/design-decisions.md`](../../docs/design-decisions.md).

## `ffc_afa07_s16fcc` — the rev-A 16-way ZIF (superseded, KEPT)

JUSHUO **AFA07-S16FCC-00** (LCSC C13744): the same connector in **16 positions**,
16× 0.6×1.8 mm pads + 2 nail pads, land 22.85 mm long. Superseded by the 20-way
above in v0.27 and **kept on purpose** — the committed rev-A boards reference this
file and must keep loading. It is not what a current build orders.

## `msk12c02_slide` — the power switch

SHOU HAN **MSK12C02** SPDT slide (LCSC C431540): body 8.0×2.8×1.4 mm, knob
protrudes ~1.5 mm from the −y face, 1.6 mm travel. Land per the manufacturer
drawing: 3 signal pads (**pin 2 = common**) + 4 mechanical lug pads + 2× Ø0.85
NPTH locating holes. Wired between cell+ and the VBAT rail; the knob passes
through the 8×2.8 slot in the top shell wall (v0.17 moved the electronics cluster
and its shell openings to the top zone).

## Also in the library

| Footprint | Use |
|---|---|
| `nRF52840_E73-2G4M08S1C` | Ebyte E73 module — 13×18 mm, 43 pads (28 castellated + 15 inner, 1.27 mm), **antenna keep-out embedded** (all-layer, crosses the board edge as placed). Pad N = Ebyte datasheet pin N; from marbastlib (see `marbastlib-LICENSE`), verified against the Ebyte User Manual. |
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | full-SMD 16P USB-C (C165948). |
| `snaptron_7mm_simple` | historical 2-pad routing proxy — **not for fab**. |
| `CON_JST_ACH_BM02B` | unused spare (JST ACH 2-pos); the battery connector is the stock-library JST-PH `S2B-PH-SM4-TB` — **J4 on the LEFT board** since v0.27 (it was J3 on the right). |
| `../snaptron_7mm_contact_pad.kicad_mod` | earlier standalone draft of the contact footprint, superseded by `thumbdeck.pretty/snaptron_7mm_contact`. |
