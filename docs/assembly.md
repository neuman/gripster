# Assembly, first flash, charge, pair & test — rev-A (v0.15)

Both boards arrive from JLC **fully assembled** (every soldered part is SMT and
machine-placed) — there is **no hand-soldering** in this build. Your work is
mechanical + one one-time SWD flash.

## 0. Order & print

1. **Boards:** two JLCPCB PCBA orders from `hardware/kicad/generated/fab/` —
   see [fabrication-sourcing.md](fabrication-sourcing.md), including the DFM
   preview checklist (LED polarity!).
2. **Prints:** back shell + front shell (PETG) and the two keymats (TPU 95A) from
   `hardware/cad/build/` (STL for slicing; STEP alongside). Coupon-test a 3×3
   keymat patch for hinge fatigue (>10 k presses) before printing the full mats.
3. **Order alongside:** 79+ Snaptron 7 mm domes with the taped retention array,
   a 16-way 1.0 mm **type-A** (same-side contacts) FFC jumper, **length ≥160 mm**
   — 200 mm is the common stock length (e.g. "FFC-1.0-16P-200mm" type A); the J2
   contact rows sit 151.2 mm apart plus ~4 mm ZIF insertion each end, so a 150 mm
   ribbon cannot mate — plus a 1S 400–700 mAh JST-PH LiPo, Ø56 N52 MagSafe ring,
   M2 heat-set inserts + screws.

## 1. Press the domes

Per grip, on the **front** (bare gold) side:

- Wipe the dome pads with IPA; don't touch the gold afterwards.
- Apply the Snaptron **retention array**: pockets locate each 7 mm dome over its
  contact ring; press each dome until it seats flat. The tape's channels vent the
  domes — don't substitute a solid film.
- Sanity-click a few domes with a meter across the centre pad ↔ ring: open at
  rest, closed when pressed.

## 2. Mechanical assembly

1. Heat-set the **M2 inserts** into the back-shell bosses (3.2 mm bores, 5 per grip).
2. Drop each board in, **parts down**, onto its perimeter bosses + the **3 support
   posts** under the key field. Check the USB-C sits in its wall opening, the
   slide-switch knob reaches its slot, and the reset tact + LED align with the
   floor pinhole + light hole.
3. **FFC jumper:** open both ZIF latches, feed the ribbon (≥160 mm type-A) across
   the spine, **contacts facing the board at both ends** (the ZIFs are
   bottom-contact and the jumper is type-A/same-side — a straight ribbon is
   correct by construction; do not twist it). Close the latches.
4. **Battery — polarity check first, cell NOT connected yet.** Vendors wire
   JST-PH pigtails **both ways**: meter the pack pigtail and confirm the red/+
   wire lands on the pin marked **"+"** on the back silk beside J3 — that is
   **pin 1, the pin nearer the bottom board edge** ("−" marks pin 2). Seat the
   cell in the spine pocket but leave it **unplugged** and the power switch
   **OFF** — the cell is connected only *after* the first flash (§3); see the
   REGOUT0 warning there.
5. Lay the keymats over the domes, seat the **MagSafe ring** in the front-shell
   recess, fit the front shell (its rim lightly clamps the keymat web) and drive
   the 10 M2 screws.

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
