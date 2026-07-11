# Reference notes — Rii i8+ (loop Step 0)

Layout observations recorded to guide the render. Described, not copied — no
images imported.

> **Historical document.** The i8+ observations below are still the reference,
> but the "How thumbdeck reinterprets it" section describes the **v0.3 50-key**
> reduction and is **superseded**: the current design is **79 keys** (9×10
> matrix, 6×6/half + clusters, 2u space bars), a D-pad + OK + mouse buttons on
> the left, PgUp/PgDn on the right, and **no trackpad in v1** (rev-B option via
> the I²C breakout). See the [README](../README.md) and
> [evaluation.md](evaluation.md) for the current layout.

## The real i8+ (from product listings / manuals)

- **~92 backlit keys** around a compact **QWERTY** block, US layout available.
- Integrated **high-sensitivity touchpad** (360° flip design, adjustable DPI;
  1-finger = left click, 2-finger = right click, 2-finger drag = scroll).
- Multimedia + PC-gaming control keys; many keys have **Fn** secondary functions
  (e.g. Fn+Space = DPI, Fn+F6 = lock keys/touchpad).
- **LED backlit**, rechargeable **Li-ion** battery, ergonomic **handheld**
  (thumb-typed) form factor.
- Rounded outer corners; QWERTY block centre with modifier/arrow/function
  clusters around it; touchpad at top.

Sources: riitek.com product pages; The Pi Hut; Amazon listings; Windows Central review.

## How thumbdeck reinterprets it (v0.3 — HISTORICAL, superseded)

The i8+ is a single ~92-key slab thumb-typed with both thumbs. **thumbdeck** is
an *i8+-inspired* reduction, not a faithful half:

- **50 keys total, 25/half** (5×5). The i8+'s 92 keys don't survive a literal
  split into two thumb grips; 25/half is the reach-friendly subset.
- **QWERTY split down the middle:** left = `1-5 / QWERT / ASDFG / ZXCVB` +
  modifiers; right = `6-0 / YUIOP / HJKL-ENT / NM,./` + an arrow/thumb cluster.
- Inner (split) columns are the QWERTY centre (T↔Y, 5↔6); outer columns are the
  pinky side — matching how the i8+ block reads across the middle.
- **Touchpad omitted** by default (i8+ has one). `TODO(user)`: add an I²C trackpad
  + ZMK input listener if wanted.
- Rounded outer / grip corners kept; straight inner edge added for the clamp.

`TODO(user)`: confirm the key subset and per-thumb reach against a real i8+.
