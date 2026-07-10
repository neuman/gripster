# thumbdeck — wireless split thumb keyboard for a phone

Turn a phone into a handheld work deck. The phone **MagSafe-mounts in the centre**;
two ergonomic grips flank it, and you **thumb-type on metal snap-dome keys** — a
full QWERTY split down the middle, like a [Rii i8+](references/rii8_ref.png) cut in
half and wrapped around a [Backbone](sketches/)-style controller. **One certified
nRF52840 module** in the right grip runs everything over **BLE**; the left grip is a
passive matrix wired across a fixed internal bridge.

![thumbdeck product view](renders/product.png)

> **This is a design in progress, not a finished board.** The layout, a real
> netlisted KiCad board, the diagrams and the BOM are here and were put through a
> 5-lens EE + product-design review (**v0.8**). Before a fab order you still need to
> **route the copper**, drop in the **module/connector/power footprints**, and
> settle a handful of **open ergonomic questions** (§[Open questions](#open-questions)).

---

## At a glance

| | value |
|---|---|
| Form | phone in **LANDSCAPE**, MagSafe-mounted centre, two dome-key grips, **fixed one-piece shell** (~287 mm wide, Steam-Deck-style) |
| Keys | **79 Snaptron 7 mm snap domes** · **9.5 mm** ortholinear pitch (~1.5 mm walls → PETG-printable) · one-piece living-hinge keymat with a **2u space bar**/side |
| Left grip | QWERT-half (6×6) + **4-way D-pad + OK** + **mouse L/R** buttons |
| Right grip | YUIOP-half (6×6) + **PgUp/PgDn** + a **PCB-integrated capacitive trackpad** (~34×26 mm copper + Azoteq IQS7211E controller, fits the grip) |
| Controller | **one Ebyte E73-2G4M08S1C** (nRF52840 module, JLC C356849) — certified radio, on-module antenna/crystals/DC-DC/UF2, ~48 GPIO |
| Matrix | single **9 × 10**, `col2row`, one **SOD-323** diode/key on the back, NKRO best-effort |
| Left grip wiring | passive matrix over a **static internal harness** (JST-GH, signals only, ground-interleaved) |
| Grip size | **74.5 × 109.5 mm** each — battery in the spine keeps them from dwarfing the ~72 mm phone (~18 mm overhang/side) |
| Power | **LiPo inside the spine, directly behind the MagSafe ring** (between the shells; the N52 ring is applied to the outside of the front shell); **MCP73831 charger** + **USB-C** + **USBLC6-2 ESD** in the right grip |
| Wireless | BLE HID (keyboard [+ pointer if trackpad kept]); USB-C for charge + flashing |
| Fabrication | **JLCPCB** turnkey, 2 boards panelized, 1.6 mm FR-4, **ENIG**, all reflow parts on the **back** (single-sided) → **~$150–230 for 5 sets** |
| Firmware | **ZMK** unibody shield (not a split); `CONFIG_ZMK_POINTING` only if the trackpad is kept |

> **Why a module, not chip-down:** a bare nRF52840 would force you to own a 2.4 GHz
> match + VNA tuning, **FCC/IC/RED radiated certification**, a USB bootloader, DC-DC +
> crystals, and a from-scratch Zephyr board port. A pre-certified module retires all
> of that and still breaks out ~48 GPIO (we need ~23). We use the **Ebyte E73** (not
> the Raytac MDBT50Q) because it's stocked in the JLCPCB library and machine-places —
> see [`docs/fabrication-sourcing.md`](docs/fabrication-sourcing.md). Full decision
> record in [`docs/design-decisions.md`](docs/design-decisions.md).

---

## The diagrams

Everything below is generated from one parametric model
([`hardware/scripts/deck.py`](hardware/scripts/deck.py)) — regenerate with the
[design loop](#reproduce-the-design).

### Product view — the whole thing

![Product view](renders/product.png)

Phone landscape in the centre on the MagSafe ring; left grip = QWERT half + D-pad/OK +
mouse buttons; right grip = YUIOP half + PgUp/PgDn + a PCB-integrated trackpad, with
the Ebyte module, power front-end in the grip and the LiPo in the spine.

### Assembly layers — top of the stack → bottom

Five renders on an **identical canvas** (2400×1050) that overlay pixel-for-pixel or
flip through as an animation. Scrolling down peels the device from the front face to
the back. Generate with `python3 hardware/scripts/render_layers.py`.

**5 · Front shell** — key openings, phone + trackpad windows, screw holes, and the
MagSafe N52 ring applied on top.

![Front shell](renders/layer_5_front_shell.png)

**4 · Keymats** — the one-piece printed keycaps joined by living-hinge strips.

![Keymats](renders/layer_4_keymats.png)

**3 · PCB front** — dome pads, vertical **column** traces, inner-margin row feeders,
the PCB-integrated trackpad copper, and the meander antenna.

![PCB front](renders/layer_3_pcb_front.png)

**2 · PCB back** — a diode behind every dome, the Ebyte module / charger / USB-C /
IQS7211E, and horizontal **row** traces. Layers join only through vias — no crossings.

![PCB back](renders/layer_2_pcb_back.png)

**1 · Back shell** — the case, screw bosses, the MagSafe + LiPo pockets in the spine,
and the USB-C cutout.

![Back shell](renders/layer_1_back_shell.png)

### Per-grip layout

![Layout, both grips](renders/iter_09.png)

Ortholinear 6-col grid at 9.5 mm per grip (bottom row = a 2u space bar), plus the cluster features.

### Fabrication view + real KiCad board

![Fabrication view](renders/fab_view.png)

The generated boards are **real, openable, netlisted KiCad files** —
[`hardware/kicad/generated/thumbdeck_right.kicad_pcb`](hardware/kicad/generated/thumbdeck_right.kicad_pcb)
(37 domes + 37 diodes) and `thumbdeck_left.kicad_pcb` (42 + 42) — with the board
outline, mount cutouts, a **real Snaptron dome footprint** at every key, a **real
SOD-323 diode on the back** under each dome, the **matrix nets** (ROW0–8 / COL0–9)
so the ratsnest is correct, and reserved keep-outs for the module / power / bridge /
trackpad. Rendered to front/back SVGs per grip
([`thumbdeck_right_front.svg`](renders/thumbdeck_right_front.svg) etc.). **Copper
routing + the module/connector/power footprints are the remaining gate.**

Like the i8+: the **front** carries only the snap-dome pads, the PCB-integrated
trackpad copper, and the vertical **column** traces; the **back** carries everything
soldered — the 79 diodes, the Ebyte module, IQS7211E, charger, USB-C, ESD, passives,
connectors — plus the horizontal **row** traces. Keeping all reflow parts on the back
makes the SMT job **single-sided** (one stencil, one pass), the key cost lever for
turnkey assembly.

---

## Parts list (BOM)

Full BOM in [`docs/bill-of-materials.md`](docs/bill-of-materials.md). **79 keys**,
**one** module, **one** battery.

### Core

| Item | Part | Qty | Notes |
|---|---|---|---|
| Snap dome | **Snaptron 7 mm 4-leg dome** (SnapForce series) | 79 (+spares) | On cross/ring pads. Footprint: [`hardware/footprints/snaptron_7mm_contact_pad.kicad_mod`](hardware/footprints/snaptron_7mm_contact_pad.kicad_mod). |
| Dome retention | Snaptron taped polyimide array **or** 0.2–0.3 mm laser-cut polyimide spacer | 2 | **Required** — the keymat alone won't stop a dome walking off its ~1.4 mm arc contact. |
| Keymat | one-piece 3D print, **TPU 95A** / tough resin | 2 | Living-hinge strips; fatigue-test a coupon >10 k cycles before the full mat. |
| Diode | **1N4148WS SOD-323** (JLC **C2128**, Basic) | 79 | One/key, `col2row`, cathode band → row net, **on the back** (no room front at this pitch). Basic part = free feeder. |
| **Controller** | **Ebyte E73-2G4M08S1C** (nRF52840, JLC **C356849**) | **1** | Certified radio, on-module antenna/crystals/DC-DC, UF2. On the **back** of the right grip. Verify stock + reserve (Extended, X-ray). Backup: Holyiot 18010. |
| Trackpad controller | **Azoteq IQS7211E** (I²C) + **PCB copper pad** (~34×26 mm on the front) | 1 | PCB-integrated (not a module) → **turnkey-friendly** (copper is free, chip reflows on the back). Fits the grip. Needs the community Azoteq ZMK input driver. |
| **LiPo** | single cell ~400–700 mAh | 1 | Right grip. Sleep-managed runtime is weeks; size to grip thickness. |
| **Bridge connector** | **JST-GH 1.25 mm, ≥15 pos** (×2) + harness | 1 set | Static internal, **signals only**, ground-interleaved. Not a slide/ZIF FFC. |

### Power / USB front-end (right grip — required even with a module)

| Item | Part | Qty | Notes |
|---|---|---|---|
| Charger IC | **MCP73831T-2ACI/OT** (JLC **C424093**; PROG for ≤0.5 C) | 1 | Module has no charger. Don't sub -2ATI (different Vreg). |
| USB-C receptacle | **fully-SMD 16P** (JLC **C165948**) + **2× 5.1 kΩ** CC1/CC2 | 1 | Must be SMD — a THT shell breaks 100 % reflow. Missing CC = never charges. |
| ESD array | **USBLC6-2SC6** (JLC **C7519**) on D+/D−/VBUS | 1 | |
| Battery sense | 2× 1 MΩ divider (÷2) + 10 nF | 1 | Tap the true cell node; ~40 µs SAADC acquire. |
| SWD pads | Tag-Connect TC2030 or 5-pad header | 1 | One-time bootloader flash / recovery. |

### Matrix hardening (both grips)

| Item | Part | Qty | Notes |
|---|---|---|---|
| Row pull-downs | 4.7 kΩ 0402 | 9 | External at the MCU — the nRF's internal pull is too weak over the harness. |
| Column series R | 100–330 Ω 0402 | 10 | Slow edges, kill ringing. |
| Dome-field ESD | low-C TVS on row-sense lines + guard ring | — | Exposed dome metal is an ESD path into GPIO. |

### PCB / hardware

| Item | Spec | Qty | Notes |
|---|---|---|---|
| PCB | `thumbdeck_right` + `thumbdeck_left`, 1.6 mm FR-4, **ENIG** | ~5 each | Selective hard gold on dome pads for production. Two distinct boards. |
| Shell | top + bottom, **MagSafe N52 ring** + alignment magnet, phone **edge-capture** on 2+ edges | 1 | MagSafe = alignment; mechanics take the load. |
| M2 hardware | screws + heat-set inserts | ~6 | 3 mount holes/grip. |

---

# Build guide

Path: **finish routing + footprints → order boards → laminate domes → assemble →
bring-up → flash → pair.** Full detail in [`docs/assembly.md`](docs/assembly.md).

## Step 1 — Finish the board, then order

The generated boards carry the correct **outline, dome + diode placement, matrix
nets and keep-outs**. Remaining before gerbers:

1. **Drop in real footprints** for the Ebyte E73 module, SMD USB-C, JST-GH, charger,
   ESD and passives (switches/diodes are already placed) — **all on the back** so the
   SMT job stays single-sided.
2. **Route** the matrix + power + bridge; pass **DRC + ERC** (needs KiCad 8 GUI or
   `kicad-cli` ≥ 8 — this repo's toolchain is 7.0, which has no DRC CLI).
3. **Order — JLCPCB turnkey PCBA**, both boards **panelized into one panel**, 1.6 mm
   FR-4, **ENIG** (snap domes need gold — HASL oxidises within weeks of cycling),
   single-sided assembly. The fab places ~95–100 % of the joints; you press the 81
   domes under the retention sheet and close the shell. **~$150–230 for 5 sets** —
   full costing, part numbers and the JLC-vs-PCBWay call in
   [`docs/fabrication-sourcing.md`](docs/fabrication-sourcing.md).

## Step 2 — Domes, retention, keymat

- Lay the **polyimide dome-retention** layer over the gold pads (pockets locate each
  7 mm dome; holes clear the actuator).
- Print the **keymat** in TPU 95A; validate boss travel + hinge fatigue on a 3×3
  coupon **before** committing the full mat.

## Step 3 — Solder & assemble

- **Both grips:** 79 domes are mechanical (no solder); reflow the **79 SOD-323
  diodes on the back**, row pull-downs, column series R.
- **Right grip:** Raytac module, MCP73831 + USB-C (with the 2× 5.1 kΩ CC), USBLC6-2,
  battery divider, LiPo (**polarity!**), Cirque trackpad on I²C + DR-IRQ.
- **Bridge:** JST-GH at each grip's inner-bottom; ground-interleaved harness, strain
  relieved. **No power crosses the bridge** — the cell lives with the MCU.

## Step 4 — Bring-up, flash, pair

- **Bring-up first:** BAT+↔GND open (no short); current-limited first power draws a
  few mA not the limit; confirm the module rail; **USB-C actually charges** (CC
  check). Never charge unattended.
- **Flash:** ZMK CI builds a single `thumbdeck` UF2. If the module shipped with the
  Adafruit UF2 bootloader, double-tap reset → drag the `.uf2`; else SWD-flash once.
- **Pair:** host pairs to **"thumbdeck"** (no inter-half pairing). Type across both
  grips — a dead **column** on the left → suspect the harness; a dead **row** hits
  **both** grips (rows shared). Confirm trackpad pointer + mouse buttons + battery %.

---

## How it works

```
  LEFT grip (passive)                    RIGHT grip (MCU)
  43 domes + diodes  ── JST-GH harness ──  Raytac nRF52840 module  ⇄ phone (BLE HID)
  D-pad/OK, mouse      signals only         + LiPo + charger + USB-C + Cirque trackpad
  (no chip/battery)                         scans the whole 9×10 matrix
```

- **One matrix, not a split.** A single 9×10 matrix scanned by one module. Right grip
  = COL0–4 (local); left grip = COL5–9 (over the harness); ROW0–8 shared. This is a
  ZMK **unibody** kscan — *not* `CONFIG_ZMK_SPLIT`. [`docs/matrix-and-diodes.md`](docs/matrix-and-diodes.md).
- **GPIO budget ~23:** 19 matrix + 2 I²C + 1 Cirque DR-IRQ + 1 battery ADC. The
  module's ~48 GPIO covers it with margin (this is what killed the pin-starved
  nice!nano and forced a full-pinout module).
- **Power all in the right grip:** keeping the cell with the MCU means only logic
  signals cross the bridge (a cell across thin harness copper is a chafe-to-short
  fire + undercharge risk). Balance the left grip with passive ballast.
- **Antenna:** on the Raytac module, at the outer-top corner, **≥15 mm from the
  MagSafe magnet ring + steel plate** in 3D. Expect the phone + hand to detune range.

**More docs:** [design decisions + review](docs/design-decisions.md) ·
[fabrication & sourcing](docs/fabrication-sourcing.md) ·
[connectivity & power](docs/connectivity-and-power.md) ·
[matrix & diodes](docs/matrix-and-diodes.md) · [assembly](docs/assembly.md) ·
[i8+ reference notes](docs/reference-notes.md)

---

## Open questions

The EE/PD review flagged decisions that are **yours to make** — they change the
shape of the build:

1. **Feel.** Pitch is now **9.5 mm** (v0.13, for PETG-printable walls + i8+ comfort).
   Still an open call: a flat ortho grid vs a **canted/fanned arc** to feel more like a
   controller — the arc is a keymat/standoff change, not a pitch change.
2. **Phone-fit window.** A fixed shell fits a **~15 mm width band (~145–160 mm)** —
   effectively one phone family (a Pro Max won't fit, a mini wobbles) unless you add
   a stick-on MagSafe ring. Deferring the telescoping bridge forecloses multi-phone.
3. **NKRO vs simplicity.** BLE boot protocol is 6KRO anyway; if true NKRO isn't
   needed, dropping diodes enables a TCA8418-class local scanner that collapses the
   bridge to ~4 wires. Diodes buy clean modifier combos regardless.
4. **Shoulder buttons** for index fingers (offload thumb modifiers)? Changes the
   matrix + conductor count.
5. **Cell size** — with a sleep-managed trackpad, runtime is weeks; a 400–500 mAh
   cell may pack better than 700 mAh.

---

## Reproduce the design

```bash
cd hardware/scripts
python3 render_product.py             # whole-assembly view   -> renders/product.png
python3 render_layers.py              # 5 stackable layers     -> renders/layer_*.png
python3 layout_gen.py     --iter 9    # per-grip layout        -> renders/iter_09.png
python3 render_fab.py                 # fabrication view        -> renders/fab_view.png
python3 gen_kicad_pcbnew.py           # REAL netlisted board    -> hardware/kicad/generated/*.kicad_pcb
```

Requires Python 3 + `matplotlib`; the board generator needs the **KiCad 7 `pcbnew`
Python module**. The digitized layout lives in
[`hardware/layout/keymat.json`](hardware/layout/keymat.json). The old 50-key /
nice!nano design-loop scripts (`gen_kicad.py`, `render_wiring.py`, `grade.py`, …)
are archived in [`hardware/scripts/legacy/`](hardware/scripts/legacy/).

---

## License

MIT — see [LICENSE](LICENSE).
