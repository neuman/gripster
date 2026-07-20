# thumbdeck — Crowd Supply launch strategy

> A go-to-market read of the project as it stands at rev-A (v0.19). This is a
> strategy memo, not a spec. Numbers are estimates to re-quote at order time.
> Bottom line up front: the design is far more finished than most pre-campaign
> hardware, but **the one thing Crowd Supply requires — a working prototype —
> does not exist yet**, and **the 5-part 3D-printed shell does not scale**.
> Those two facts drive everything below.

---

## TL;DR

- **Can you launch on Crowd Supply?** Yes — it's the right platform for this
  (open hardware, ZMK, KiCad, MIT license all fit their audience). But not yet.
  They require a functioning prototype and you have "not yet built."
- **What to do first:** build and validate the first-article run of 5, then apply.
- **The market** is real but narrow: two-handed phone power-typists — mobile
  writers, Termux/mobile-dev tinkerers, field/radio operators, the retro-handheld
  crowd, and some accessibility users. Think **hundreds to low thousands** of
  units over the product's life, not tens of thousands.
- **Price:** $189–229 is the defensible band. Below ~$170 the unit economics
  stop working; above ~$250 you're competing with full ergo keyboards.
- **Can you make money?** A modest amount, *if* you solve the shell (injection
  molding or a vetted print/CNC partner) and treat labor as a real cost. As a
  pure 3D-print-at-home operation it's a paid hobby, not a business.

---

## 1. What you need to do to launch on Crowd Supply

Crowd Supply is an all-or-nothing platform (you get funds only if you hit goal)
that takes roughly **12% of sales + payment processing (~2.9% + $0.30/txn)** —
budget ~15% all-in. In exchange they provide real hands-on help (copywriting,
media, sourcing, risk review, fulfillment, support) and place their own
follow-on order typically **50–100% of what backers raise**. Over 90% of their
launched projects fund. See [Apply](https://www.crowdsupply.com/apply).

Gating items, in order:

1. **Build a working prototype.** This is non-negotiable and it's your critical
   path. The README is explicit: rev-A is *routed and DRC-clean but not built*,
   and *no green CI run producing `thumbdeck-zmk.uf2` exists yet*. Do exactly
   what the build guide says:
   - Get one green Actions run producing the `.uf2`.
   - Reserve the **E73 modules** first (stock swings ~1000 → ~20 in days).
   - Order the first-article 5 sets, press domes, print shells, flash, pair.
   - Prove range with a phone + hand actually cradling it (the antenna sits next
     to the phone and battery — the README flags detuning as an open risk).
2. **Prove the ergonomics.** Feel is still an open question in the README (flat
   ortho vs. canted arc; shoulder buttons; no trackpad). You need a device you've
   lived with for a week, and ideally 3–5 other testers, before you ask strangers
   for money. This is the #1 reason input-device campaigns disappoint at delivery.
3. **Pick and lock a phone-fit story.** Today the shell is dimensioned to *one*
   phone (S25 Ultra + 1.2 mm case). That's a killer for a mass audience. Decide:
   ship model-specific shells (small SKUs, honest), a small family of the most
   common large Androids, or an adjustable/universal clamp. This is a
   product-defining call, not a detail.
4. **Solve the shell for volume** (see §5). A 5-part FDM print per unit is a
   prototype process, not a fulfillment process.
5. **Apply** with the prototype, a short demo video, the BOM/cost model, and a
   fulfillment plan. Crowd Supply's team then helps shape the campaign page,
   funding target, and stretch goals before you go live.
6. **Set an honest funding goal** = the money you actually need to place the
   production run + tooling + packaging + a buffer, not a vanity number. All-or-
   nothing rewards a *reachable* goal; you can always overshoot.

---

## 2. What is the market for this device?

**The core buyer:** someone who wants to type a lot on a phone held in two hands
like a game controller, and finds on-screen keyboards and folding BT keyboards
inadequate. That's a genuine, underserved niche — but it *is* a niche.

Concentric circles, most to least likely:

- **Mobile writers / journalers / email-on-the-go** who currently tolerate
  thumb-typing on glass. The clearest value prop: tactile QWERTY without a table.
- **Termux / mobile-dev / sysadmin tinkerers** — the exact ZMK/open-hardware
  crowd Crowd Supply already reaches. Physical keys + a phone = a pocket terminal.
- **Retro/emulation & handheld-PC crowd** — the Backbone/GBC form language you
  chose speaks directly to them; a keyboard controller is a natural adjacent buy.
- **Field / radio / industrial** — techs, ham operators, inspectors entering text
  on a phone in the field where a desk isn't available.
- **Accessibility** — some users type far better on tactile domes than glass;
  worth naming, though it needs care to serve well.

**Size, honestly.** Comparable open-hardware input devices set the ceiling:
Ultimate Hacking Keyboard and ErgoDox EZ each built real businesses, but those
are full ergo keyboards with broad daily-driver appeal. A *phone-mounted thumb
deck* is narrower and phone-dependent. Realistic expectation for a first
campaign: **~100–500 units, ~$20k–$100k gross.** Treat anything above that as
upside. The phone-specificity is the biggest cap on the number — every phone you
don't fit is a customer you can't serve.

**Competition / alternatives** backers will weigh you against: folding Bluetooth
keyboards ($30–60), the phone's own gesture/swipe typing (free), Clicks-style
snap-on physical keyboard cases (iPhone-focused), and game-controller grips with
no keys. Your differentiator is *full split QWERTY thumb-typing while holding the
phone* — lean on that, and on open firmware/hardware, hard.

---

## 3. How do you reach them?

Crowd Supply's own audience and newsletter are the single best channel for this
exact product — that's a big part of what the 12% buys. Beyond that, in rough
priority:

- **Build in public now.** Post the renders, the CAD, the KiCad boards, the
  "phone becomes a work deck" hook. r/ErgoMechKeyboards, r/olkb, r/MechanicalKeyboards,
  Hacker News, the ZMK Discord, lobste.rs. This crowd rewards openness and a
  good story, and it's where your early adopters and beta testers live.
- **Video is the product.** This device is impossible to understand from a
  spec sheet and obvious in 15 seconds of footage of thumbs flying on a
  phone-in-hand. One good demo clip will do more than any copy. Prioritize it.
- **Hardware press** that covers Crowd Supply/open hardware: Hackaday (natural
  fit — pitch the autonomous route+DRC pipeline and the single-module unibody
  split), Hackster, CNX Software, tom's-hardware-adjacent maker coverage.
- **Niche creators** — mobile-productivity YouTubers, the handheld-emulation
  channels, ZMK/keyboard-hobby creators. Send units, not press releases.
- **A landing page with an email list before launch.** The size of that list on
  day one is the best predictor of whether an all-or-nothing campaign funds.
  Crowd Supply lets you collect "notify me" interest pre-launch — use it.

The pattern that works: months of build-in-public → a pre-launch list → a strong
video → Crowd Supply's newsletter amplifying the launch → press picks it up
because the story (open, self-routed, phone-as-deck) is interesting.

---

## 4. How do you price it?

Build price up from cost, then sanity-check against comparables.

**Cost shape today (prototype, qty 5):** the docs put the two PCBAs at ~$150–250
for 5 sets — i.e. **$30–50/unit for boards alone** at tiny volume, flat-fee
dominated. That's not a production cost; it's a prototype cost.

**Estimated landed COGS at 500–1,000 units** (order-of-magnitude, re-quote):

| Element | Est. per-unit | Note |
|---|---|---|
| 2× 4-layer ENIG PCBA | $18–28 | falls hard with volume; ENIG + E73 X-ray keep it up |
| E73 nRF52840 module | ~$6 | volatile stock — hedge |
| 78 snap domes + retention array | $3–6 | Snaptron + polyimide |
| LiPo 403040 + connector | $2–4 | |
| FFC jumper + 2× ZIF | $1–3 | |
| MagSafe N52 ring | $1–2 | |
| **Enclosure + keymats** | **$8–25** | **the swing factor — see §5** |
| Assembly + dome pressing + flash + QA | $10–25 | real labor, per unit |
| Packaging, cable, insert | $3–6 | |
| **Landed COGS** | **≈ $55–95** | before platform fees, returns, support |

Now layer on Crowd Supply's ~15% and the reality that hardware needs margin for
returns, support, and the units you scrap. A healthy consumer-hardware markup is
**~2.5–4× COGS**.

**Comparables (the ceiling and the anchor):**
- Ultimate Hacking Keyboard: ~$275+
- ErgoDox EZ: ~$295–350
- Keyboardio Model 100: ~$349
- Folding BT keyboards (the cheap alternative): $30–60

**Recommendation: price in the $189–229 band, with an early-bird tier around
$169–179.** Reasoning:
- At ~$70 COGS and $199 retail, after ~15% fees you net ~$100/unit — enough to
  absorb reality and make a margin.
- It stays clearly under the $275–350 full-ergo-keyboard tier, positioning
  thumbdeck as a *companion device*, not a keyboard replacement.
- It's high enough that folding-BT-keyboard shoppers self-select out — you don't
  want price-shoppers; you want the niche that gets it.
- **Below ~$170 the math breaks** once labor, the shell, and fees are honest.
  Resist the urge to price it like a hobby BOM. Do not price off the qty-5
  prototype cost.

Add a **bare-board / kit tier** (PCBAs + BOM, bring your own printing) for the
maker crowd at a lower price — it costs you little, widens the top of the funnel,
and suits the open-hardware audience. Given the MIT license, some will build it
themselves regardless; a kit converts those people into customers instead.

---

## 5. Can you make money? (the honest part)

**Yes, modestly — but only if you retire two risks.**

1. **The enclosure has to scale.** Five FDM-printed parts per unit is fine for
   5 units and impossible for 500 — the labor, print time, warping, and QA
   variance will eat you alive, and buyers of a $200 device expect an
   injection-molded feel. Your real options:
   - **Injection molding:** ~$10k–30k tooling for a multi-part set, then a few
     dollars a unit. Best margin at volume, but it's real capital and it locks
     the phone-fit geometry. Only justified if the campaign funds enough units.
   - **Vetted print farm / MJF / resin service or CNC:** higher per-unit, near-
     zero tooling, scales without capital. The right call for a first run of
     hundreds. Silicone-molded keymats similarly beat printed TPU at volume.
   - Whatever you pick, **it must be sorted before you name a price or a goal.**
     The enclosure decision is the difference between a healthy margin and a loss.
2. **Labor is a cost, not free.** Pressing 78 domes, assembling five parts,
   seating an FFC, flashing, pairing, and QA per unit is real time. Price it in,
   or find an assembly partner (JLC/PCBWay can quote dome application — the docs
   note it roughly doubles board cost but it removes you from the critical path).

**The economics, plainly:**
- At $199 retail, ~$70 COGS, ~15% fees → ~$100 contribution/unit.
- 300 units ≈ $30k contribution; 1,000 units ≈ $100k — **before** your own time,
  tooling amortization, support, warranty, and the inevitable v2 respin.
- That's a solid side project or a springboard, not a salary on the first run.
  Open hardware businesses that work (UHK, ErgoDox EZ) got there over *years* and
  multiple products, funded by a first campaign exactly like this one.

**What would make it genuinely profitable:**
- Broaden phone fit (more addressable buyers per campaign).
- Nail the demo video (this product lives or dies on "I get it in 15 seconds").
- Solve the shell at volume (protects margin).
- Build the pre-launch email list (de-risks all-or-nothing funding).
- Keep the kit/bare-board tier (cheap funnel-widener given the open license).

**Biggest risks to margin and reputation:** shipping before the ergonomics are
proven; BLE range disappointing once a hand + phone are actually against the
antenna; phone-fit complaints from people whose phone you don't support; and
underpricing off the prototype BOM. All four are addressable *before* launch —
which is the whole point of building the first article first.

---

## Suggested sequence

1. Green CI `.uf2` → reserve E73s → build & validate the first-article 5.
2. Live with it a week; recruit 3–5 testers; settle feel + phone-fit.
3. Decide the volume enclosure path; get a real per-unit quote at 300/500/1000.
4. Rebuild the cost model at those volumes; set price ($189–229) and goal.
5. Start building in public; stand up a landing page + Crowd Supply notify list.
6. Shoot the demo video.
7. Apply to Crowd Supply with prototype + video + cost model + fulfillment plan.
8. Launch with a list already in hand.

---

*Sources: [Crowd Supply — Apply](https://www.crowdsupply.com/apply),
[Crowd Supply vs. Kickstarter](https://www.crowdcrux.com/crowd-supply-vs-kickstarter/),
[Crowd Supply — Keyboards & Input Devices](https://www.crowdsupply.com/keyboards-and-input-devices),
[Ultimate Hacking Keyboard](https://www.crowdsupply.com/ugl/ultimate-hacking-keyboard),
[ErgoDox EZ crowdfunding](https://ergodox-ez.com/crowdfunding),
[Keyboardio Model 100](https://www.kickstarter.com/projects/keyboardio/model-100).
Cost figures derived from this repo's `docs/fabrication-sourcing.md` and
`docs/bill-of-materials.md`; treat all dollar figures as estimates to re-quote.*
