# Fabrication & sourcing — JLCPCB vs PCBWay (v0.9)

**Recommendation: JLCPCB Standard PCBA, single-sided (all reflow parts on the
back), left+right panelized into one panel.** For the minimum run this is roughly
**$150–230 all-in delivered for 5 sets** vs **~$300–600 at PCBWay**. The only reason
to pick PCBWay is if you want the *fab* to press the Snaptron retention sheet for you
(a quote-only manual step that roughly doubles cost) — otherwise you press the domes
in yourself at either house.

Derived from a 5-agent sourcing review (JLC, PCBWay, LCSC availability, assembly
strategy). Prices are indicative 2026 figures — re-quote before ordering.

## Why the domes/trackpad can't be turnkey
Snap domes are **mechanical spring contacts** — they oxidise/warp in a reflow oven,
so **no house machine-places them**. The Cirque is a **connectorized sub-module**,
also not reflowable. So the split is always:

| Stage | Parts | Who |
|---|---|---|
| SMT reflow (single-sided, **back**) | Ebyte E73 module · 81× SOD-323 diodes · ~20–40 passives · USB-C · MCP73831 · USBLC6-2 · JST-GH · SMD LiPo connector | **fab SMT line (~95–100% of joints)** |
| Mechanical | press 81 domes under the Snaptron **Peel-N-Place** retention array · laminate keymat · mate LiPo · close shell · (optional trackpad) | **you** |

## Part changes to make it turnkey (from → to)

| Part | From | To (LCSC/JLC) | Why |
|---|---|---|---|
| **nRF52840 module** | Raytac MDBT50Q-1MV2 | **Ebyte E73-2G4M08S1C** (C356849) | Raytac was **out of stock** / not reliably JLC-placeable. E73 is in the JLC library, is the community-standard ZMK module, and machine-places. **The change that enables turnkey.** *(Backup: Holyiot 18010/22066.)* |
| **Trackpad** | Cirque TM023023 FFC module | **PCB-integrated pad + Azoteq IQS7211E** controller | v0.11: a copper pad on the front + one SMD controller on the back **is turnkey-assemblable** (unlike a Cirque FFC module, which can't be reflowed) and any size we want. No hand-assembly step. Trade: needs the community Azoteq ZMK driver. |
| **Diode** | generic 1N4148WS | **1N4148WS SOD-323, C2128** (Basic) | Basic part → cheapest tier, no extended-feeder fee (feeder billed once per unique part, not per placement). |
| **USB-C** | unspecified | **fully-SMD 16P, C165948** | A THT-shell USB-C adds $3.50/order + $0.017/joint and breaks 100 % reflow. |
| **Charger** | MCP73831 (generic) | **MCP73831T-2ACI/OT, C424093** | Correct 4.2 V-regulation variant; library-placeable. Don't sub the -2ATI (different Vreg). |
| **ESD** | USBLC6-2 | **USBLC6-2SC6, C7519** | Library part. |
| **Bridge** | 1× ≥15-pos JST-GH | **confirm SMD GH; likely 2× SM10B-GHS-TB (C2683602)** | Placeable GH tops out ~10-pin — split (or reduce pins) to stay machine-placeable; must be top-entry **SMD**, not THT. |
| **Layout** | mixed sides | **all reflow parts on the BACK** | Front carries zero reflow parts (domes only), so single-sided SMT = one stencil/paste/pass/setup (~$25 vs $50). Biggest cost lever after part choice. |
| **LiPo connector** | hand-wired leads | **SMD JST battery connector** | Moves the battery joint onto the line; only the cell mate-up stays manual. |

## Cost (minimum run, 5× of each grip, panelized)

- **JLCPCB ~$150–230 delivered:** PCB+ENIG ~$25–45 · assembly setup $25 (single-side)
  · stencil ~$8 · extended feeders ~$5–6 · placement ~$2 · module X-ray ~$3–16 ·
  components ~$85 (the E73 at ~$6×10 dominates) · shipping ~$20–30.
- **PCBWay ~$300–600:** ENIG ~$40–70 · stencil ~$10–30 · SMT labor ~$60–125 · parts
  at cost (verify — a report saw ~2× markup) · **+** the reason to choose them:
  quote-only manual dome-sheet application.
- **Both exclude** the domes+retention sheet, LiPo, shell, and the (dropped) trackpad.

## Open decisions (these pick the house / finalize the order)
1. **Domes:** press them yourself → **JLCPCB** (cheapest), or have the fab apply the
   retention sheet → **PCBWay** (quote-only, ~2×). *This single choice picks the house.*
2. **Panelize** L+R into one panel (pay setup/stencil once)? — cost-optimal default **yes**.
3. **Trackpad:** drop (recommended, unpopulated footprint) or keep as a hand-fit option?
4. **Bridge pin count:** confirm exact count; split into 2× SM10B-GHS-TB or keep ≤10 so it stays SMD-placeable.
5. **Which grip hosts the module** (only one gets the module + X-ray fixture cost).
6. **Domes as a Peel-N-Place array** (one-sheet application) not loose domes.
7. **Plain ENIG** on dome pads (cheap, sufficient) vs selective hard gold (quote-only, only for very high actuation counts).

## Caveats
- **Verify E73 stock and reserve it** (only ~42 units at check; Extended, X-ray-required).
- A ≥15-pos JST-GH SMD single part may not be stocked — plan to split.
- Every **through-hole** joint breaks 100 % reflow — confirm each connector shows **SMD**.
- **ENIG is mandatory** on the dome pads — state it explicitly in the quote.
- At qty ~5 the flat setup/stencil/fixture fees dominate; per-board cost only falls with volume.
