# hardware/footprints — switch footprint (SCAFFOLD, `TODO(user)`)

The Xiaoyztan **5 × 5 × 1.5 mm 4-terminal SMD tact** switch is the one gate that
blocks a fab order. Its four legs are **shorted internally in pairs** → treat it
as a **2-terminal SPST** (short the two pads that belong together, use the pair
as one net node into the diode/matrix).

## Do NOT hardcode dimensions from memory

The generated board (`hardware/kicad/generated/*.kicad_pcb`) marks each switch
position with a **provisional** placement guide, not a verified footprint. Before
you route or order:

1. Measure the real part (or pull the manufacturer datasheet). Record:
   - pad count/arrangement (4 pads; which two are internally common),
   - pad size + spacing (X/Y pitch),
   - courtyard / keep-out,
   - actuator/plunger centre (for keycap alignment).
2. Build the footprint in KiCad (`Footprint Editor`), or adapt a known
   5×5 4-pin SMD tact footprint **only after confirming it matches**.
3. Save it here as `xiaoyztan_5x5_tact.kicad_mod` and assign it in the schematic.

## Verified dimensions (fill these in)

```
TODO(user): pad pitch X = ____ mm
TODO(user): pad pitch Y = ____ mm
TODO(user): pad size    = ____ x ____ mm
TODO(user): body        = 5.0 x 5.0 x 1.5 mm (confirm)
TODO(user): common pads = (which legs are internally shorted?)
```

HASL finish is fine (SMD legs, no bare carbon pads — ENIG was only for the
abandoned carbon-pad idea).
