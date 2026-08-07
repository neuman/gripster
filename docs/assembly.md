# Assembly, first flash, charge, pair & test — rev-A (v0.22)

> **This device has never been physically built.** The boards are routed and
> DRC-clean and the shells are fit-checked in CAD, but no first article exists —
> this guide is a design-derived procedure, not a walkthrough of a build that
> actually happened. Expect to find things it does not anticipate.

Both boards arrive from JLC **fully assembled** — every part is machine-placed
SMT (the v0.21 pointing nub's electronics are a single SOT-23-6 hall sensor,
U4, on the same reflow pass as everything else). There is **no soldering by
you** in this build. Your work is mechanical + one one-time SWD flash.

> **Status (superseded by the v0.19 note below):** the boards, fab package and firmware in this guide are the
> re-routed **v0.17** grip (79.5 × 97 mm; the E73 + power front-end — USB-C,
> charger, ESD, power slide switch, reset, charge LED — moved to the **top**
> zone, with the JST-PH battery connector in the bottom chin) — **unchanged in
> v0.18**. The **3D shells and keymats have been regenerated and fit-checked
> for v0.18** (flush-screen sunken tray sized for a cased Galaxy S25 Ultra;
> battery relocated into the left grip) — print from the current STLs.
>
> **2026-07-15 (Rii-follow Enter):** the right board, keymat and shells were
> regenerated for the **Rii-style 2u Enter** ending the right H-row (right grip
> now 36 keys, 78 total; `'` moved to FN+`;`), the right board rerouted
> (still 0/0) and the fab package re-exported — order from the current `fab/`
> files. The keymats now carry debossed keycap legends.
>
> **2026-07-17 (v0.19 GBC rework):** BOTH boards regenerated + re-routed for the
> boxy Game-Boy-Color outline (75.0 × 97 mm, straight outer edge) and the
> **M3 flush-countersunk** face screws; the phone well is closed (end walls +
> finger dish) and the spine is 3.9 mm wider — order boards and print shells
> from the CURRENT fab package + STLs only.
>
> **2026-08-07 (v0.27 — the battery rides the ribbon):** the bridge is now a
> **20-way** 1.0 mm ZIF and four of its conductors carry the cell, so **there is
> no separate battery power cable any more**. The battery connector moved with it:
> **J3 is gone from the right board; the cell plugs into J4 on the LEFT board**,
> ~8 mm from where it sits, through a new **F1** PPTC fuse. Two things this changes
> for you, both safety-relevant: **buy a 20-way TYPE-A ribbon, never a 16-way**
> (§0.3), and **seat the ribbon BEFORE plugging in the cell** (§2) — the power
> switch gates only the load, so the ribbon is live whenever the cell is attached.
> BOTH boards were re-routed 0/0 for this, so order from the CURRENT fab package.

## 0. Order & print

1. **Boards:** two JLCPCB PCBA orders from `hardware/kicad/generated/fab/` —
   see [fabrication-sourcing.md](fabrication-sourcing.md), including the DFM
   preview checklist (LED polarity!). That directory is **not committed**;
   generate it first with `python3 hardware/scripts/gen_fab.py` (it refuses
   unless DRC is 0/0).
2. **Prints:** six PETG shell parts — `back_left` (moving jaw), `back_right`
   (ground), `grip_lid_left`, `grip_lid_right`, the v0.24 `bridge` telescoping
   tray, and the v0.21 nub pair:
   `nub_spring` (Ø14.8 flexure; **its 3 spiral arms are the compliance coupon**
   — print one, flex it by hand, and if it feels dead-stiff or floppy retune
   `NUB_ARM_T` ±0.2 in `deck3d.py` before printing the final) and `nub_cap`
   (**RED TPU 95A**, prints with the keymats — a classic ThinkPad soft-dome
   replica; tune its 4.6 mm square socket ±0.1 to press snug on the spring's
   4.4 mm square platform — or skip it and push on any **genuine classic
   full-size TrackPoint cap**, which shares the same socket standard) — and
   the two keymats **plus the two `gripper_left/right` phone grippers** (all
   TPU 95A). STLs are tracked in `hardware/cad/models/` (or regenerate to
   `hardware/cad/build/`, STEP alongside). Every part fits a 220 × 220 bed
   (Ender 3 V2) flat; orientations + slicer notes in
   [cad-process.md](cad-process.md). Coupon-test a 3×3 keymat patch for hinge
   fatigue (>10 k presses) before printing the full mats.
3. **Order alongside:** 78+ Snaptron 7 mm domes with the taped retention array,
   a **20-way** 1.0 mm **TYPE-A** (contacts on the SAME side at both ends) FFC
   jumper, **length ≥240 mm** (v0.24) — the clamp span is now VARIABLE (the grips
   slide 130–170 mm), so the ribbon carries a **rolling service loop** that folds
   in a channel under the telescoping `bridge` tray and pays out as the jaw moves;
   it must reach at max extension (~195 mm J2-to-J2) plus the fold, so coupon-tune
   the loop radius. **20-way and type-A are both hard requirements, not
   preferences** (v0.27): this ribbon carries the battery as well as the matrix,
   and a 17 mm 16-way ribbon drops into the 21 mm housing with 4 mm of slop at each
   end — up to a 4-position shift, which the pin order survives (VBAT lands on a
   column, one dead MCU pin) only because it was designed to. There is **no
   separate battery power cable to buy any more**. Also: 2 **extension springs**
   (~5–8 N, ≥40 mm working
   extension) for the clamp force, a 1S **403040** pouch LiPo (4.0 × 30 × 40 mm,
   ~450–500 mAh, JST-PH; the footprint is a hard limit — the cell lives inside
   the **left grip**, not the spine) that **must have an integrated PCM**
   (overcurrent 2.0–2.5 A / 8–16 ms, overcharge 4.275 V, overdischarge 2.75 V —
   the board's F1 PPTC and the pack's PCM cover *different* fault bands and
   neither alone is sufficient), 0.3 mm foam tape for the cell, Ø56 N52
   **10 M3 heat-set inserts (OD ≤4.6, ~4 mm) + 10 M3×10 DIN 965
   countersunk screws** (10 grip lids) + **2 short M3** for the bridge-to-grip
   bolts. (DIN 965 = 90° countersunk flat head, flush with the face.)

## 1. Press the domes

Per grip, on the **front** (bare gold) side:

- Wipe the dome pads with IPA; don't touch the gold afterwards.
- Apply the Snaptron **retention array**: pockets locate each 7 mm dome over its
  contact ring; press each dome until it seats flat. The tape's channels vent the
  domes — don't substitute a solid film.
- Sanity-click a few domes with a meter across the centre pad ↔ ring: open at
  rest, closed when pressed.

## 2. Mechanical assembly

Order matters with the split shells: **FFC into the boards first, battery taped
into the left grip before its board, lids before panel, panel last** (it overlaps
nothing but is the seam splice + the FFC service hatch — the battery is
serviced through the left grip, not the panel).

> **v0.27 — the ribbon goes in before the cell, and that is not a preference.**
> SW90 gates only the **load**, so `VBAT_CELL` — and therefore the bridge ribbon —
> is live the moment the cell is plugged into J4. Seat and latch both ZIF ends
> first, then plug J4 (which is only in §3, after the first flash). J4 is also
> your de-energize point for any later service: **unplug J4 before touching the
> ribbon.**

1. Heat-set the **14 M3 inserts** (Ø4.0 bores): 5 per grip in each back half's PCB bosses
   and 2 per half in the panel bosses beside the x=0 seam (all Ø4.0 bores).
   *(The two ring-height spine anchors are gone in v0.18 — the panel takes 4
   border screws only.)*
2. **FFC jumper first:** with the boards loose, open both ZIF latches and seat
   the ribbon (**20-way**, ≥240 mm, type-A), **contacts facing the board at both
   ends** (the ZIFs are bottom-contact and the jumper is type-A/same-side — a
   straight ribbon is correct by construction; do not twist it). Push it fully
   home against both ends of the 21 mm housing and check it is **square in the
   slot with no conductor over-hanging either end** before closing the latches:
   since v0.27 four of these conductors are the battery, and a ribbon seated a few
   positions over is a fault, not a dead key. Close the latches. The
   ZIFs are unreachable once the lids are on. The ribbon will later fold into a
   **rolling service loop** inside the telescoping `bridge` tray that pays out as
   the clamp jaw slides (step 6).
   Note the ribbon does **not** leave the ZIF toward the spine. Since v0.27 the
   slot faces **inboard**: the ribbon runs a short way into the grip, folds down
   through the back cavity, then doubles back at low level and out through a duct
   under the phone cradle into the tray lane. Seat the fold before the lid goes on
   — it is a static crease, not a moving one (the rolling service loop lives in the
   tray). `deck3d.py --check-lanes` verifies the whole path is clear.
3. **Battery — polarity check first, cell NOT connected yet.** Since v0.27 the
   cell's connector is **J4 on the LEFT board** (there is no J3 — the right board
   lost its JST when the battery stopped crossing the spine). Vendors wire
   JST-PH pigtails **both ways**: meter the pack pigtail and confirm the red/+
   wire lands on the pin marked **"+"** on the back silk beside **J4** — that is
   **pin 1** ("−" marks pin 2); the silk also carries `BAT`, and `F1 PPTC 0.75A`
   labels the fuse sitting in series with that positive line. Foam-tape
   (0.3 mm) the 403040 cell to the **left** grip's floor where it will sit
   under the passive PCB — only the left cavity has the headroom — and dress its
   short pigtail along the chin to J4, ~8 mm away in the same cavity. Nothing
   crosses the spine any more. Leave the cell
   **unplugged** and the power switch **OFF** — it is connected only *after*
   the first flash (§3); see the REGOUT0 warning there.
4. Drop each board in, **parts down**, onto its perimeter bosses + the **3
   support posts** under the key field. On the **left**, the board goes in
   over the cell (~0.8 mm clearance under the diodes at nominal) — check the
   pigtail reaches J4 in the chin cleanly and nothing is pinched. Check the USB-C sits in its wall
   opening, the slide-switch knob reaches its slot, and the reset tact + LED
   align with the floor pinhole + light hole. *(v0.17: the USB-C opening and
   slide-switch slot are in the TOP shell wall, the reset pinhole + charge
   light-hole in the floor near the top zone — the shells were regenerated and
   fit-checked for this layout on 2026-07-14.)*
5. Lay the keymats over the domes and fit each **grip lid** (its rim lightly
   clamps the keymat web); drive the **5 M3×10 countersunk screws per grip** — heads finish flush with the face.
6. **Cable the tray + join the grips (v0.24):** the two grips no longer meet at
   x=0 — they're bridged by the telescoping tray. Lay the FFC into the `bridge`
   tray's enclosed channel with a **rolling service loop** (a U-fold that pays out
   as the jaw slides). Since v0.27 it is the **only** cable in there — one lane
   between the two springs, walled off from both by printed divider ribs, so keep
   the fold inside its channel and it cannot reach a coil. Bolt the `bridge` to the **right
   grip** (the ground member) with its **2 short M3s** into the cradle bosses,
   then engage the **left grip's inner shroud** into the open left end of the
   tray so it laps inside (it stays overlapped 57→17 mm across the travel, so the
   springs and the FFC stay enclosed at every width). Hook the **2 extension
   springs** from the tray's fixed anchors to the inner shroud's hooks — these
   are the clamp force. Leave the battery unplugged at J4 for now.
7. **Pointing nub (v0.21):** three steps, all on the right lid.
   **(a) Magnet:** press the Ø4 × 2 N52 disc into the `nub_spring` hub pocket
   **N pole facing down** (toward the sensor). Find N BEFORE seating, with a
   compass: **the disc face that attracts the needle's SOUTH end (the
   unpainted/white end) is the N face** — seat that face down. The driver
   zero-calibrates at boot but cannot fix a flipped magnet (both axes invert
   and the offset range is wrong). It's a press fit; a drop of CA if loose.
   **(b) Spring:** stand the spring on the bare PCB zone under the aperture —
   its 3 legs on the board's front face, magnet down over the sensor — then
   lower the lid over it so the square cap platform rises through the Ø10
   aperture and the underside counterbore captures the flange. Driving the lid screws presses
   the counterbore ceiling onto the flange (0.05 mm preload against the legs):
   the spring is clamped rigid, no adhesive. If it can rattle after screwing
   down, a print tolerance ate the preload — shim the counterbore with a strip
   of tape rather than glue.
   **(c) Cap:** with the lid screwed down, press the cap — the printed red
   replica or a genuine classic TrackPoint cap — onto the 4.4 mm square
   platform, exactly like re-capping a ThinkPad. It pulls off for lid
   removal — pull straight up, don't lever.
   First power-up: leave the nub untouched for the first ~2 s (32-sample zero
   calibration); axis flips/swaps are DT properties in `thumbdeck.dts`, not
   code.
8. **Grippers (v0.24):** **slide** the two **TPU grippers** in from the
   **y end of each cradle, under the rigid retainer** — they are trapped by it, not
   pressed on, so don't push them straight in from the front and don't glue them. **Teeth face the phone** (half-round ribs down the pad's inner
   face — they bite the cased edge so the phone can't creep or rotate; a gripper in
   backwards will hold, badly, and is the first thing to check if the screen won't
   stay square). The gripper is **biased toward the bottom** of the cradle, not
   centred — once the bottom shelf datums the phone by its lower long edge, a
   centred pad would miss the bottom of every short phone. Push it down against the
   shelf end of the slot. **v0.24e:** the **TPU lip** is what retains the phone — it
   stays soft so it can flex for thicker cases and can't scratch cover glass; the
   shell's retainer only stops the gripper peeling off and never reaches over the
   screen. **Don't run without a gripper** — there is no rigid backup over the phone.
   Retention is **mechanical**, so the deck is safe used screen-down. To fit a phone:
   pull the jaws apart, **seat one short edge under its lip first**, then push the
   other edge in — it will not drop straight down past both lips. To remove, hold the
   jaws open and lift the phone **up over the 3 mm bottom shelf**; the lip undersides
   are deliberately square and won't cam the phone out, which is the same reason it
   can't fall out. **Very thick cases:** compliance is only what the TPU lip can flex,
   so a chunky rugged case may push the lip aside and lose positive capture — check the
   phone can't be lifted straight out before trusting it screen-down. Then
   (v0.25: there is no MagSafe ring any more — retention is entirely the spring clamp,
   the toothed TPU grippers and the capture lips.)
   the battery means opening the **left grip** (5 screws, lid, keymat, board).

## 3. First flash (one-time SWD, then UF2 forever)

The E73 ships **blank** — it cannot be UF2-flashed out of the box.

> **Order matters — first power-up must be battery-free.** Until `UICR.REGOUT0`
> is programmed to 3.3 V, the nRF's I/O rail runs at its **1.8 V** default, and a
> full 4.2 V cell would put the battery divider's **2.1 V on AIN0 — exactly the
> pin's absolute-maximum rating**. So: battery switch OFF and cell unplugged,
> power from USB or the SWD probe only, flash the bootloader (which programs
> REGOUT0 = 3.3 V), and only *then* connect the cell.
>
> **v0.27: "battery-free" now means J4 unplugged, on the left board.** The switch
> alone will not do it — SW90 gates the load, not the cell, so with J4 mated the
> ribbon and the charger see the cell whatever the knob says. That is also exactly
> why J4 exists on the board the cell lives in.

1. Connect an SWD probe (J-Link, CMSIS-DAP, or a Raspberry Pi with OpenOCD) to the
   silk-labelled pads **TP1–5**: SWDIO, SWDCLK, RESET, 3V3, GND. Power the board
   from **USB or the probe's 3V3 only** — cell unplugged, switch OFF.
2. If the part arrives access-protected: `nrfjprog --recover` (or the OpenOCD
   equivalent) first.
3. Flash the **Adafruit nRF52 bootloader — nice_nano build** (that build matches
   this board's flash layout; the board itself is *not* a nice!nano). The
   bootloader sets `UICR.REGOUT0 = 3.3 V`, which the LiPo-direct power scheme
   requires — verify the flash completed before going further.
4. **Now connect the cell at J4** (polarity already metered in §2; the ribbon is
   already seated and latched at both ends) and switch ON —
   **ON = knob toward the USB-connector end of the board**.
5. From now on it's drag-and-drop: **double-tap reset** (paperclip in the floor
   pinhole) → a UF2 drive mounts → drag on `thumbdeck-zmk.uf2` from the GitHub
   Actions build (`.github/workflows/build.yml`, self-contained ZMK v0.3.0).
   That build is green (run 29443394494, 2026-07-15) so the artifact does exist —
   but **it has never been flashed to hardware, because no hardware exists.**
   Actions artifacts also expire, so re-run the workflow and use a fresh build
   rather than an old download.

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
- **Modifiers are mirrored** (v0.20): both grips end in the same stack — Ctrl at
  the bottom-outside corner, Shift directly above it, Alt beside Space. Hold the
  modifier with the thumb OPPOSITE the target key (Ctrl+C = right-thumb Ctrl +
  left-thumb C). No sticky/one-shot behaviors — everything is a plain hold;
  same-side triples (Ctrl+Shift+letter) use the corner Ctrl+Shift one-thumb
  bridge or a quick cross-hand reach.
- **FN layer** (hold FN, left grip): MINUS/EQUAL on 0/9, HOME/END on PgUp/PgDn,
  PSCRN on DEL, **SQT (`'`) on `;`** (the apostrophe has no physical key — the
  right H-row ends in the 2u Enter), **PIPE (`|`) on `[` and BSLH (`\`) on `]`**
  (the backslash cap became the right Ctrl in v0.20), `BT_CLR` + `BT_SEL 0–3`
  for profiles, plus `&bootloader` / `&sys_reset`.
- Pointer: nudge the **nub** — the cursor should track, faster with steeper
  deflection (rate control). **Hands off the nub for the first ~2 s after
  power-up** (zero calibration). If an axis is mirrored or swapped, set
  `invert-x` / `invert-y` / `swap-xy` on the `nub` node in `thumbdeck.dts` —
  a first-article calibration, not a code change. FN-layer mouse keys on the
  D-pad remain as a fallback pointer.
- Chord several keys at once — the diodes kill ghosting (verified exhaustively in
  `sim_matrix.py`, but enjoy confirming it with fingers).
