# Assembly, first flash, charge, pair & test — rev-A (v0.16)

Both boards arrive from JLC **fully assembled** (every soldered part is SMT and
machine-placed) — there is **no hand-soldering** in this build. Your work is
mechanical + one one-time SWD flash.

## 0. Order & print

1. **Boards:** two JLCPCB PCBA orders from `hardware/kicad/generated/fab/` —
   see [fabrication-sourcing.md](fabrication-sourcing.md), including the DFM
   preview checklist (LED polarity!).
2. **Prints:** five PETG shell parts — `back_left`, `back_right`,
   `grip_lid_left`, `grip_lid_right`, `center_panel` — and the two keymats
   (TPU 95A). STLs are tracked in `hardware/cad/models/` (or regenerate to
   `hardware/cad/build/`, STEP alongside). Every part fits a 220 × 220 bed
   (Ender 3 V2) flat; orientations + slicer notes in
   [cad-process.md](cad-process.md). Coupon-test a 3×3 keymat patch for hinge
   fatigue (>10 k presses) before printing the full mats.
3. **Order alongside:** 79+ Snaptron 7 mm domes with the taped retention array,
   a 16-way 1.0 mm **type-A** (same-side contacts) FFC jumper, **length ≥160 mm**
   — 200 mm is the common stock length (e.g. "FFC-1.0-16P-200mm" type A); the J2
   contact rows sit 151.2 mm apart plus ~4 mm ZIF insertion each end, so a 150 mm
   ribbon cannot mate — plus a 1S 400–700 mAh JST-PH LiPo, Ø56 N52 MagSafe ring,
   **16 M2 heat-set inserts + 16 M2×10 button-head screws** (one SKU: 10 grip,
   4 panel-floor, 2 panel-ring).

## 1. Press the domes

Per grip, on the **front** (bare gold) side:

- Wipe the dome pads with IPA; don't touch the gold afterwards.
- Apply the Snaptron **retention array**: pockets locate each 7 mm dome over its
  contact ring; press each dome until it seats flat. The tape's channels vent the
  domes — don't substitute a solid film.
- Sanity-click a few domes with a meter across the centre pad ↔ ring: open at
  rest, closed when pressed.

## 2. Mechanical assembly

Order matters with the split shells: **FFC into the boards first, lids before
panel, panel last** (it overlaps nothing but is the seam splice + service hatch).

1. Heat-set the **16 M2 inserts**: 5 per grip in each back half's PCB bosses,
   2 per half in the panel bosses beside the x=0 seam, and 1 per half in the
   Ø8 boss on the transverse spine wall (all 3.2 mm bores).
2. **FFC jumper first:** with the boards loose, open both ZIF latches and seat
   the ribbon (≥160 mm type-A), **contacts facing the board at both ends** (the
   ZIFs are bottom-contact and the jumper is type-A/same-side — a straight
   ribbon is correct by construction; do not twist it). Close the latches. The
   ZIFs are unreachable once the lids are on.
3. Drop each board in, **parts down**, onto its perimeter bosses + the **3
   support posts** under the key field. Check the USB-C sits in its wall
   opening, the slide-switch knob reaches its slot, and the reset tact + LED
   align with the floor pinhole + light hole.
4. Lay the keymats over the domes and fit each **grip lid** (its rim lightly
   clamps the keymat web); drive the **5 M2×10 screws per grip**.
5. **Join the back halves:** thread the FFC slack through the transverse-wall
   windows, engage the two floor tabs and the wall shiplaps at x=0, and press
   the halves flush. No screws here — the center panel is the splice.
6. **Battery — polarity check first, cell NOT connected yet.** Vendors wire
   JST-PH pigtails **both ways**: meter the pack pigtail and confirm the red/+
   wire lands on the pin marked **"+"** on the back silk beside J3 — that is
   **pin 1, the pin nearer the bottom board edge** ("−" marks pin 2). Seat the
   cell on the spine floor (adhesive on **one half only**, so a future seam
   split doesn't pry the pouch), route the leads through the wall window to J3,
   but leave it **unplugged** and the power switch **OFF** — the cell is
   connected only *after* the first flash (§3); see the REGOUT0 warning there.
7. Seat the **MagSafe ring** in the panel recess (epoxy the full annulus — the
   bond, not the 0.8 mm web, takes the detach pull), then fit the **center
   panel** and drive its **6 M2×10 screws**: 4 in the plateau strips straddling
   the back seam, 2 in the pocket floor at ring height (they sink 1.4 mm — the
   phone clears them). To service battery/FFC later, only these 6 come back out.

## 3. First flash (one-time SWD, then UF2 forever)

The E73 ships **blank** — it cannot be UF2-flashed out of the box.

> **Order matters — first power-up must be battery-free.** Until `UICR.REGOUT0`
> is programmed to 3.3 V, the nRF's I/O rail runs at its **1.8 V** default, and a
> full 4.2 V cell would put the battery divider's **2.1 V on AIN0 — exactly the
> pin's absolute-maximum rating**. So: battery switch OFF and cell unplugged,
> power from USB or the SWD probe only, flash the bootloader (which programs
> REGOUT0 = 3.3 V), and only *then* connect the cell.

1. Connect an SWD probe (J-Link, CMSIS-DAP, or a Raspberry Pi with OpenOCD) to the
   silk-labelled pads **TP1–5**: SWDIO, SWDCLK, RESET, 3V3, GND. Power the board
   from **USB or the probe's 3V3 only** — cell unplugged, switch OFF.
2. If the part arrives access-protected: `nrfjprog --recover` (or the OpenOCD
   equivalent) first.
3. Flash the **Adafruit nRF52 bootloader — nice_nano build** (that build matches
   this board's flash layout; the board itself is *not* a nice!nano). The
   bootloader sets `UICR.REGOUT0 = 3.3 V`, which the LiPo-direct power scheme
   requires — verify the flash completed before going further.
4. **Now connect the cell** (polarity already metered in §2) and switch ON —
   **ON = knob toward the USB-connector end of the board**.
5. From now on it's drag-and-drop: **double-tap reset** (paperclip in the floor
   pinhole) → a UF2 drive mounts → drag on `thumbdeck-zmk.uf2` from the GitHub
   Actions build (`.github/workflows/build.yml`, self-contained ZMK v0.3.0).

## 4. Power-on checkpoints

1. Switch ON (knob toward the USB end of the board): BLE advertising should start
   (see the host's scanner). Idle draw on
   a bench meter: single-digit mA advertising, dropping toward µA in deep sleep.
2. Plug USB-C: the **charge LED** in the floor lights; it goes out when full.
   The cell also charges with the switch OFF (charger is on the cell side).
   Never charge unattended.
3. First battery reading on the host should be plausible (÷2 divider on AIN0).

## 5. Pair & test

- Pair the host to **"thumbdeck"**. There is no inter-half pairing — the left grip
  is wired, not a BLE peer.
- Type across **both** grips. Debug map: a dead left-grip **column** → reseat the
  FFC ribbon; a dead **row** affects **both** grips (rows are shared).
- **FN layer** (hold FN): MINUS/EQUAL on 0/9, HOME/END on PgUp/PgDn, PSCRN on DEL,
  `BT_CLR` + `BT_SEL 0–3` for profiles, plus `&bootloader` / `&sys_reset`.
- Pointer: D-pad + ZMK mouse keys on the FN layer (no trackpad in v1).
- Chord several keys at once — the diodes kill ghosting (verified exhaustively in
  `sim_matrix.py`, but enjoy confirming it with fingers).
