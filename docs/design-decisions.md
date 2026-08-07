# Design decisions

Decision log, newest first. Older entries are **history** — they record why calls
were made at the time and may name parts since replaced (Raytac → E73, Cirque /
IQS7211E trackpad → dropped, JST-GH → FFC ZIF, nice!nano → bare E73 board,
16-way FFC → 20-way, battery connector J3-on-the-right → J4+F1-on-the-left). The
current design is rev-A / v0.27 (first entry).

## v0.27 — the battery rides the bridge ribbon (2026-08-07, branch main)

The 403040 has lived in the **left** grip since v0.18; the charger, the switch and the
E73 have lived in the **right** grip since v0.8. Between them ran a two-wire pigtail
~265 mm long, across the spine, through a mechanism that moves on every phone insertion,
in an enclosure lane of its own. v0.27 deletes that cable. The bridge FFC goes **16-way →
20-way** (JUSHUO **AFA07-S20FCC-00**, LCSC **C262352** — same 1.0 mm pitch, bottom
contact, side entry, slide lock, 2.5 mm height, same JLC **Extended** tier, so no
assembly-class change) and four of the extra conductors carry the cell.

The **14 matrix signals are unchanged**, so ROW0–8 / COL0–9 land exactly where they did
and **the firmware is completely unaffected** — not "regenerated identical", untouched.

### Why the ribbon, and not a second connector pair

Three options: keep the pigtail, add a dedicated 2-pin connector at each end of a proper
cable, or spend four conductors on the ribbon that already crosses. The third wins on
every axis that matters here, and the v0.24d entry below is the evidence for most of it:

- **The second cable is where the enclosure kept failing.** Every v0.24c/d cable fault
  was the power lane's: it was the lane the tray's single end-wall window missed
  entirely (cut at y 15–33, lane at y 40), and its envelope was the one hanging 0.95 mm
  below the moving shroud's underside at full extension. One cable in one walled channel
  is not a smaller version of that problem — it is the problem deleted.
- **Part count goes DOWN, not up.** A dedicated pair costs two connectors, a cable and a
  second service loop. The ribbon route adds one connector (J4) and deletes one (J3), so
  the count is flat — and the ribbon's service loop already exists and is already ribbed
  off from both springs.
- **The cell finally terminates in the grip it lives in.** ~8 mm of pigtail to J4 instead
  of ~265 mm of bare two-wire to the other grip. That is the actual safety win; the fuse
  below is what pays for putting the cell on a flat flex.
- **Freed volume.** `POWER_Y`/`POWER_W`/`POWER_T` are gone and y 40.0–82.5 inside the
  clamp cavity is now empty — the lane plan reads `spring | FFC | spring`.

The costs, stated rather than buried: the ribbon now carries the **raw cell**, which is
what forces F1; and the left board **stops being purely passive**, which is what forces
J4. Both are treated as requirements below, not as nice-to-haves.

### Why 20-way and not 24

A 24-position sibling exists in the AFA07 family (confirm the exact suffix and LCSC
code against the JUSHUO drawing before ordering — this design never sourced one) and four
more guard conductors would be pleasant. It does not fit the board. J2 sits between the chin
mount hole at deck y 6.0 and the inner-mid mount hole, and it is the inner-mid hole's
**Ø8 boss disc** — not the board edge, not the routing — that caps the connector's pin
count. At 20 positions the land is **26.85 mm** long with **4.08 mm** to the boss against
a 4.00 mm gate: 0.08 mm of margin, and only after moving that hole from `board_h*0.42`
(= 40.74) to a **frozen 46.0**. A 24-way needs the hole at **≥50.0** — i.e. moving a
mount hole, its boss, its screw and the shell around it, to buy guard positions that F1
and the pin order below already make unnecessary.

The `0.42` is worth a sentence of its own. A hard geometric requirement had been hiding
behind an innocuous-looking fraction that nothing was allowed to notice; it is an
absolute now, with the reason written next to it.

### F1 is required. It is not belt-and-braces.

**Bourns MF-MSMF075-2** PPTC, LCSC **C84140**, 1812, **0.75 A hold / 1.5 A trip**,
13.2 V, Imax 100 A, initial resistance ≤0.45 Ω. On the **left** board at deck
(50.0, 5.5), in series with the cell **positive**, between J4 and J2 — on the **cell**
side of the ribbon, or it protects nothing at all.

The reasoning is a gap between two protections, not a duplication of either:

- A 1S pouch's built-in PCM does not trip until **2.0–2.5 A**.
- A 1.0 mm-pitch FFC conductor is **0.70 × 0.035 mm = 0.0245 mm²**. It reaches its
  105 °C insulation limit at about **2.8 A·√s**, and at a real short it melts its own
  PET in **~0.2 s**.
- Between them sits the **0.43–2.0 A** band: too little for the pack to notice, more than
  enough to cook the ribbon over seconds to minutes. That is precisely the signature of a
  **partially abraded conductor in a mechanism that flexes on every phone insertion** —
  the one failure this device's geometry actively invites — and nothing else covers it.

0.75 A hold rather than 0.5 A because the part derates with temperature and has to stay
clear of the ~196 mA charge current in a device designed to sit on a car dash.

**The cell must also be a protected pack — that is now a hard requirement, not advice.**
Integrated PCM with overcurrent 2.0–2.5 A / 8–16 ms, overcharge 4.275 V, overdischarge
2.75 V. The PCM and the PTC cover **different bands**; neither alone is sufficient, and
the BOM says so.

**What F1 costs: charge TIME, not capacity.** Its ≤0.45 Ω is in the charge loop, so
CC→CV handover happens at a lower cell voltage and the taper runs longer. The
*undercharge* at termination is `ITERM × R_loop` ≈ **10–16 mV**, which is negligible
beside the MCP73831's own **±32 mV** VREG tolerance — the charger's datasheet spread is
already twice the effect. What the loop resistance did deserve was a real trace:
`VBAT_CELL`/`VBAT` now route at **0.4 mm** via a genuine `power` netclass injected in
`route.sh`'s DSN rewrite. Before v0.27 `gen_board.py`'s `PWR = 0.5` was **dead code**
(KiCad 9 exposes no netclass setter through SWIG) and `VBAT_CELL` shipped at 0.2 mm —
about **336 mΩ**, a third of the entire charge loop, on a board that had a stated
intention to do better.

### The conductor order is an interlock, not packing convenience

Index 0 = **highest** deck y:

```
GND | GND | ROW0..ROW8 | COL5..COL9 | NC | VBAT_CELL | VBAT_CELL | NC
^ high deck y                                              low deck y ^
```

The hazard being designed against is **not** a one-position slip. It is the 16-way ribbon
every rev-A builder already owns: 17.0 mm of ribbon in a 21.0 mm housing has **4.0 mm of
independent slop at each end** — up to a **4-position shift**. `place_bridge()` maps the
left connector **by deck y**, so a shift joins right-net(k) to left-net(k+n), and only
nets present on *both* boards can fault.

- **GND is 15 positions from VBAT_CELL.** VBAT onto GND is a dead cell short — roughly
  10–16 A through one 0.0245 mm² conductor, which melts its own PET in ~0.2 s. At 15
  positions apart **no achievable shift can reach it**. The worst case instead lands VBAT
  on a **column**: ~50–100 mA into an MCU output NFET — one dead pin, no fire.
- **The two NC guards** absorb a ±1 slip completely, so VBAT never touches a matrix line
  for the ordinary error either. They carry **no net at all**, deliberately: tying them to
  GND would recreate exactly the short the guards exist to prevent.
- **No VBAT at a ribbon edge**, where a conductor is most exposed to abrasion.
- **Ribbon GND is not in the matrix return loop** (that closes through the right board's
  R1–R9 pulldowns and right-board GND), so exiling it to the far end costs no signal
  integrity — it is purely the battery return.
- **This ordering is only correct with F1 fitted.** Without the fuse the right answer
  changes shape entirely, which is another reason F1 is not an option.

**Consequence: purging "16-way" from the documentation is itself a safety item.** Any doc
still telling a builder what ribbon to buy in 16-way terms is actively dangerous now, so
every such reference across the repo moved to 20-way, and J2's silk names the **width and
the type** (`J2 FFC20 1.0mm TYPE-A <- pin1`) because getting either wrong is a short, not
a no-op.

### J3 out, J4 + F1 in — and why J4 has to exist

**J3 is deleted from the right board.** **J4** (JST-PH-2, S2B-PH-SM4-TB, C295747) is new
on the **left** board at deck (60.0, 5.5), mouth facing **+y**. Pin 1 = "+". Placement is
not free: `rot=180` would aim the plug off the bottom board edge into the shell wall, and
the naive mirror of the old right-board J3 at x = 31 would drive the mated plug's swath
straight into the cell. F1 sits west of it at (50.0, 5.5), clear of the cell footprint,
of the innermost diode column and of every boss. `VBAT_CELL` reaches the right board's
charger and switch over the ribbon; the power tree is otherwise **unchanged** — the
charger is still on the cell side of SW90, so it still charges while switched off, and
VBAT_SENSE (R22/R23/C6 → AIN0) is untouched.

J4 is **required**, not a convenience, and the reason is a live-parts argument: **SW90
gates only the LOAD**, so `VBAT_CELL` — and therefore the whole ribbon — is energised
whenever the cell is attached. Without a connector on the board the cell sits on, there
is no way to de-energize the ribbon for the service operation the docs advertise, and
[assembly.md](assembly.md)'s **battery-free first power-up** (the REGOUT0 / AIN0
absolute-maximum rule) becomes impossible to perform. So the build order changes:
**ribbon first, then J4** — and "battery-free" now means *J4 unplugged*, not *switch off*.

### The enclosure loses a lane and gains an assertion

`spring | FFC | power | spring` → **`spring | FFC | spring`**. `FLEX_Y` 26.5 → **28.5**,
`FLEX_W` 17.0 → **21.0**, `FLEX_T` still 0.3, `POWER_*` deleted.

The lane move is the more interesting half. v0.24d recorded that the FFC lane was kept at
"**J2's y centre (24.5)**" so the ribbon would enter the ZIF dead straight. **That was
false when it was written.** The lane was 26.5 and the connector was at 24.5 — a 2.0 mm
skew that ran the 17 mm ribbon off the pad row and put its first conductor outside the
housing altogether. 26.5 was never J2's y; it was the lane-plan *minimum* that the
spring-rib assert would accept, silently overriding the connector, and nothing objected
because the two numbers lived in different files and nothing compared them.

v0.27 makes the claim true and then makes it checkable. J2 moves to deck y **28.5** on
both boards — the 21 mm ribbon needs ≥28.20 to clear the front spring lane, and the
inner-mid mount boss is the ceiling — and `check_lanes()` now asserts the lane y against
**J2's slot centre read from the KiCad placement export** (to 0.25 mm) *and* the ribbon
width against J2's body, so a wrong pin count fails loudly too. `deck3d.py
--check-lanes` runs the whole thing in seconds, before any mesh work. The general lesson
is the same one v0.24d learned about its guards: a comment claiming two numbers are equal
is not a constraint, it is a wish.

### Boards

Both re-generated and **re-routed from scratch to 0 DRC violations / 0 unconnected**.
Right board: **75 nets, 114 footprints, 30 GND escape vias**. Left board: **60 nets**
(was 58 — `VCELL_RAW` and `VBAT_CELL` are new there). The footprint library gains
`ffc_afa07_s20fcc`; the 16-way file is **kept**, because the committed rev-A boards
reference it.

### The FFC duct, and why J2 was rotated to face inboard

A defect that **pre-dates v0.27** surfaced the moment the ribbon was modelled honestly:
there was no physical route from either ZIF into the enclosure lane, and never had been.
J2's cable slot sits at z ≈ 6.95 (the ZIF is back-mounted under a board at `PCB_Z` 7.9)
and the lane at z 0.2, and across the ribbon's y band the grip is solid from the tray end
to the cavity wall. With the slot facing the spine that left about **1.20 mm of x** in
which to lose **6.74 mm of z**. It could not be done.

Nothing caught it because *both* bridge cables were straight boxes in the lane reaching
neither connector, and a cable that reaches nothing touches nothing — `collide()` had no
opinion, and `cable_enclosure()` clipped 6 mm off each end, putting the connector ends
outside its window by construction.

Two ways to open the route, and the choice is structural:

- **Cut a full-height slot** from the lane up to the ZIF. No PCB change, no re-route —
  but at the ribbon's 23 mm y band that slot passes through the cradle backstop wall, its
  1.2 mm rest ledge and the bottom shelf, removing ~23 mm of phone-edge support out of
  ~78 mm on the one structure whose entire job is stopping a phone falling out.
- **Rotate J2 to face inboard** (chosen). The ribbon exits into ~10 mm of open back
  cavity, descends there, folds at z ≈ 2.2 and leaves through a **low duct** that passes
  *under* the retention structure — all of which lives at z ≥ 3.9. Costs one re-route and
  ~20 mm more ribbon, and buys back the cradle intact.

The duct is **stepped**, and that is not cosmetic. Only its grip-side half may be tall:
inboard of the grip's inner face the moving inner shroud's roof spans `CAV_Z1` 1.75 to
`izt` 3.15, so a straight 2.6-high cut across the whole duct left that roof **0.55 mm**
thick on an exposed outside surface — well under this file's own 3-perimeter convention
(`RIB_T` = 1.2). The grip side has no such roof (it is cutting the grip's own floor slab,
whose top is at 1.55), so it goes to `FLEX_DUCT_Z1` = 2.6 for the fold while the shroud
side stays a flat slot at `FLEX_DUCT_Z1_LANE` = 1.95. Measured result: **1.42 mm** of roof
left, and the ribbon's vertical drop is placed on the grip side of the face so it still
has the height it needs.

The descent is dimensioned, not eyeballed. `FFC_BEND_R` = 1.6 mm is charged against
`FLEX_TURN_X` = 2.0 mm, because a ribbon leaving a slot horizontally lands its vertical
leg one bend radius past the fold — sizing the fold to a zero-radius corner is how a
21 mm-wide ribbon ends up over a diode column. `check_lanes()` measures the resulting leg
against the real placement and asserts it clears the innermost back-side part: currently
**0.98 mm** (left, D25) and **1.03 mm** (right, D24).

`flex_route_report()` then sweeps the ribbon's **full 21 mm section** — not its centre
line — along the whole path and asserts nothing is buried in the shell. The centre-line
version of that test was written first and rejected: this repo's own v0.24e lesson is
that centre-line enclosure tests lie, and with 21 mm of ribbon in a 23 mm duct band the
width is exactly what is tight. Removing the duct makes it fail with the first
obstruction at y = 18.0 — the ribbon's *edge*, which a centre-line probe would have
walked straight past.

## v0.26 — the nub magnet becomes real, and the flexure gets a spec (2026-08-03, branch main)

The magnet had a **pocket** in `nub_spring` since v0.21 but never a **body**: it was in no
STL, no GLB, no render and no collision check. Adding it turned into an audit of the whole
pointing stack, because once you draw the magnet you have to say exactly where it sits, and
that number had never been written down.

### The magnet: a part you can actually order

The BOM said "Ø4 × 2 mm N52 disc, axially magnetized" with no supplier, no plating and no
tolerance. It now names **supermagnete `S-04-02-N`** (Ø4 × 2 mm, **N45**, Ni-Cu-Ni, axial,
Br 1.32–1.37 T) with a US part (totalElement `D4X2MMN52-250PK`) and an engineering-grade
alternative (Radial 9039 = Digi-Key `469-1072-ND`, N35SH, 150 °C, magnetization angle sorted
to ≤ 3°).

- **Grade drops N52 → N45.** N52 has the **lowest** service temperature of the common grades
  (≤ 65 °C vs ≤ 80 °C). This device clamps a phone, sits in sunlight and rides in cars. Past
  that limit the loss is irreversible and the driver's boot-zero *cannot* recover it — it
  re-zeros a weaker magnet and pointing goes quietly sluggish forever. N45 costs ~8 % of Br,
  which the firmware gain absorbs without noticing.
- **"(Bean spec)" was false.** The code comment credited the Ø4 × 2 size to the Ploopy Bean.
  The Bean's hardware appendix actually specifies **Ø6 × 2**, which our Ø7.0 hub cannot carry
  (the wall would drop to 0.5 mm). Ø4 × 2 is our own choice, made because it is a genuine
  mass-stock size that the hub *can* carry. The Bean also mounts its magnet **N away** from
  the sensor — the opposite of ours — so the polarity note is ours to own too.
- **Order by SKU, not description.** A Ø4 × 2 mm *diametrically* magnetized disc is also a
  cataloged product and is the wrong part.
- **The pocket was never a press fit.** It was drawn Ø4.10 for a Ø4.00 ±0.10 magnet, so a
  +tolerance magnet exactly equals the nominal bore — and FDM prints holes undersize. That is
  an interference fit being driven into a 1.45 mm wall by hand, and NdFeB is brittle. The bore
  opens to **Ø4.20** and retention becomes a drop of cyanoacrylate against the pocket ceiling.

### The gap nobody had computed

The docstring said the magnet sits "~2.6 mm over the back-side TMAG5273". That is the distance
to the **package**, and the package is not what measures anything. Per TI SLYS045C Figure 6-2,
the hall element sits **0.73 mm below the moulded top face** — and U4 is back-mounted, so its
mould face points *away* from the board and that 0.73 mm is *toward* the PCB. The real
magnet-face-to-die distance is **3.33 mm**:

```
magnet face 10.45 | 0.95 air | 1.60 FR4 | 0.06 solder | 0.72 package | die 7.12
```

`deck3d.py --report` now prints and asserts this whole stack instead of leaving it in a
comment. Modelled SOT-23-6 height also went 1.1 → **1.45 mm** (the real DBV figure), because
the die reference is measured off a face the model was placing 0.35 mm wrong.

At 3.33 mm a Ø4 × 2 N45 disc puts **~52 mT** on the die. Nothing saturates: the driver enables
**X and Y only**, and the axial field never enters a measured channel.

- **The X/Y range was wrong in the safe direction.** It was set to ±80 mT for "headroom vs the
  close nub magnet" — but X/Y only ever see the *transverse* field, which peaks around 12 mT
  including the static misalignment offset. v0.26 uses **±40 mT**, doubling resolution to
  1.2207 µT/count for free.
- **The hall element is 0.418 mm off the package axis** (+0.40 along the body, −0.12 across),
  and `gen_board` centres U4's *footprint* on the nub axis, so the die is off-axis by that much.
  This is left **uncompensated, deliberately**: it costs a static transverse offset the boot-zero
  removes and **under 1 %** response asymmetry once the flexure is stiff enough to stay in its
  linear range. Correcting it would mean either a board respin or de-coupling the mechanical nub
  from the feature that places the sensor. Recorded here so the next board spin can shift U4
  0.418 mm and take the 17 % of full scale back.

### The flexure: the arms were already right, but for no stated reason

The user's ask was a "ThinkPad-like experience of tension / pressure / travel", so the arms were
modelled properly for the first time. **Four** independent beam models got built — two here, two
adversarial — and the honest result is that **they agree on stress and disagree on stiffness by
7×.** That disagreement is itself the finding, so it is recorded rather than averaged away.

The reason is a boundary condition, not a modelling error. The arm is a 1.2 mm ribbon spiralling
r 3.6 → 5.9, so its first ~22 % is buried in the Ø7 hub and its last ~30 % in the flange bore.
Treat the whole 100° arc as a free beam and you get 2.6 N/mm; clamp it rigidly at both embedments
(48° free) and you get 18.3 N/mm. Neither is true — the hub is genuinely stiff, the 1 mm flange
ring is not — and no beam model can tell you where in between the real part sits.

What that bracket *can* settle is the design question, because the two candidates fall on opposite
sides of it. Against a target of **350–600 µm of cap travel at 150 gf** (the TrackPoint IV spec —
0–150 gf usable, 320 gf working — adapted to a hall nub, which unlike a strain gauge must actually
move to be read):

| arm thickness | cap travel at 150 gf | verdict |
|---|---|---|
| **0.8 mm (as built)** | **474 µm** (free-span) … **285 µm** (hub clamped) | **straddles the band** |
| 1.2 mm | 158 µm … 94 µm | below it under *every* assumption — nearly rigid |

So **`NUB_ARM_T` stays at 0.8.** An earlier pass of this same work had thickened it to 1.2 on the
strength of the softest model alone; correcting the embedment assumption reversed that. The v0.21
value was right — it simply had no stated reason, no target band, and no calibration procedure
attached to it. It now has all three, and arm thickness is documented as a **coupon-calibrated
parameter**: print at 0.7/0.8/0.9, hang 50/100/150 gf laterally off the cap, measure with a dial
indicator, and take the one nearest 350–600 µm. Do not trust a beam model here, including ours.

Peak arm stress at 150 gf is **23–29 MPa** against PETG's ~50 MPa yield — first yield around
300 gf. That is a thinner margin than one would choose, which is what the first change below is for.

Two changes the arms did need, both **independent of the stiffness argument**:

- **Root fillets.** The arm was a constant-width ribbon meeting the hub and the flange at a square
  re-entrant T-junction, and *every* model built — including the ones that disagreed about
  everything else — put peak stress at exactly that corner. The arm is now a two-sided offset
  polygon whose half-width swells 0.5 mm at both ends, shaped `(2s−1)^6` so the swell stays inside
  the last ~15 % — the zone where the arm is merging into the hub or flange anyway, so it costs no
  free slot at mid-arc. Peak stress drops ~19 % (28.6 → 23.1 MPa at 150 gf) and the peak migrates
  off the corner. This is the fix the stress numbers actually supported; thickening was not.
- **A plunge stop.** Nothing limited *axial* travel: the hub could sink the full 0.90 mm to the
  PCB, and because the magnet approaches the die over that stroke, Bz swung 52 → 92 mT and the
  pointing gain rose with it. The cursor sped up when you pressed harder **at constant tilt** —
  precisely the squishy, non-isometric feel a TrackPoint avoids. Three pads on the hub underside
  now bottom out at **0.35 mm**. (Note the stop is directionally uneven — it engages sooner toward
  a pad than between pads. Widening or adding pads is the follow-up if that reads as notchy.)

**Correction to v0.22.** That entry claims the cap skirt hitting the Ø10 aperture wall is the
"first tilt-stop" and that it keeps peak arm strain under 3.5 %. It does neither. The skirt has
1.1 mm of radial clearance and the cap moves ~54 µm/N laterally, so reaching that wall takes
**~20 N** — nothing a thumb will ever do. There is no tilt stop in the lid, and there never was.
What does bound overload is the v0.26 plunge pads (they ground out on the PCB in tilt as well as
in plunge) plus the arms' own ~300 gf first-yield margin. The "<3.5 % peak arm strain" acceptance
criterion should also be retired rather than re-used: PETG's yield strain is ~2.5 % (50 MPa /
2.0 GPa), so a 3.5 % budget is already past it. Judge stress against yield directly instead.

### Firmware is half of the feel, so it moved with the spring

`gain-div` is not independent of the arms — it converts field into cursor speed, so it inherits
the flexure's stiffness and the sensor's range. Two of the three changes here are unambiguous:

- **X/Y range ±80 → ±40 mT.** The old setting was justified as "headroom vs the close nub magnet",
  which conflates the axial field with the channels being measured. `MAG_CH_EN` enables X and Y
  only, and those never see more than ~12 mT. Halves the count size for free.
- **deadzone 150 → 100 counts.** Forced by the above: the range change halved the microtesla value
  of a count, so keeping 150 would have *doubled* the physical deadband. 100 counts = 0.122 mT ≈
  9.5 gf, about 2.8× the noise floor at 8× averaging.
- **`MAG_TEMPCO` → NdFeB (0.12 %/°C)** — a free register field left at "no compensation" for a
  magnet that is, in fact, NdFeB.

**gain-div 3500 → 1054 is a bracket, not a measurement**, and is labelled as such in the binding.
It inherits the flexure's 7× stiffness uncertainty: targeting full speed at 150 gf gives 615 at the
stiff end of the bracket and 1807 at the soft end. 1054 is the geometric mean, and across the
bracket the curve spans:

| thumb force | cursor speed |
|---|---|
| 25 gf | 8 – 35 px/s |
| 50 gf | 57 – 191 px/s |
| 100 gf | 289 – 876 px/s |
| 150 gf | 701 – 1200 px/s (clamp) |

The binding carries the formula to re-derive it from a measured count at 150 gf. It stays a
first-article item for two further reasons: printed arm stiffness varies with material and layer
bonding, and the sensor is spec'd to ±20 % sensitivity error, which this quadratic curve squares
into ±44 % of cursor speed.

### Also fixed

The site's "TI TMAG5273A1 Hall Sensor" hotspot was anchored to **`pcb_right__U2`** — the
MCP73831 **charger**, 13.5 mm away. The TMAG5273 is U4, and it was not even preserved as a node
in the web export. Both fixed, and the magnet is now its own explodable part.

## v0.25 — flat one-plane back, and the tray joint deleted rather than fixed (2026-08-02, branch main)

Two user calls in one pass, plus a consequence neither of them had alone.

### The faceted crown is gone (option A)

*"I appreciate everything you did to add the ergonomic 'cheeks' … but they are not working for me
aesthetically."* Five options were rendered as hillshaded relief so the choice could be made on the
shape rather than on a description; the call was **delete it**. Worth separating what was wrong: the
5.5 mm of palm fill was doing real ergonomic work, but the *language* — a cut-corner octagon, one
steep chamfer band, three scored grooves — read as a block applied to the back rather than a shape
the back has. The crown was also the sole reason the back halves printed cavity-down and therefore
needed tree supports through the cavity, and why the reset pinhole was a 7.1 mm Ø1.6 straw.

### The tray-to-grip joint is deleted, not repaired (option J3)

Measuring the joint to answer "is this the best design for strength and simplicity" turned up that
**it could not be assembled at all**:

- Both sides were **Ø3.4 M3 *clearance*** (`SCREW_HOLE_R` 1.7). No tapped hole, no heat-set bore, no
  head seat anywhere in the joint — a bolt engaged nothing. Conspicuous, because the grips' own five
  mount holes do it properly (Ø4.0 × 5.3 for an M3 insert, OD ~4.6).
- A probe straight down the bolt column at x = 83.3 meets solid grip from z = 17.7 to 5.2 — the
  cradle wall and capture retainer sit **12.5 mm** directly on top of it. No driver could reach it.

`--check` passed it every time, because **assemblability is not a collision**. Rather than fix a
joint whose whole job was to exist, the fixed tray is now unioned into `back_right`: one part,
203.75 × 103.8 × 22.2 mm. It missed the 204 mm brim-safe gate by 3.75 mm as drawn, so `OUTER_LEFT`
went −45 → **−41** and `INNER_LEN` 67 → **71** paid it back — full-open telescoping overlap is
unchanged at 13.35 mm, which is the number the enclosure assertion actually cares about.

### …and the two together broke the stance, which is why the back is now one plane

`SHROUD_ZBOT` = −4.5 was chosen as "above the −5.5 grip crown": the device rested on the two crown
plateaus with the tray hanging 1 mm clear. Delete the crown and the grips' backs are flat at z = 0,
so **the tray became the lowest thing on the device by 4.5 mm** — it would have rested on the centre
tray with both grips floating, and since J3 prints the tray as part of `back_right`, the merged part
would have needed support under ~87 cm² of cosmetic back face.

The fix is `BACK_Z = SHROUD_ZBOT`: both grips' outer backs drop to the tray floor, so the whole back
of the device is **one flat plane**. Deriving it from `SHROUD_ZBOT` rather than writing −4.5 twice
makes the coplanarity a fact of the model. The part now lies straight on the bed and prints with **no
supports at all** — the cavity, its bosses and its posts all open upward.

Consequences handled in the same pass: the back is 6.1 mm thick under the cavity there, so the reset
pinhole and the LED pipe get a Ø3.2 counterbore from the back and keep only their last 1.6 mm narrow
(otherwise the crown's 7 mm straw would have come straight back).

### The outside edges the hands wrap get a 1.2 mm quarter-round

`EDGE_R` = 1.2 on the back plane's outer edge and on the grip lids' keyboard-face outer edge —
*"just a slight rounding … around the outside of the device where human hands will touch
frequently."* Built as six ~0.2 mm bands of inset profile rather than a CadQuery `.fillet()`: these
boundaries are 200 mm long with dozens of segments, an OCC fillet on them is slow and fragile, and at
one band per layer the printed result is identical. Each band overhangs the last by one layer, so it
prints with no support. The lid's round is built from the **unclipped** footprint on purpose — near
the seam that profile sits 2.9 mm inboard and gets clipped away, so the reveal keeps its crisp 0.5 mm
chamfer and only the outer perimeter is rounded. Nothing moves: the nearest screw hole edge is 5.4 mm
inboard of the outer boundary and its countersink cone stops 2.3 mm short of the round.

## v0.25 — the nav cluster becomes one integrated D-pad (2026-08-01, branch main)

User request, with the Rii i8+ nav cluster circled as the reference: *"adjust the 5
circles directional pad to instead be a traditional integrated d pad like in the rii.
The idea is for it to be a circle with some sort of ridges internally or in the back to
enable the clicks to be cleanly discrete between up down left right and center. I think
this can be a change to the keymat and shell only."*

It can, and it is. The left grip's nav cluster was five scattered Ø6.2 buttons on 8.5 mm
centres poking through five Ø7.8 holes. It is now **one Ø24 pad** — four arm sectors
around a Ø9 centre OK, split by 2.0 mm relief moats — standing in a **single Ø24.4 lid
aperture** with a 0.6 mm dished lip. `deck.py` still emits the same five `NAV_*` dome
features at the same coordinates, so **the board, the matrix, the routing and the ZMK
keymap are byte-for-byte untouched**; the whole change lives in `deck3d.py`'s keymat and
grip-lid builders (`_dpad_zone` / `_dpad_plan`).

### Discreteness is bought with geometry, not with rigidity

A faithful one-piece rocker — a rigid cross on a centre pivot, rocking to press one dome
at a time — is the obvious answer and the wrong one here. It needs a stiff cap, and the
keymat is **TPU 95A** (E ≈ 30 MPa, ~80× softer than the PETG shells): a 24 mm TPU disc
does not transmit a corner press to a pivot, it just squashes locally. Worse, a centre
pivot has nowhere to react against except the **OK dome**, so every direction press would
land force on OK. Rocking was rejected; four cheaper pieces of geometry do the job:

- **Moats** (keymat). Each of the five actuators is its own column all the way down to
  the 0.8 mm web, so no cap material links neighbours at all. This is the primary
  isolator and it is *geometric*, not stiffness-dependent — which is why cross-talk
  becomes a web problem instead of a cap problem.
- **Moat relief** (keymat) — *the part that is easy to miss.* A moat on its own isolates
  nothing: the caps stop but the web runs straight on underneath at full thickness, and
  over a short span that web is **stiff**, because a thin-strip coupling goes as
  `t³/L³`. The first cut of this design used a 1.0 mm moat over the unmodified 0.8 mm
  web — **3.4× stiffer** than the 1.5 mm of web that separates two ordinary keycaps, i.e.
  a pad that would have pressed its neighbours along with the key you meant. The moat is
  now 2.0 mm wide and the web beneath it is thinned to **0.4 mm** (two 0.2 layers), which
  lands **~19× looser** than that key pair. `_dpad_zone` asserts that ratio rather than trusting a
  number: the absolute stiffness of a printed TPU membrane is not something this model
  can honestly predict, but "no stiffer than the geometry we already assume works" is a
  bar it can hold.
- **Clamp ring** (grip lid). The perimeter clamp rim only pins the web where the field's
  edge happens to run, and the pad sits well inboard of it. A closed annular downstand at
  **r 13.0 → 14.5** pins the web all the way round the pad, so a sector reacts against a
  clamped boundary instead of lifting the web its neighbours stand on. Its 1.0 mm standoff
  from the pad edge leaves each arm a short full-thickness hinge — soft enough to rock
  (≈ 32 N·mm/rad, an order more travel than the 0.4 mm a dome wants) but short enough to
  locate the arm.
- **Back rib** (keymat). The matching annulus on the web's underside, reaching to 0.2 mm
  above the PCB face, so the pinned ring cannot simply sink instead of clamping. It is a
  **backstop, not a preload** — 0.2 mm of rest clearance keeps it off `collide()`'s
  keymat-vs-board pair, which is not a mating one.

r 13.0 is not arbitrary: the arm domes are Ø7 discs centred at r 8.5, so their edges
reach r 12.0. `_dpad_zone` asserts the band starts ≥ 0.5 mm outside that, or the back rib
would come down on a dome's edge. It also asserts the pad covers its domes, that the OK
button plus moat leaves an arm sector to press, that the pad's web does not swallow
`MB_L`/`MB_R`, and that the web disc stays 1.0 mm inside the grip cavity — because
growing the upper zone to fit a bigger pad *is* a board change, and it should fail loudly
rather than quietly re-derive `board_h`.

### Notes

- The moats read as the seams of a moulded D-pad rather than as five gaps, which is the
  Rii/GBC look. A seamless top skin over hidden rear moats was considered and dropped for
  the same `t³/L³` reason the relief exists: a skin thin enough to fold over a 2 mm moat
  is ~0.4 mm, and bridging 0.4 mm of soft TPU across an enclosed slot is a print gamble
  where an open moat is not.
- The pad's outer edge and the OK button's each get a 45° break (0.5 / 0.4 mm) so the
  flat-topped extrusion the other caps use still reads as a moulded control, and the lid
  aperture gets a 0.6 mm 45° dish so the pad sits *in* the face rather than standing in a
  punched hole. Every one of those cones is based *outside* the wall it chamfers — a cone
  based exactly on the wall is a coincident-face boolean, and OCC returns a
  **non-watertight** shell for it (caught by `--all`, which prints watertightness).
- The NAV arrows grow 3.2 → 4.6 mm now that each has a whole sector, and `OK` is sized to
  the Ø9 button instead of the old Ø6.2 one. `_dpad_plan` asserts each Ø2.8 actuator nub
  still lands fully under its own cap — with the moat at 2.0 mm the arms start at r 6.5
  and the nubs at r 8.5 keep 0.6 mm of margin.
- `deck.Config.dpad_d` owns the diameter so `layout_gen.py` (which draws the pad as a
  dashed footprint *under* its five domes — the board really does still have five
  switches) and `deck3d.py` cannot drift apart.

## v0.24e — the capture lip actually captures (2026-07-30, branch main)

User review of the assembled GLB: *"the lips of the grippers are submerged within the
phone body… are they actually large enough to hold a phone with the gripster fully
inverted?"* and *"is the grip strength really enough or do we need a small shelf?
Phones dropping out is a dealbreaker."* Both were right, and the arithmetic is worse
than the observation. **v0.24d had no working capture lip at all** — retention was
friction, and friction does not have the margin.

### The lip was measured off two planes that don't exist

- **Underside.** It sat at `FACE_Z - LIP_T` = 13.1. A nominal cased phone's front face
  is at `RECESS_TOP + PHONE_TC` = **14.5**. The lip was modelled **1.4 mm inside the
  phone body**, so only its top 0.2 mm was ever above the screen.
- **Overhang.** `CRADLE_LIP` = 2.8 was measured from the *nominal* phone-edge plane
  (x = ±82.6). But the pad (1.6) and its teeth (0.8) stand 2.4 mm proud of that plane,
  so the clamped phone's edge rests on the **tooth crest** at 80.2, against a lip inner
  edge at 79.8 — **0.40 mm** of real overhang.
- Review then found the 0.4 was itself optimistic: `LIP_CHAM` = 0.8 sits on the lip's
  *top inboard* edge, which is precisely the sliver above the phone, so net capture over
  the front face was **≈ −0.2 mm — a clearance gap**. And because the lip's inner edge
  was 0.4 mm *inboard of the tooth crest*, the soft lip, not the teeth, was the clamp
  contact: **the v0.24d teeth were dead geometry.**

Fixed by referencing surfaces that physically exist: `PHONE_FACE_Z` for the underside,
and `lip_depth() = GRIP_PAD_T + TOOTH_R + LIP_OVER` so `LIP_OVER` is overhang past what
the phone actually touches. `--check` asserts both.

### The lip stays TPU. A rigid hook was tried and rejected.

An adversarial review refuted the all-TPU lip — it passes its bending check comfortably
(b = 60, TPU 95A at a pessimistic E = 20 MPa → 0.47 mm tip deflection at 10 g, 16 % of
the overhang) but review raised four modes bending never captures: **gripper pull-off**
(`gripper()` is a plain L-section with no dovetail, undercut or screw, so the whole
retention chain hung off a friction joint), **creep** under a deck stored face-down,
**temperature** (TPU 95A loses 35–45 % of its modulus at 50 °C, 60–70 % at 70 °C), and
**asymmetric load** (the phone rotates about one edge, so one lip takes all of it).

So a rigid PETG hook over the phone was built — and then **rejected on user review, which
was right**, for a reason none of the four reviewers raised:

> **A rigid hook at a fixed z can only capture a phone whose cased thickness is ≤ nominal.**
> The lip's underside is `PHONE_FACE_Z`, a 9.4 mm cased phone. A thicker case puts the
> phone's front face *above* that plane, so its edge butts into the lip's z band and the
> jaw cannot close. The lip degenerates into a side pad and the capture is silently gone.

TPU fails gracefully in that case — it deforms, rides up, still part-captures — where
PETG fails hard. And printed PETG layer lines on cover glass are a scratch source; TPU
spreads the contact. Stiffness and thickness-compliance are the *same* direction (+z),
so a lip cannot provide both: **the compliance has to be TPU, and the lip is the only
place it can live** without moving the phone's back datum.

What survives from the rigid version is the part that never touched the phone: a
**`_gripper_retainer`** caps the TPU lip's **root** so the gripper cannot peel off, and
stops `RETAIN_CLR` = 0.4 mm **outboard of the clamped phone edge** — so no rigid material
is ever over the screen, and the 3.4 mm of lip inboard of it stays free to flex, which is
exactly where a thick case needs give. Pull-off is solved; compliance and screen safety
are kept. The lip's top inboard edge carries the lead-in chamfer; its **underside stays
dead flat**, because a chamfer there would turn the phone's weight into a jaw-spreading
wedge.

**Known limitation, stated rather than hidden:** thickness compliance is only what the
TPU lip can flex. Cases meaningfully thicker than nominal still lose capture. The real
fix is a compliant pad *behind* the phone so the screen plane stays put regardless of
case thickness — but that drops the tray floor and cascades into `SHROUD_ZTOP`, the
v0.24d lane plan, the MagSafe recess and the v0.23 back crown, so it is not taken here.

### Insertion: the mechanism couldn't fit its own largest phone

Travel was exactly 130–170 — *identical* to the phone range — so at 170 there was zero
opening left. With a real lip that is fatal. Rotating the phone in doesn't help: its
xz diagonal (170.3) is longer than its length, and the well is exactly `PHONE_TC` deep.
The only path is seat-one-edge-then-translate, which needs

    clamp_pos ≥ P + lip_depth() + (GRIP_PAD_T + TOOTH_R) = P + 7.8

not the "one lip overhang" (3.0) first assumed. `clamp_insert_clr` = **9.0**, so the jaw
opens to **179**. Every mm of opening costs a mm of telescoping overlap, so `INNER_LEN`
goes **62 → 67** to keep the enclosure sealed: overlap at *full open* is 13.35 mm,
still over the ≥ 12 assertion. `--check` now runs a fourth **"open"** state, because the
widest the jaw goes — not the biggest phone — is the real worst case.

### Grip strength: the math, and why the shelf is justified

Statics: the springs pull the moving jaw with total `F_s`; that force passes through the
phone, so the normal force at **each** of the two grippers is `F_s` (not `F_s/2`).
Holding force = `2·μ·F_s`.

| `F_s` | μ | hold | slips at (0.30 kg phone) |
|---|---|---|---|
| 10 N | 0.6 (molded-TPU optimism) | 12.0 N | **4.1 g** |
| 10 N | 0.40 (glazed, oily, dusty) | 8.0 N | **2.7 g** |
| 10 N | 0.25 (printed ridges on a glossy PC case) | 5.0 N | **1.7 g** |
| 20 N | 0.6 | 24.0 N | 8.2 g |

Printed TPU is not molded TPU — layer ridges mean the pad contacts a smooth case only on
ridge crests, and elastomer friction is adhesion-dominated, so **μ ≈ 0.25–0.45 is the
defensible design range, not 0.6**. Review also derates `N` itself: the spring pulls at
`LANE_Z` = 0.2 while the phone contact acts at pad mid-height ≈ 9.9, and that ~9.7 mm
offset is a permanent racking couple reacted as slide friction in the shroud — roughly
`N ≈ 0.7·F_s`. Net: **the phone slips at 2–3 g**, which is ordinary handling.

Held normally, gravity acts along **−y**, and nothing was under the phone's bottom long
edge — the tray sits *behind* it (z), not *below* it (y). So that load rode entirely on
the one path that decays. **`SHELF_H` = 3 mm upstand** along the tray top's low-y edge
plus a tab on each grip's cradle turns it into bearing (contact stress 0.05 MPa —
nothing). It blocks only −y, so the phone still drops straight in and lifts straight
out. Honest caveats: it does nothing for the device held **upside down** (+y), where
friction still rules; and it can't live on the moving inner shroud, whose front wall is
inset to y ≥ 8.75, *inside* the phone's 8.5 footprint — so at long spans ~40 mm of the
phone's bottom edge overhangs the tray shelf and is carried by the cradle tabs.

Worth recording: **no commercial controller has a bottom shelf** — Backbone, Kishi,
GameSir and the Abxylute all leave both long edges clear. They can, because molded
liners and higher clamp force give them the friction we don't have.

### Springs: the anchor moves, and the spring type is still wrong

`SPRING_ANCHOR_X` **22 → 76**. At 22 the installed length ran 7.85 → 47.85 mm — 510 %
extension, which no coil spring survives — and because an extension spring is weakest
when least stretched, the **smallest phones would have got the weakest clamp**. At 76 it
runs 61.85 → 105.85 mm, a **1.71:1** length ratio instead of 6.1:1.

That makes the spring *buildable*, not *right*. Review closed the loop on the numbers:
a Ø4 / 0.5 mm music-wire spring at C = 7 caps initial tension at **F0 ≈ 1.85 N/spring,
not the 3 N assumed** — τ_i would need ~259 MPa against a ~160 MPa limit — so min-span
clamp lands near 5.8 N total, not 8.1. And the spring is **fatigue-limited** (τ ≈
870–930 MPa against an ~843 MPa cyclic allowable, cycling on every insertion), while a
**hooked extension spring's failure mode is total release**. None of Backbone, Kishi,
GameSir or Abxylute uses hooked extension springs: they use **compression springs
captive in the telescoping bridge**, or a **constant-force spiral**. That is a component
choice for the user to make, so it is flagged, not silently changed.

**Also flagged, not fixed:** the assembly GLB used to seat the phone by its *camera-bump
tip* on the recess floor (a v0.18 rigid-well leftover), which put its screen 0.82 mm
above `PHONE_FACE_Z` and is why the lip still rendered buried. It now seats by the
**screen**, so the GLB and the fit model agree — and that makes visible a real
interference the old datum was hiding: a bare S25U's camera bump stands ~2.0 mm proud of
its back while a 1.2 mm case covers only 1.2 of it, so **a flat full-width tray cannot
accept a phone whose bump exceeds its case thickness**. Either the tray needs a bump
relief or it needs to narrow toward the Kishi/Backbone rail form.

## v0.24d — enclosure lane plan + gripper teeth (2026-07-28, branch feature/expanding-clamp)

User review of the v0.24c clamp found three faults. All three were real, and the first
two were the *same* fault: v0.24c placed the enclosure's contents by eye, one at a time,
instead of to a plan.

- **Everything inside the enclosure now runs in its own y LANE, on one shared z.**
  Front → back the tray reads `spring | FFC | power | spring`, every lane on `LANE_Z`
  (the mid-height of the *moving* shroud's cavity). Nothing is stacked over anything.
  - *Why it was broken:* v0.24c ran the FFC at y=24 directly under spring 0 (also y=24),
    z bands overlapping — the coil sat on the ribbon, and the ribbon's service loop had
    nowhere to crumple at short spans that wasn't a spring. The user called this out
    before it ever got printed.
  - *The fix is a lane plan, not a nudge.* The springs move OUT to the enclosure's y
    extremes (13.5 / 83.5); the FFC keeps **J2's y centre (24.5)** so the 16-way ribbon
    still enters the ZIF dead straight rather than being doglegged to make room; the
    power cable keeps its own row at 40. Pushing the springs outboard is a second win:
    a wider stance resists jaw racking.
    > **⚠ Superseded by v0.27, and the "J2's y centre" claim in this bullet was already
    > wrong when written.** The lane was 26.5 against a connector at 24.5 — a 2.0 mm
    > skew that put the ribbon's first conductor outside the housing. 26.5 was the
    > lane-plan minimum the spring-rib assert would accept, not J2's y. v0.27 moves
    > both to **28.5** (21 mm ribbon, 20-way), deletes the power lane and its cable
    > entirely (`spring | FFC | spring`), and makes `check_lanes()` assert the lane
    > against the KiCad placement export so the two cannot drift apart again.
  - **Printed divider RIBS** wall each cable into a channel, in *both* telescoping
    members, so a loose loop has no path into a spring lane at any extension. The tray's
    ribs can only live right of the moving shroud's end at the *shortest* span — that is
    still the majority of the run, and exactly the stretch that was open cavity before.
- **The cables were exposed out the back at full extension — root cause was a z, not a
  gap.** v0.24c pinned both cables to the FIXED tray's floor. The MOVING shroud's floor
  sits 1.4 mm *above* that, so across the span only the moving shroud covers (longest at
  full extension) the cables hung in open air behind the device — the power cable's
  envelope reaching 0.95 mm below the shroud's underside. Putting every lane on `LANE_Z`
  *inside the moving shroud's cavity* makes enclosure hold **by construction** at every
  extension, instead of depending on the fixed tray still happening to be underneath.
  Two consequential fixes came with it: the shroud's left end wall now has real cable
  **pass-throughs** (v0.24c modelled the ribbon straight through 1.4 mm of PETG), and the
  tray's right end wall has **one window per lane** (v0.24c cut a single window at
  y 15–33, which the power lane at y=40 missed entirely).
- **The TPU grippers get TEETH** (the GameSir / Abxylute detail v0.24c skipped). 13
  half-round ribs at 3.4 mm pitch, axis along the phone's thickness, 0.8 mm proud of the
  pad face. A flat pad resisted the phone creeping or rotating in y by friction alone;
  the teeth bite the cased edge, which is what actually keeps the screen square to the
  keyboard face. Rolling them out of cylinders centred *on* the pad face leaves exactly
  half proud — the shape that bites and the shape TPU prints without support. The
  capture lip also gains a **lead-in chamfer** on its top inboard edge so the phone snaps
  past it instead of having to be threaded in square.
- **Both `--check` guards that should have caught this were themselves wrong** — worth
  recording, because the geometry bugs were only survivable *because* the guards passed.
  - `cable_enclosure` ray-cast from the cable's **centre line**, so a cable sunk inside a
    shroud wall reported "SEALED": every ray promptly hit the wall it was embedded in. It
    now runs two tests — a **solid** test (the clipped run may not intersect the tray at
    all; a cable inside a wall is impossible, not "contact") and rays cast from just
    outside the cable's **envelope**. Fed the v0.24c lanes it fails 2 / 9 / 10 samples at
    min / nominal / max span, `power … open: down` — precisely the reported symptom, and
    worst at full extension, as reported.
  - `_allowed` whitelisted **"spring vs anything"** as intended mating, which is how a
    coil resting on the FFC never showed up as a clash. A spring may now only touch its
    own anchors (`bridge`, `back_left`). Likewise the cables no longer get a free pass
    against `bridge`: inside the tray they run in a walled channel with real clearance,
    so any overlap there means buried-in-a-wall.
  - `--check` now also asserts the **lane plan** numerically (each cable between the two
    springs, ≥2 mm clear of both, channels far enough apart to wall off, lane axis inside
    the moving shroud's cavity) — pure arithmetic, so a lane regression fails in
    milliseconds instead of after a four-minute build.

**Known, not fixed here:** the spring stroke is aggressive. With the anchor at x=22 the
installed length runs ~7.9 mm at min span to ~48 mm at max — a >5:1 working ratio no coil
extension spring will survive. Moving the anchor toward the tray's right wall converts
that to a far saner ratio on the same 40 mm travel. Left alone deliberately: it is a
spring-selection question the user has not weighed in on, and it does not interact with
the lane plan.

## v0.24 — expanding spring-clamp back (2026-07-26, branch feature/expanding-clamp)

User request: make the back **expand and collapse like a Razer Kishi 2 / Backbone** so
it clasps different-size phones with a spring — a drastic rework of the rigid center.
Chosen after four decisions: **printed dual-rail slide** (no metal rods), **2 extension
springs**, **preserve near-flush at the nominal phone**, phone long-edge range
**130–170 mm**.

**FINAL landing: 2-part tray (the geared 3-stage below was built, then simplified away).**

- **The rigid center is gone.** Deleted the bolted `center_panel`, the sunken
  flush-screen well, the x=0 back seam + tabs/shiplap, the panel screws, and the central
  spine slab. The two grips are now separate bodies joined by the telescoping tray. A
  deliberate reversal of the v0.8/v0.18 fixed-flush calls — the user wants multi-phone
  fit over a single-phone flush mount.
- **2-part telescoping TRAY (final).** After building the geared 3-stage (below), the
  user flagged it as over-complex and pointed to the Abxylute S9 / 8BitDo single-joint
  trays. Reframe that settled it: **our travel is only ~40 mm (1.3:1)**, and the geared
  telescope's whole value is holding overlap over *large* travel — for 40 mm a single
  lap keeps huge overlap throughout, so the gear solved a problem we don't have. The
  tray (`bridge` = fixed tray + the left grip's lapping plate) is simpler, sturdier in
  practice (the clamped phone is the stiffener), far easier to tune, and its continuous
  flat top hosts the MagSafe ring + leaves back-space for maker alt-shells (the user's
  hackability goal). Kept: the enclosure (lapping plates), springs, power cable, rounded
  section. *(⚠ v0.27: the power cable is deleted — the cell crosses on the bridge ribbon.)* Dropped: the pinion, both racks, the separate centre stage, the twin channels.
- **Face-down retention is MECHANICAL, not magnetic.** Requirement: usable screen-down
  over your face (Switch/Steam-Deck). Magnets shear/peel — unsafe over a face — so the
  phone is trapped between the tray (behind) and **deep soft lips** (front); gravity just
  presses it into the lips. The lips + a compliant edge grip are one **TPU gripper** per
  grip (`gripper_left/right`, GameSir-style, prints with the keymats). Lip depth + clamp
  force are the coupon tune.
- **MagSafe is back — as a SECONDARY convenience.** A strong **N52 ring** (mount side,
  not a passive steel plate — the user correctly noted the phone/case magnet is the weak
  one) seats in a recess at the tray centre (`magsafe_ring`), for back-flat + snap only.
  Because it isn't load-bearing, its alignment drift across phone sizes/cases (the thing
  that killed a fixed ring on the old rigid mount) stops mattering; makers can reposition
  or float it. Opt-in: Android (incl. our S25U) needs a magnetic case/stick-on ring;
  iPhone gets it free; the clamp holds the phone either way.
- **THREE-STAGE GEARED brace (feedback: match the Kishi's geared telescope; make it
  sturdy for print/mould).** `deck.product()` is parametric on `clamp_pos`; the right
  grip is the frame reference and the left is the moving jaw. The brace is a 3-section
  slide: a **centre stage** (`bridge`) telescoping inside a **channel on each grip**,
  with a **pinion** (`pinion`) meshing a **fixed rack** (right grip) and a **moving
  rack** (left grip). This enforces a **2:1** — `_center_x()` places the centre at the
  midpoint = the phone centreline at every span. *Why geared, not free-sliding:* a
  telescope's stiffness is its overlap; free stages hand off (one runs to its stop,
  then the other), leaving the worst-case one-joint-does-all at intermediate spans. The
  2:1 keeps **both joints half-engaged everywhere**, maximising rigidity, killing
  racking, halving per-joint travel/wear, and keeping the pad behind the phone. Three
  stages (not two) also buy the collapsed→extended range without a bigger closed unit.
  It evolved from a 2-stage nested shroud (this same iteration) once the geared
  reference was specified.
- **Sturdy section (per the brief).** Every stage is a solid bar with a **flat
  phone-side top + a rounded-bevel back** (`_rbar`) — a deep, stress-concentration-free
  section for bending/torsion, comfortable in hand, and consonant with the v0.23 crown.
  The clamp **springs**, the **FFC**, and the **power cable** run enclosed in the nested
  stages' cavity on y-lanes clear of the gear/racks.
- **The missing power cable, added + enclosed.** The battery leads (left-grip 403040 →
  J3 on the right board) were never modeled; they're now a `power_body` routed enclosed
  through the shrouds in its own y/z lane beside the FFC, each with a rolling service
  loop. Collision shows both cables as intended contacts with the shrouds (threaded
  through, inside the cavity), not clashes.
  > **⚠ Deleted in v0.27.** The cable, its lane and J3 are all gone: the cell crosses on
  > four conductors of a 20-way bridge ribbon and plugs into **J4 on the LEFT board**,
  > ~8 mm from where it sits. `power_body` no longer exists.
- **Packing conflicts solved during collision bring-up** (validated at min/nominal/max):
  the left grip's mount screws had to be shifted with the moving jaw (they were pinned
  at nominal); the recess floor was shortened to x −60 so it clears the **collapsed
  grip's battery** (the phone is edge-clamped, so it only needs central + cradle-edge
  support, not full-back support); the cradle walls were pulled 0.9 mm shy of J2's
  courtyard; and the bolt column was moved off J2's y-band. `--check` asserts the
  shrouds stay overlapped (≥12 mm) so the enclosure can't open at full extension.
- **Retention & near-flush trade-offs (accepted).** X = spring clamp on the short
  edges via TPU-padded cradles; Z = screen-edge lips + the recess; Y = bridge walls.
  Near-flush holds exactly only at the nominal cased thickness (9.4 mm) — thinner
  phones sit slightly low, thicker slightly proud — and the smallest phones are
  right-justified (right edge pinned) rather than centred.
- **Electrical / battery.** Both cross-grip cables — the 16-way FFC (matrix) and the
  battery power leads — now need a **rolling service loop** (fold inside the shroud;
  FFC grows to ≈240 mm) because the span is variable. The 403040 battery stays in the
  left grip and rides the moving jaw. No PCB changes — this is shell-only; the boards
  remain v0.22 rev-A.
  > **⚠ Superseded by v0.27.** There is only **one** cross-grip cable now: a **20-way**
  > FFC carrying the matrix *and* the cell. ≥240 mm and the rolling service loop still
  > stand — quoted for 20-way stock, **TYPE-A only**. This did become a PCB change: J2
  > is a 20-position ZIF at deck y 28.5, the right board loses J3, and the left board
  > gains J4 + F1.

## v0.23 — faceted ergonomic back crown (2026-07-26, branch feature/back-ergonomics)

User feedback: "the design is great but flat — use more sophisticated geometry for
better ergonomics, especially the back contours; take inspiration from the Rii 8+
back and 90s electronics." The back was a dead-flat extruded tray (outer face a
single z=0 plane), so the device pressed a flat slab into the palm.

- **A faceted palm crown, added BELOW z=0.** Two cut-corner **grip plateaus** rise
  **5.5 mm** below the back plane (apex biased to the outer edge where the thenar
  heel and curled fingers bear), each scored with three **shadow-line grip
  grooves**; a lower faceted **spine panel** (−2.2 mm) laps into both so the whole
  back reads as one milled 90s-industrial block (Sega/Nokia cut-block facets, crisp
  panel lines), tapering to a thin land at the perimeter. Generated with CadQuery
  **ruled lofts** of cut-corner octagon sections — planar-facet B-rep, exact and
  STEP-clean, the right tool for the *faceted* (not smooth-organic) look the user
  chose. scipy thin-plate-RBF + scikit-image marching-cubes were installed for a
  future SDF/organic pass but are unused here by design.
- **Why additive-below-z=0 is the whole trick.** The crown never enters the
  electronics cavity (everything at z ≥ FLOOR), so the validated PCB fit, the
  221-body collision result (still **0 clashes**), the joinery and the bed-fit are
  unchanged by construction — the change is provably local to the cosmetic back.
  The reset pinhole + charge-LED holes are the only cavity features it touches, and
  they are just lengthened to pierce the crown to daylight.
- **Print orientation flips floor-down → CAVITY-DOWN** (the one real cost). A
  convex crown can't print floor-down (a convex-down face droops near its apex), so
  the halves now print cavity-opening-down: the crown prints **apex-up as a
  strictly-narrowing faceted peak** — self-supporting at any facet angle, clean
  cosmetic face. The internal PCB bosses/posts become the only downward faces and
  take **tree supports inside the cavity**, where the scars are hidden (the user
  explicitly chose "cavity-down with supports so the support scars are internal"
  over a bolt-on cover or an outer-face-down print with visible palm-side scars).
- **Thickness.** Device stays 14.7 mm at the flush front plane and ~15.7 mm at the
  thin edges; the grips swell to ~20 mm back-to-face (~24.8 mm incl. keycaps) —
  the Rii-8+ hand-filling target. The PCB is unchanged from v0.22 rev-A (the crown
  is shell-only; boards were not re-fabbed, so their silkscreen still reads v0.22).

## v0.22 — true-mirror page keys + genuine-TrackPoint-cap mount (2026-07-24, branch feature/right-joystick)

Two user-feedback items on the v0.21 print/renders.

- **PgUp/PgDn move to the TRUE mouse-button mirror x = 57.25** (the F10|DEL
  gap, mirroring the left pair's ESC|F1 gap; y unchanged at cy_lo ± 5.5). The
  user caught them sitting "above F9" (x 45.7). v0.21 had dodged 57.25 with
  the note "the true mirror is ON the E73 body" — which conflated the two
  board FACES: domes are front-side copper, the module is a back-side part,
  and they coexist at the same x/y. What actually needed care: (1) BOTH
  feature diodes — PGUP's default spot (deck 57.25, 87.5) is under the module
  belly and PGDN's (57.25, 76.5) is on the TP1-5 SWD row (y 75.7), so they
  drop to deck (52.5, 73.2) and (57.25, 73.2), just under the TP row; (2)
  SW91 moved (53.5, 71.5) → (46.0, 80.5) — the vacated old-PGUP zone; its
  first two candidates hit TP6/TP7 and the R-row (the reset's 7.6×5.7
  courtyard fits no gap in the crowded y 66–77 band); (3) the
  module's south-castellation escape vias must clear the PGUP dome's r3.6
  all-layer via keep-out — the autorouter re-fans them (tracks stay legal
  through the keep-out; only vias are banned). The dome courtyard clears the
  antenna keep-out band (module-top 5.5 mm) by ~4 mm.
- **The nub mount becomes GENUINE-TrackPoint-cap compatible.** v0.21's Ø5
  round spigot + smooth-top printed dish cap (TPU, but no dot texture — a
  slick surface that wears with no replacement path but a reprint); the user
  asked for the classic cap look ("people who love the nub
  will respond to it visually"). The spring's post is now the **standard
  classic TrackPoint square platform: 4.4 mm sq × 2.5** (genuine classic
  full-size caps — soft dome / soft rim / classic dome, the ones sold in
  10-packs everywhere — have a ~4.5 mm square socket ~2.5 deep; dimension
  cross-checked against the navcaps project's cap-mount sources, which print
  against genuine caps: mount side 4.5, height 2.5, classic cap adds ~5 mm
  height, and 6 mm-tall variants "tend to come off" as thumbsticks). The
  printed cap is now a **classic soft-dome replica in ThinkPad-red TPU**:
  mushroom profile (Ø7.8 flared skirt, Ø6.8 waist, Ø7.8 dotted dome, 5.25
  tall), the same 4.6 sq × 2.6 socket (corners r0.6, waist Ø6.8 — the r0.6 corner
  reaches r3.00, so a Ø6.2 waist left a 0.10 mm unprintable corner wall,
  caught in STL review; Ø6.8 leaves 0.40 mm ≈ one extrusion width), so
  printed and genuine caps interchange on the same post.
  Hub top drops 16.4 → **14.0** (0.7 below the face): the cap skirt nestles
  INTO the Ø10 aperture exactly like a TrackPoint between keycaps; dome top
  z 18.9 (+0.35 dot grid) ≈ 4.2 mm proud of the face. First tilt-stop is now the rubber skirt
  against the aperture wall (1.2 mm) instead of plastic-on-plastic — gentler
  on the flexure (peak arm strain drops below ~3.5%). Sensor gap, magnet,
  arms, legs and clamp are untouched; the GLB paints the cap
  `trackpoint_red`.
  > **⚠ Superseded by v0.26 — the tilt-stop claim in this paragraph is wrong.** Reaching
  > the aperture wall takes ~20 N of thumb force, so it is not a stop at all, and the
  > "<3.5 % peak arm strain" criterion is past PETG's ~2.5 % yield strain anyway. v0.26
  > re-derived the flexure against the TrackPoint IV spec and **kept the 0.8 mm arms** (they
  > were already in the target band), but added a root fillet and a 0.35 mm plunge stop, so
  > "arms, legs and clamp are untouched" no longer holds. Neither does "sensor gap ...
  > untouched": the gap was never 2.6 mm — that measured to the package, not the die.

## v0.21 — right-grip pointing nub: Bean-style TMAG5273 hall sensor (2026-07-23, branch feature/right-joystick)

The right top zone becomes a mirror of the left cluster, with a real pointing
device where the D-pad mirror lands. Final architecture: a **ThinkPad-style
rate-control nub** built the way the
[Ploopy Bean pointing stick](https://github.com/ploopyco/bean-pointing-stick/)
does it (hardware CERN-OHL-S v2 — credit where due; our sensor placement,
flexure, and driver are original implementations of the same architecture):
a **TI TMAG5273A1 I²C 3-axis hall sensor** (SOT-23-6, LCSC **C3716049**,
~$0.60, basic SMT — machine-placed like everything else) under the board, a
**Ø4×2 mm N52 disc magnet** press-fit into a **3D-printed flexure spring**
above the lid, and a printed friction cap. Deflecting the nub tilts/shifts the
magnet; the sensor reads the X/Y field **through the 1.6 mm FR4**; firmware
maps deflection to cursor **velocity** (quadratic curve + deadzone + remainder
accumulation) — steeper tilt = faster cursor, exactly the trackpoint behavior
the user asked for, with zero moving parts on the PCB.

- **The ALPS detour, recorded honestly**: the first implementation used an
  ALPS RKJXV1224005 analog gimbal stick (THT, JLC hand-solder). It worked
  electrically (routed 0/0) but the 11.2 mm module body stood proud of the
  face with a housing built around it — the user expected "the stick pokes
  out, not the module," and a Switch-style flush face is geometrically
  impossible with any COTS gimbal in a 5.2 mm under-lid cavity: the module
  that fits doesn't exist at JLC, and the module JLC has doesn't fit. The
  hall-nub architecture inverts the problem: the tall part (spring + cap) is
  a printed part *outside* the shell; the electronic part is a 1 mm SMT chip
  *inside* it. It also restores the all-SMT, no-hand-solder fab story and
  drops the moving-part count on the board to zero.
- **Placement**: sensor U4 at (32.3, 79.0) right-grip-local — the **exact**
  left-D-pad mirror (32.3 mm from the inner edge on both grips, same y — the
  ALPS variant's 2 mm terminal-row offset died with the ALPS). Back
  side, under the lid's Ø10 nub aperture. PgUp/PgDn are the mouse-button
  pair's mirror: same y-heights (cy_lo ± 5.5), same 11 mm spacing, at
  x = 45.7 — the true MB mirror x (57.25) is ON the E73 body; the right
  outer-top has belonged to the antenna since v0.17, so the pair sits between
  nub and radio.
- **Electrical**: the rev-B "trackpad breakout" pads finally do their job —
  **SDA = TP6 (P0.05), SCL = TP7 (P0.28), INT = TP8 (P0.29)**, TWIM0 at
  400 kHz, addr 0x35. Adds only R26/R27 (4k7 pullups) and C8 (100 nF bypass).
  No new MCU pins, no analog domain, no SAADC conflict with the battery
  divider (the ALPS plan's open risk), and deep-sleep drain is the sensor's
  sleep current instead of 660 µA of pot bias.
- **Board knock-ons**: TP6-8 relocate to deck y 67.5 (PgDn's diode landed on
  the old row); C7 beside the USB-C; SW91 reset to deck (53.5, 71.5); the
  deterministic In2 USB lanes get a reworked D+ elbow (rev-A 24.0 → 33.0) and
  a dedicated D− resurface column — the v0.17 columns are inside the new
  PGUP dome ring. Board is back to **all-SMT, 36 right keys, 78 total**; the
  ALPS footprint file is deleted.
- **Firmware**: new in-tree Zephyr module **`firmware/zmk-modules/tmag5273_nub`**
  (Apache-2.0, register map from the upstream Zephyr tmag5273 sensor driver +
  TI datasheet — NOT derived from the Bean's GPLv3 QMK firmware): polls X/Y at
  100 Hz, boot-averages the magnetic zero (which also swallows the MagSafe
  ring's static field), then quadratic rate-control → `input_report_rel`
  into a `zmk,input-listener`. Deadzone/gain/max-speed/axis-flips are DT
  properties — first-article tuning without touching C. A `pm_device` hook +
  `CONFIG_PM_DEVICE` puts the sensor into its ~nA sleep mode when ZMK deep
  sleep fires (continuous mode free-runs at ~2.3 mA on the always-up REG0
  rail — enough to kill the cell in a week of "sleep"; caught in review) and
  re-zeros on resume. Matrix stays 78 keys; west.yml carries no third-party
  modules.
- **Shell/CAD**: right lid gets a plain **Ø10 aperture** (no collar, no pod —
  the face stays flat like a ThinkPad keyboard) with an underside counterbore
  over a printed **nub_spring** (Ø14.8 flange + 3 spiral flexure arms + Ø7 hub;
  the magnet pocket is a press-fit, N-up). The spring is **clamped, not
  floating**: 3 legs on the flange underside bear on the PCB front face and
  the counterbore ceiling presses the flange onto them with 0.05 mm preload
  when the lid screws go home (the adversarial fit review caught the first cut
  leaving the flange 0.9 mm free to drop). A **nub_cap** (Ø8.5 TPU friction
  dome, 4.25 mm proud of the face) press-fits 0.95 mm onto the hub's Ø5
  spigot — cap and spring are prints 8 and 9. Spring compliance is a
  print-tune parameter (arm thickness 0.8); both parts verified watertight.

## v0.20 — mirrored modifiers: Ctrl/Shift/Alt on both grips (2026-07-22)

The 147 mm phone gap means a thumb can never reach the opposite grip, so any
modifier+same-side-key chord needs that modifier on BOTH grips — with left-only
Ctrl, the entire core shortcut cluster (Ctrl+Z/X/C/V/A/S — all left-grip
letters) was physically impossible. The Rii i8+ itself half-acknowledges this:
it duplicates Shift at both ends of the Z-row and carries a right-side AltGr,
and its layout demotes Del to Fn+Backspace. We extend its own logic to the
split geometry. Reviewed by a 3-critic panel (thumb ergonomics, ZMK
feasibility, Rii fidelity) before landing.

- **Two right-grip caps relabel, nothing else moves**: bottom-row `AGR` → `Alt`
  (the keycode was already RALT; AltGr ≡ right Alt on US layouts) and the
  outer-corner `\` → `Ctrl`. Both grips now end in the identical mirrored
  stack — **Ctrl at the bottom-outside corner, Shift directly above it, Alt
  beside Space** (the Rii's own Alt|Space|AltGr grammar). Left grip, brackets,
  FN and WIN are untouched. Zero PCB/matrix change: `thumbdeck.dtsi`
  regenerated **byte-identical**; all 78 domes keep their positions; the JLC
  fab package stays valid.
- **Backslash demotes to the FN layer as DIRECT bindings — FN+`]` = `\`,
  FN+`[` = `|`** (same pattern as `'` on FN+`;`). Pipe deliberately does NOT go
  through Shift: Shift+FN+] would be a three-key chord no thumb-pair can hold.
  Bracket caps get debossed Rii-blue sublegends (`|` and `\`).
- **Side-aware HID codes** in `gen_firmware.py` (`KC_RIGHT`): the right grip
  emits RCTRL/RSHFT/RALT so left/right modifiers stay distinguishable and AltGr
  keeps working under intl layouts. Previously `kc()` was side-agnostic.
- **No sticky/one-shot behaviors — deliberate.** All chords are plain holds;
  the modifier is held by the thumb opposite the target key. Same-side triples
  (Ctrl+Shift+letter) use the vertical corner Ctrl+Shift one-thumb bridge or an
  occasional cross-hand reach. Known residual gaps, accepted: Win+left-side
  combos (Win+E/D, Super+1–5) and left-grip FN-layer targets (BT select) need
  the cross-hand reach — BT is setup-time, Win combos are rare on this device.
- Stale-count cleanup: `gen_firmware.py` docstring and `sim_matrix.py` banner
  said 79 keys; the matrix has been 78 since the v0.17 2u-Enter change.
  `sim_matrix.py` re-run fresh: **78 keys (right 36 + left 42), 0 cross-grip
  collisions, 0 ghost/miss failures — PASS**.

## v0.19 — Game-Boy-Color rework: boxy outline, flush M3 screws, closed well (2026-07-17)

Driven by the user's print-test feedback (5 items) with a Game Boy Color as the
design-language reference (boxy rounded silhouette, Atomic-Purple translucent
shell, dark button-gray keys).

- **Outline (item 4):** the outer **parabolic cheek bow is deleted** — printed
  testing showed the widest part of the cheek blocks thumb reach to the
  edge-adjacent keys and top corners. The outer edge is now **straight** at a
  constant `grip_margin` (7.0 → 8.5: +1 for the fatter M3 boss column, +0.5 routing
  relief — at 8.0 Freerouting left 1-3 nets open every attempt), so
  boards go **79.493 → 75.0 mm** wide; corners: r_in 4.0 / **r_out_top 8.0**
  (antenna-pinned — the E73 keep-out forbids anything rounder) / **r_out_bot
  11.0**, plus a **1.0 mm parabolic bottom crown** (the GBC's convex bottom).
  Face cheek is now a constant ~11.4 mm (was 9.9–15.9 bowed). Device face
  width 330.6 → **325.5 mm** despite the wider spine (below).
- **Mount holes → M3 (item 1):** all 14 face screws are **M3×10 DIN 965
  countersunk, heads flush** with the face (proud M2 pan heads were
  uncomfortable). PCB holes Ø2.2 → **3.4** (boards unordered — free change),
  bosses Ø6/7 → **Ø7.5/8.0** with **Ø4.0 bores** for M3 heat-set inserts;
  lid plate **TOP_T 2.0 → 2.4** so the Ø6.2 countersink cone keeps ≥1.0 mm of
  land (face plane 14.3 → **14.7**; keymat plungers +0.4 to keep caps 1.0
  proud). Hole positions re-tuned for the fatter bosses (inner column x 3.2 →
  4.2, H3 y 77.6 → 72.0, outer column at edge−4.2, H5 y 67.9 → 68.0) against a
  **raised boss gate (r 3.0 → 4.0)** in gen_board/verify_alignment — at the old
  r 3.0 a real dome-courtyard clash would have shipped. The top electronics
  cluster's placement anchor is now a **frozen absolute** (AX 72.493), not
  board_w-derived — the narrower board slid a W-anchored cluster 5 mm inboard
  onto the PGUP/PGDN dome courtyards (caught by the C5 GND-escape assert).
- **Closed phone well (item 2):** the well's x-ends were open slots into the
  grip cavities (the v0.18 gap put the phone ends exactly AT the panel edges).
  The spine gap grows `2 × (0.35 well clearance + 1.6 end wall + 0.3 reveal)`
  = span_x + 4.5 (gap 165.8 → **169.7**), and the panel's well is a full
  **picture-frame** (explicit frame rect replaces the y-only buffer band).
  FFC jumper spec ≥190 → **≥194 mm** (J2 rows now 173.3 mm apart).
- **Thumb scallop → finger dish (item 3):** the R9 scallop cut used to punch
  through into the interior. Now a **curved backer** (R10.6 half-annulus wall +
  solid floor to z 6.0, clipped to the spine cavity −0.25) is unioned before
  the R9 re-cut: watertight, support-free in the panel's slab-down print, case
  edge still exposed ~17 mm for tip-out. Scallop centre moved 2.3 mm into the
  well; the top border screws moved to |x|=13 to clear the dish + Ø8 bosses.
- **Colors (item 5):** GLB shells switch from per-face concept colors to a real
  **glTF PBR material** — "atomic_purple", baseColorFactor linear [0.198,
  0.102, 0.381, 0.55], alphaMode BLEND, doubleSided (translucent purple with
  the guts visible); keymats **dark button gray**. The matplotlib renders
  mirror both (render_iso no longer forces alpha=1).
- **Boards re-routed from scratch** (outline + all 10 hole centers moved =
  Edge.Cuts change): gen_board → route.sh both sides → DRC 0/0 gate → fab
  re-export; sim_matrix / verify_alignment / verify_geometry re-run
  (verify_geometry's hole-to-key gate raised 3.0 → 7.9 c-c to encode the M3
  boss + dome-courtyard rule).

## Rii-follow: 2u Enter at the end of the right H-row (2026-07-15)

Following the Rii i8+'s wide Enter: the right grip's H-row (4th from the top) is
now **H J K L + a double-wide 2u ENT** — 5 caps spanning the 6-unit row width,
one dome under the wide cap (same construction as the 2u space bars). The
apostrophe gave up its physical spot: **`'` is now `&kp SQT` on FN+`;`** (the FN
layer already carried -, =, Home/End, PrtSc and the mouse moves).

- Key count **79 → 78** (right grip 37 → 36: 34 grid keys + PgUp/PgDn; left
  unchanged at 42); diodes likewise 78 (right board 36, refs D1–D36).
- **PCB, keymat and shells regenerated**; the right board **rerouted — still
  0 DRC violations / 0 unconnected** (left board untouched, 0/0); fab package
  re-exported (right BOM now 67 placements). Board dims unchanged (79.5 × 97.0).
- Firmware regenerated: 78 `RC()` transform entries, keymap carries `&kp SQT`
  on FN+`;`.
- Also in this pass: the keymat model carries **debossed Rii-style keycap
  legends** (primary legend + small shifted-symbol secondaries + FN-layer
  legends on 0/9/PgUp/PgDn/Del/;), and the assembled 3D model now includes the
  **M2 shell screws**.

## v0.18 — flush-screen phone well + battery to the left grip (2026-07-14)

Goal: an **S25 Ultra in a typical thin case** sits with its **screen surface flush
with the grip lids' keyboard face** — one continuous 14.3 mm-high front plane
(lids · panel border · screen), thumbs sweeping from glass onto keys with no step.
No change to the boards (no reroute); grips untouched.

- **The math.** Keyboard face (lid top) = z 14.3. Cased S25U = 8.2 + 1.2 case back
  = **9.4 mm** back-of-case → screen. So the phone must rest at z 4.9 — a
  **10.2 mm drop** from v0.17's 15.1. The center panel becomes a **sunken tray**:
  border flange 12.3..14.3 (flush with the lids), well floor at 4.7 with the same
  Ø57×1.8 MagSafe recess / 0.8 mm web / 0.2 mm-proud ring construction as before,
  translated down. Device thickness **22.9 → 15.3 mm** (keycap tops; the flat
  face is 14.3, the case lip sits ~0.4 proud of flush glass).
- **Phone dims got real.** The model carried placeholder iPhone dims (71.6 ×
  147.6); the flush stack forced the real **S25 Ultra (162.8 × 77.6 × 8.2) +
  case_t 1.2** into `deck.Config`. Consequence: the spine gap is sized to the
  cased length (165.2 + 0.6 clearance), so the device is **324.8 mm wide
  (+18.2)** — that is the phone's own size, not packaging growth; y-footprint
  (102.8) and grips unchanged.
- **Battery relocation: REQUIRED, not optional.** Under the sunken well's floor
  slab only **0.5 mm** remains above the back floor — no standard Li-Po exists
  that thin. Survey of the cavities: right grip has 0.24 mm spare (mated JST-PH),
  the **left grip (passive board: diodes 1.16 mm + the FFC ZIF) has 5.14 mm
  free**. The cell is now a **standard 403040 pouch (4.0 × 30 × 40 mm,
  ~450–500 mAh)** foam-taped (0.3 mm) to the left floor under the key field —
  0.84 mm below the diodes at nominal, ~0.4 mm at +10 % swell. 450–500 mAh is the
  capacity the README's own cell-size note preferred, and PROG (196 mA ≈ 0.43 C)
  needs no change. Support posts auto-route around the cell (it's an obstacle box
  in `support_post_locations`). Leads run left cavity → bottom-border lane (y≈5,
  outside the well) across the spine → J3 on the right board. Trade-off logged:
  battery replacement now means opening the left grip (5 screws + lid + keymat +
  board) instead of the panel hatch; the FFC stays panel-serviceable.
  > **⚠ The lead route is superseded by v0.27.** Nothing crosses the spine any more:
  > the cell plugs into **J4 in its own grip**, through **F1** (0.75 A PPTC), and
  > `VBAT_CELL` reaches the right board's charger over the bridge ribbon. The
  > left-grip-service trade-off below still stands.
- **FFC drops into a floor channel.** The ribbon crossed at z≈5.4 — inside the
  well now. A **0.5 mm recess in the back floor (19 mm lane at the J2 band)**
  gives it a 1.1..1.6 duct under the panel slab (0.5 mm headroom), S-bending down
  from each ZIF inside the grip cavities. The lower seam floor-tab moved
  30–38 → 36–44 so the channel doesn't thin it.
- **Transverse walls cut down to sills** (z 1.95) over the well span — the phone
  and the slab pass over them; full height outside the span still seats the
  border. The old ring-height Ø8 anchors are gone (their bores sit 8 mm above the
  new floor): MagSafe detach is held by the **4 border screws** + slab stiffness
  (~0.25 mm flex at 8 N), down-press by **4 floor nubs** under the slab. Panel
  screw count 6 → 4; **total M2×10: 16 → 14**.
- **Removal scallop.** With the phone sunk 9.4 mm, you can't pinch it — an R9
  thumb scallop in the top border exposes ~18 mm of case edge to tip it out
  against the ring.
- Phone x-retention is the grips' PCB/lid inner edges (0.3 mm clearance per
  side); y-retention the well's 2.0 mm wall band; alignment the MagSafe ring.

## v0.17 — Rii-height grips: chin cut + electronics to the top (2026-07-14)

Ergonomic feedback after printing the right grip lid: the grip (114.5 mm) was
significantly taller than the phone (~80 mm short-side) and than the Rii i8+ the
user thumb-types daily (~97 mm), the excess concentrated in a tall "chin" below the
bottom key row, and the 6-row field (55.5 mm) read taller than the i8+'s (~45 mm),
so the keys sat less within thumb reach. Goal: mimic the i8+'s proportions within
FDM + our-board limits — and since the **trackpad was dropped for v1**, the top zone
it would have occupied is free to reclaim.

- **Grip 114.5 → 97.0 mm** (the i8+ is ~97 mm); width 76.5 → 79.5 mm. Three levers:
  1. **Chin cut, `bottom_strip` 19 → 7 mm.** The 19 mm strip existed only to hold
     the E73 (18 mm) antenna-down at the bottom edge. With the module relocated
     (below), the chin under the space row drops ~23 → ~9 mm — the bulk of the excess.
  2. **Rectangular keys, `key` 8×8 → 8.5×7, `pitch` 9.5 → 10 (X) / 9 (Y).** The i8+
     keeps a short field with wider-than-tall chiclets; ours follow. The 7 mm domes
     (contact courtyard r3.9) still clear at 9 mm Y-pitch (1.2 mm courtyard gap);
     gutters stay ≥1.5 mm (X) / 2.0 mm (Y) for PETG-FDM. Field 55.5 → 52 mm.
  3. **Electronics to the top zone.** The E73 + the whole power front-end (USB-C,
     charger, ESD, reset/power switches, JST, passives, SWD/I²C pads) move from the
     old bottom strip up into the vacated trackpad space, implemented as a rigid
     180° rotation of the DRC-verified rev-A cluster about the board centre
     (`gen_board`'s `P()`/`xf()` involution), so the hand-routed USB fan-in copper
     carries along unchanged rather than being re-derived.
- **Antenna-up at the top edge.** The rotation lands the E73 antenna at the
  CENTRE-top edge — farthest from the centred phone/LiPo, and off the edge the palm
  (which cradles the bottom) doesn't cover. RF is a judgment call vs the old
  antenna-down: hand-detune should improve, phone/battery proximity is similar —
  **re-check range on the first article.** A small inward shift (`DX = 7`) keeps the
  13 mm module off the rounded corner; the JST is placed separately in the chin (its
  rotated pose hit the inner-top page keys); PgUp/PgDn move to the inner-top corner.
- **Top-outer corner sharpened, r_out 14 → 10** (bottom stays 14 for the palm) so
  the top cluster clears the corner — and squarer "shoulders" read more like the i8+.
- **Both boards re-routed 0/0** (KiCad 9, error-severity DRC + 0 unconnected); the
  fab package, firmware (byte-identical — the matrix/pin-map is unchanged) and all 2D
  renders are regenerated. Routing is tighter than rev-A (module-top / bridge-bottom
  puts the 14 bridge nets across the board); `route.sh` is a route-until-clean loop
  and hit 0/0 within a few passes.
- **Switch re-evaluated and KEPT: Snaptron 7 mm 4-leg dome** (2026-07-14 review,
  triggered by the rectangular-cap change). It verifiably fits the new geometry —
  courtyard Ø7.8 vs 9.0 mm Y-pitch = 1.2 mm gap (0.7 mm at the 8.5 mm cluster
  pitch), Ø2.8 nub presses every dome dead-centre (cap centre = dome centre for all
  79 keys incl. the 2u space), and both boards are routed 0/0 around this exact
  footprint. Alternatives lose: 8.4 mm domes physically don't fit the pitch; 5–6 mm
  domes give up travel/centre-hit tolerance under an 8.5 mm cap; LCSC SMD tacts
  (TS-1088 etc.) add 1.0–2.6 mm of z-stack (dome is 0.5 mm), 79 fab-soldered parts,
  and a full reroute. The fab's role is unchanged either way: ENIG gold pads only —
  domes press on at assembly. **Actionable:** sample LIGHT-force (~160–180 gf trip)
  4-leg domes, not the 400+ gf GX class, to approximate the i8+'s light feel.
- **3D regenerated for v0.17** (same session, after review): `deck3d.py` updated —
  keymat plungers/lid openings are now the real **rounded-rect 8.5 × 7 caps** (18.5
  for the 2u space; cluster keys stay round), the USB-C opening / power-switch slot /
  antenna wall relief moved to the TOP wall, the slide-switch knob direction is
  derived from the placed rotation, and the 4 panel seam screws are derived from the
  phone-pocket span (the old hardcoded y=105 was off the 97 mm shell entirely, and
  y=10 clipped the new pocket rim). The antenna wall stays CLOSED — 1.9 mm of PETG
  remains over the relieved span; the antenna radiates through plastic, not a hole.
  Also fixed a **latent v0.16 keymat bug the regen render exposed**: the cluster
  plungers (PgUp/PgDn, D-pad, mouse pair) sat outside the web buffer's reach — the
  "one-piece" keymat was really 3+ floating pieces. The web now grows the **3 mm
  living-hinge strips** the 2D concept always drew (each feature → nearest grid key
  + nearest other feature) and asserts single-polygon connectivity at build time.
  Also fixed: `deck.product()` origin rounding 2 → 3 decimals (a 79.493 mm board_w
  put the left grip 0.003 mm off the seam and tripped deck3d's frame assert).
- **Adversarial alignment audit (machine-verified, 2026-07-14):** all 79 domes sit
  at model key centres with 0.0 µm deviation on both boards; diodes at +3.0 mm; min
  dome courtyard spacing 9.0/8.5 mm vs the 7.8 floor; every non-dome footprint is
  back-mounted. Two margins worth knowing: (1) the cap Y-dimension (7.0) exactly
  equals the dome diameter — zero cover margin, so keymat registration (screw bosses
  + clamp rim) is what keeps the dome edge hidden; (2) the USB-C shield stakes and
  the J1/SW90 locating pegs protrude through to the PCB FRONT in the top zone —
  they clear the keymat web by ~8.4 mm and sit below the lid plate, but any rev-B
  front-side feature near x 31–40, y 90–95 must account for them.

## v0.16 — 5-part shell split for a 220 mm bed (2026-07-13)

Concept change from the sketches (`sketches/All.png`, `top_shell.png`, `side.png`):
the front is **two cyan grip lids** and a **pink center panel** that is visually
"the front of the back"; the back stays pink. Driver: the one-piece shells were
306 × 120 mm — they don't fit a Creality **Ender 3 V2 (220 × 220)** at any
rotation (min enclosing square ~302 mm); the target printer is now first-class.

- **Part set: 5 shells** — `back_left` + `back_right` (tray split at x=0 mid-
  spine, ~161/153 × 120 mm), `grip_lid_left/right` (~79 × 120), `center_panel`
  (~147 × 120). `deck3d.py --all` gates every part on **bbox ≤ 204 mm** (220 −
  2×8 brim). Keymats unchanged.
- **Staggered splices** — the bolted-on panel bridges the back seam at x=0; the
  continuous back halves bridge the front seams at the grip edges: every
  cross-section keeps one uncut structural member.
- **Back seam is screwless printed joinery** (adversarial design review killed
  the lap-screw variant: M2 inserts don't fit a 0.8 mm floor flap, and a
  horizontal lap is a 120 mm unprintable one-sided cantilever): floor butt +
  two full-thickness tabs into cleared notches, an 8 mm **vertical shiplap** in
  each perimeter wall (vertical faces print clean; 0.25 mm clearances), and a
  0.4 mm 45° outer V-groove = elephant-foot relief + intentional shadow line.
- **Panel/lid joint is a 0.3 mm open reveal, no overlap** — a shiplap/rebate
  here either lands on the inner lid screw heads (3.2 mm from the grip edge,
  fab-locked) or creates more mid-air mating faces; the reveal needs neither.
  Both edges get 0.8 mm 45° chamfers, so the seam reads as a design line.
- **Transverse spine wall at each grip boundary** (new, in each back half):
  closes each half's torsion box where the front plate is now cut, seats the
  panel edge, and carries a **Ø8 boss at MagSafe-ring height** — phone-detach
  pull anchors in line with the ring instead of peeling the panel. FFC and
  battery-lead windows are cut from the placed J2/J3 positions. *(⚠ v0.27: there are no
  battery-lead windows and no J3; the one remaining window is the FFC duct.)*
- **Panel plate 2.0 → 2.6 mm**: the Ø57 ring recess now leaves a **0.8 mm
  (4-layer) web** instead of one 0.2 mm layer; ring still sits 0.2 mm proud;
  spine grows 16.3 → 16.9 mm. Panel = spine **service hatch**: 6 screws expose
  battery + FFC without touching the grips.
- **Fasteners: 10 → 16 M2 (one SKU, M2×10 button-head)** — grips keep their 5
  per side untouched; the panel adds 4 floor bosses straddling the back seam +
  the 2 ring-height wall bosses.
- **Fixed en route:** `battery_body()` modeled the 503450 pouch rotated 90°
  (34 × 50 overflowed the 52 × 36 reserved rect y-span); `--sync-models` now
  refreshes the tracked `hardware/cad/models/` STLs (they had gone stale/orphan).
- `deck3d.py --check` = **0 collisions** (203 bodies); back-seam interpenetration
  asserted 0.000 mm³; both cosmetic faces verified flat for their print
  orientation.

## v0.15 / rev-A — the production audit pass (2026-07-11)

An 8-dimension adversarial audit (120 findings, 14 blockers) followed by fixes,
a fully autonomous route (both boards **DRC-clean, 0/0**), fab export, firmware
repair and a mechanical re-verify. Full record in
[design-review.md](design-review.md); status in [evaluation.md](evaluation.md).

- **Snap-dome footprint → production `snaptron_7mm_contact`** (centre pad +
  continuous leg ring with a 67.5° routing escape gap, pour/via keepouts, tape-
  channel venting). The simple 2-pad proxy would have given dead keys at 45° dome
  rotation.
- **E73 antenna-down at the bottom board edge**, keep-out crossing the edge +
  0.6 mm shell relief (was aimed mid-board at the USB shell — detuned).
- **Bridge → 2× 16-pin 1.0 mm FFC ZIF (AFA07-S16FCC-00, C13744) + a 16-way
  1.0 mm type-A (same-side contacts) jumper, length ≥160 mm** (200 mm is the
  common stock length, e.g. "FFC-1.0-16P-200mm" type A — the J2 contact rows are
  151.2 mm apart + ~4 mm ZIF insertion per end, so 150 mm cannot mate); left-grip
  nets assigned by ribbon geometry (straight
  jumper correct by construction). Replaces the 2×08 THT header that couldn't fit
  the shell cavity (8.5 vs 5.7 mm), overhung the right edge and landed under a
  left-grip dome. **No hand-soldered parts remain** — the USB-C shell's plated
  stakes and the FFC/slide-switch locating pegs are the only through-board
  features, all placed in the same single-pass JLC assembly → 100 % turnkey.
- **Battery: JST-PH SMT (C295747)**, polarized (was an unpolarized 2.54 header);
  **NEW** MSK12C02 power switch (charger on the cell side — charges while off),
  TS-1187A reset tact behind a floor pinhole, charge LED behind a floor light
  hole.
- **Charger corrected per datasheet:** 4.7 µF 0805 25 V at both supply and cell
  nodes, at the chip; PROG 5.1 k → ~196 mA. 100 nF SAADC filter added to the
  battery divider.
- **USB ESD inline; deterministic USB copper** for the interleaved data pads
  (autorouters can't solve it). **COL9 off P0.00/XL1 → P0.04**; spare I²C to
  TP6–8; SWD on TP1–5.
- **Trackpad dropped from v1** (single-maintainer ZMK Azoteq driver + ATI tuning
  burden); D-pad + FN-layer mouse keys cover pointer duty; TP6–8 keep rev-B open.
  Column series R + dome-field TVS dropped from the BOM (telescoping-cable-era
  artifacts; rev-B option).
- **Boards 76.5 × 114.5 mm** (inner margin 6→8 for the FFC, bottom strip 14→19
  for module-at-edge + passive lane), 4-layer with solid In1 GND; **GND escape
  vias + obstacle-aware stitcher** make the headless route loop converge to 0/0.
- **Fabrication: two separate JLC orders** (panelizing two designs costs more);
  right = Standard (E73 X-ray), left = Economic-eligible.
- **Firmware:** ZMK **pinned to v0.3.0** (main dropped HWMv1 boards); LF clock
  from internal RC (**the E73 has no 32 kHz crystal** — without this BLE never
  starts); DCDC config removed (module has no inductors; LDO correct); flash
  partitions = exact Adafruit/nice!nano-v2 bootloader layout; board moved to
  `config/boards/arm/thumbdeck`; FN layer gained MINUS/EQUAL, HOME/END, PSCRN,
  BT controls, bootloader/sys_reset.
- **Mechanical:** back cavity 5.7→6.3 mm (mated JST-PH + 0.24 margin); 3 support
  posts per grip under the key field; top-shell rim clamps the keymat web
  (0.1 mm preload); phone pocket in a raised spine plateau with a Ø57×1.8
  MagSafe-ring recess; USB-C/switch/pinhole/LED openings cut from real part
  placement. `deck3d.py --check` = 0 collisions.

## v0.13 — printable spacing, 2u space bar, cluster fixes

- **Pitch 8.5/8.8 → 9.5 mm (#5).** At 8.5 mm the inter-key wall was only ~0.5 mm —
  **not printable in PETG-FDM** (needs ≥1.2–1.6 mm = 3–4 perimeters at a 0.4 mm nozzle).
  9.5 mm gives a ~1.5 mm wall, and matches the i8+ pitch. Grips grow to 74.5 × 109.5 mm.
  (To go tighter you'd print the keymat/shell in resin/SLA or use a 0.25 mm nozzle.)
- **Double-wide 2u space bar (#4).** The MENU key is dropped and the bottom row shifts
  over one, so the inner key is a **2u space** on each side (`SPC AGR [ ] \` right,
  `SPC ALT WIN FN CTL` left). The dome stays single under the wide keycap. Keys now
  carry a `w` (width in units); `_key_centers` lays each row out by cumulative units.
- **D-pad no longer overlaps the F-row (#2).** The upper zone is sized to fully clear
  the plus-cluster and the clusters are centred in it (previously an offset pushed
  NAV_D down into the grid).
- **Screw no longer passes through the bridge (#1).** The bottom-inner mount hole moved
  below the vertical JST-GH connector.
- **Every cluster keycap ties into the keymat web (#3).** The one-piece keymat now
  draws living-hinge strips from each D-pad / mouse / page key to its nearest grid key
  and nearest neighbour, so nothing floats.
- Verified programmatically: no keycap overlaps, nothing off-board, no screw inside any
  keep-out, both grips.

## v0.12 — outline-clamped placement, layer-correct traces, PCB antenna

- **Nothing hangs off the board.** All right-grip electronics (module, charger,
  USB-C, antenna) and the two outer mount holes are now **clamped inside the actual
  rounded/bowed outline** via `_right_edge_x()`, instead of being referenced to
  `outer_base` (which sits outside the corner). Electronics moved into the **bottom
  zone**; the trackpad has the upper zone to itself (clean capacitance).
- **Layer-correct matrix (Rii i8+ topology).** Front copper = **vertical columns**
  (over the keys) + inner-margin **row feeders**; back copper = **horizontal rows** +
  diodes + chips. The two layers connect **only through vias** (drawn at every key and
  at each row's inner end), so nothing shorts — the earlier diagonal "airwire" fan
  that crossed the row buses is gone. Power traces are short and local to the bottom
  cluster.
- **PCB meander antenna** (fat squiggle on the front, with a **ground cut-out** on the
  back) drawn in the outer-bottom corner, far from the centre magnets. **OPEN
  DECISION:** a board antenna means going **chip-down** (a module carries its own
  antenna) — chip-down is cheaper and gives the free squiggle, but re-adds RF
  match/tuning + crystals + DC-DC + bootloader, and (only if ever *sold*) FCC/IC/RED
  radiated cert. For a personal, non-marketed build the cert isn't required, so the
  real cost is RF tuning + assembly complexity. Keep the certified E73 module (its own
  antenna) unless you want to take that on.

## v0.11 — trackpad-on-PCB, battery-behind-ring, straight bridge, cleanup

- **Trackpad → PCB-integrated capacitive pad** (~34×26 mm copper on the front, driven
  by an **Azoteq IQS7211E** controller on the back), replacing the 43×40 mm TPS43
  module. It now **fits the grip** (no overhang) *and* is **turnkey-friendly** — the
  pad is free copper and the controller reflows with everything else, so the trackpad
  no longer has to be dropped for assembly. Trade: needs the community Azoteq ZMK input
  driver (vs the in-tree Cirque one).
- **Battery stack-up fixed:** the LiPo sits **inside the spine, directly behind the
  MagSafe ring** (sandwiched between back and front shells). The **N52 ring is applied
  to the outside of the front shell** (top of the stack); the phone mates to it.
- **Bridge connectors rotated vertical** at each grip's inner edge so the flex exits
  toward the spine and runs **straight across** to the mirror connector, clearing the
  spine battery above it.
- **Chip-interconnect traces** are now drawn (indicatively) on the PCB layers: module →
  rows / USB-C / charger / ESD / IQS7211E / bridge; passive grip rows → bridge.
- **Repo cleanup:** old 50-key design-loop scripts moved to `hardware/scripts/legacy/`;
  grading artifacts + the superseded front/back render archived to `renders/history/`.

## v0.10 — proportions, spine battery, rectangular trackpad, layer set

- **LiPo → central spine** (behind the phone / MagSafe ring), out of the grips. Short
  wire to the right-grip charger; it does **not** cross the left bridge, so the
  battery-across-flex risk still doesn't apply. This lets the grips shrink from
  **118 → 102 mm** so the ~72 mm (landscape) phone is no longer dwarfed (~15 mm
  overhang/side, matching the i8+).
- **Trackpad → Azoteq TPS43** (43×40 mm **rectangular** I²C module, 40 µA active, sold
  maker-ready). Still optional; sits as a **shoulder-bump** over the upper-right grip
  (its 40 mm height overhangs the top rather than forcing the whole grip taller).
- **Stackable layer renders** (`render_layers.py`): back_shell · pcb_back · pcb_front ·
  keymats · front_shell, all on one 2400×1050 canvas for overlay/animation.

## v0.9 — landscape, turnkey sourcing, and shell-readiness

- **Phone orientation → LANDSCAPE.** The phone's long side spans horizontally
  between the grips (Steam-Deck posture); device is now ~287 mm wide. `deck.product()`
  handles orientation.
- **MCU module → Ebyte E73-2G4M08S1C** (JLC C356849), replacing the Raytac MDBT50Q,
  because the Raytac was out of stock / not reliably JLC-placeable. The E73 is in the
  JLC library, is the community-standard ZMK nRF52840 module, and machine-places.
- **Trackpad dropped from the turnkey build** (kept as an optional, dashed, hand-fit
  I²C header). The host is a phone with its own touchscreen; the Cirque isn't LCSC-
  stocked (hand-assembled anyway), and enabling ZMK pointing forces a HID re-pair on
  every host. This resolves the crowded upper-right zone too.
- **Turnkey assembly = JLCPCB, single-sided (all reflow parts on the BACK), L+R
  panelized.** ~$150–230 for 5 sets vs ~$300–600 at PCBWay. Domes + retention sheet +
  LiPo + shell are hand steps at either house (snap domes can't be reflowed). Full
  costing, LCSC part numbers and open decisions in [fabrication-sourcing.md](fabrication-sourcing.md).
- **Shell-readiness (emulate i8+):** 5× M2 screws per grip clamp the keymat perimeter
  evenly (consistent dome feel), placed in the inner column + top/bottom strips, clear
  of the key field; every key/cluster is ≥6.5 mm from the board edge (shell wall +
  keycap skirt); USB-C on the outer-bottom edge; module + all SMD on the back. This
  preps the board for the next step — the 3D shell + keymat models.

## v0.8 — phone target, MagSafe, module, and a 5-lens EE/PD review

Big shifts from v0.3–0.7: target is a **phone** (MagSafe centre-mount), telescoping
is **deferred** for a **fixed one-piece shell**, switches are **Snaptron 7 mm snap
domes** on a one-piece 3D-printed keymat (adopted from PocketMage), the grid grew to
**6×6/half + clusters** (~81 keys) validated against the Rii i8+ the user thumb-types,
and a trackpad + D-pad + mouse buttons returned. A background workflow ran a
**5-lens review** (digital EE, RF/power EE, product/ergonomics, DFM, firmware). Its
decision record, adopted:

| Topic | Decision | Why (short) |
|---|---|---|
| **MCU** | **Raytac MDBT50Q-1MV2 module**, *not* chip-down bare nRF52840 | Chip-down triggers FCC/IC/RED radiated cert + RF match + crystals/DC-DC + USB bootloader + Zephyr port. Module gives certified radio + ~48 GPIO (need ~23) + UF2. |
| **GPIO** | Budget ~23: 19 matrix + 2 I²C + 1 Cirque DR-IRQ + 1 batt ADC | Confirms the pin-starved nice!nano was the real problem, solved by a full-pinout module — not by chip-down. |
| **Battery** | LiPo + charger + USB-C + MCU **all in the right grip**; ballast the left | Cell across the bridge = chafe-to-short fire + charge IR-drop undercharge + ground coupling into the SAADC/scan. Only logic crosses the bridge. |
| **Power front-end** | Add MCP73831 charger + PROG R, USB-C **2× 5.1 kΩ CC**, USBLC6-2 ESD, ÷2 batt divider, VDDH wiring, SWD pads | A module hides crystals/DC-DC/antenna but **not** the charger, CC resistors, ESD or divider. Their absence = won't charge / over-VDD / unflashable. |
| **Matrix** | Single 9×10, passive left, per-key **SOD-323** `col2row`, NKRO best-effort | Unibody single kscan over a cable (NOT a ZMK split). Diodes de-ghost modifiers even though BLE boot is 6KRO. Standardise SOD-323 (drop SOD-123). |
| **Bridge** | Static internal harness, **JST-GH ≥15 pos**, signals only, ~22–24 conductors w/ ground interleave | Fixed shell ⇒ assembled-once harness (no flex-fatigue). One GND can't shield 9 sense lines; power stays with the MCU. |
| **Trackpad** | **Cirque TM023023 (23 mm)**, I²C 0x2A, **DR-IRQ wake** (not polled), flat ≤2 mm non-conductive overlay | 30 mm isn't a catalog size. Polling collapses runtime to ~28 h; conductive/variable FDM overlay kills sensing. |
| **PCB finish** | **ENIG** (hard gold on dome pads for production), not HASL | Snap domes shorting bare pads need gold; HASL oxidises → rising contact resistance in weeks. |
| **Dome retention** | Add taped-polyimide dome array / laser-cut spacer | Keymat alone doesn't laterally retain a dome on its single ~1.4 mm arc; ~0.5 mm walk = dead key. |
| **Keymat** | TPU 95A / tough resin; fatigue-test a hinge coupon >10 k cycles | Non-TPU living hinges at ~0.5 mm webs crack early; boss preload must be shimmed. |
| **MagSafe** | Alignment only + **mechanical edge-capture** on 2+ edges | Magnets alone shed peel/torque on a waved handheld. |

### Open questions (need a human call — see README §Open questions)

- **Pitch/feel:** keep 8.5 mm flat ortho, or go ≥9.5 mm canted/fanned arc (i8+-like) via a switch daughter-PCB / standoff-canted mat? The review says the flat rigid plane can't both type well and feel like a controller.
- **Phone-fit:** fixed shell = ~145–160 mm band (≈ one phone family); accept, or bring back telescoping for multi-phone?
- **NKRO vs simplicity:** if 6KRO is fine, dropping diodes enables a TCA8418 local scanner + a 4-wire bridge.
- **Shoulder/bumper buttons** for index fingers? Changes the matrix + conductor count.
- **Cell size:** sleep-managed runtime is weeks → a 400–500 mAh cell may pack better than 700 mAh.

## v0.3 — the architecture pivot (single controller)

**Decision:** one nRF52840 in the right grip; the left grip is a passive matrix
wired over the bridge. This *replaces* v0.2's two-controller ZMK BLE split.

**Why:** the halves are joined by a telescoping bridge, so a cable through it is
simpler than a wireless link between them — which is exactly how real Backbone-
style controllers are built (single MCU + battery + radio; the other grip wired
across). The two-controller split was borrowed from desk split-keyboards, where
the halves are physically separate; it doesn't fit a bridged phone controller.

**What it buys:** one battery, one USB-C, **one charge session**, ~half the BOM,
lower latency, no inter-half pairing, and *simpler* firmware (a plain 50-key
keyboard, no split/`col-offset`/battery-proxy).

**What it costs:** GPIO — one MCU must scan 50 keys (15 pins). Resolved by moving
the default board **XIAO nRF52840 → nice!nano v2** (~18 usable GPIO). Optional
MCP23017 I²C expander in the left grip reduces the bridge to 4 wires. The one
property given up — halves that fully detach with zero electrical link — isn't a
real requirement for something that clamps a phone.

## Locked decisions (updated for v0.3)

| Area | Decision |
|---|---|
| Form factor | Two grips, Backbone-clamp style, flanking a phone. 3D shell = user's later work; PCB exposes mount + bridge features. |
| Reference look | i8+-inspired QWERTY, split L/R. Keys-only (touchpad = `TODO(user)`). |
| Switches | Xiaoyztan 5×5×1.5 mm 4-terminal SMD tact (owned). Treated as 2-terminal SPST. |
| **Controller** | **One nRF52840 (nice!nano v2)** in the right grip. |
| **Left grip** | **Passive** 5×5 matrix (switches + diodes), wired over the bridge. |
| **Connectivity** | BLE **or** USB-C wired HID, from the single controller. |
| **Power** | **One LiPo**, one USB-C charge, nice!nano onboard charger. |
| **Matrix** | Single 5×10 (no split). Cols 0–4 right grip, 5–9 left grip. `col2row`, 1N4148W. |
| Firmware | ZMK, single non-split shield `thumbdeck` on `nice_nano_v2`. |
| Fabrication | JLCPCB, 1.6 mm, HASL, gerbers from KiCad. |

## Decisions carried from the layout loop

- **Real pins.** rows `pro_micro 4,5,6,7,8`; cols `9,10,14,15,16` (right) +
  `18,19,20,21,1` (left, over bridge). All in the nice!nano `pro_micro` set;
  15 of ~18, leaving `0,2,3` (2/3 = I²C for the expander option).
- **Left-half legends pre-reversed** so the mirrored render reads naturally
  ("1 2 3 4 5", "Q W E R T"). `matrix_map.py` asserts legends == keymap.
- **Board geometry.** 63 × 108 mm per grip, symmetric D-shape (flat inner mating
  edge + bowed outer). Both grips same outline (symmetric phone clamp); keep-outs
  differ by role. Bridge connector at the inner-bottom corner of each grip.
- **Render path.** matplotlib PNG (no KiCad in this env); board file is
  hand-authored KiCad S-expression.
- **License:** Apache License 2.0. Chosen over MIT for the explicit **patent
  grant** (§3) and the explicit **inbound contribution terms** (§5) — both matter
  for a hardware-adjacent project that ships fabricable board files and invites
  outside build reports. It also states attribution/NOTICE handling explicitly,
  which is what carries the vendored third-party footprint attribution
  (marbastlib, CERN-OHL-2.0-P) cleanly alongside the original work.

## History: v0.2 (superseded)

v0.2 was a ZMK **BLE split** — two XIAO nRF52840s (right=central, left=peripheral),
a 50-key combined transform with a peripheral `col-offset`, and a LiPo + USB-C per
half. It graded PASS but was more complex than this form factor needs. See the git
history and `renders/history/iter_03.png`.

## Open `TODO(user)` — historical (v0.3 era), all resolved by rev-A

Kept for the record only; every item below was closed by the rev-A design (see
the v0.15 entry at the top): production dome footprint, fully routed/DRC-clean
boards, FFC ZIF bridge with a defined pinout, spine LiPo, printed keymats, 3D
shells, and a layout validated against the i8+.

- Datasheet-verified switch footprint (before gerbers).
- Copper routing in KiCad (before gerbers), incl. the bridge connector pinout.
- Bridge cable + connector choice (10-pin FPC/JST, or MCP23017 → 4-wire).
- LiPo capacity vs. shell space (~100–150 mAh assumed).
- Keycap/top solution; touchpad (would use the nice!nano's spare GPIO / I²C).
- 3D clamp + bridge shell geometry (out of scope here).
- Confirm key count/reach against a real i8+ and your thumb span.
