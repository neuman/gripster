#!/usr/bin/env python3
"""
gen_board.py — rev-A KiCad board generator, one board per grip.

Places REAL footprints and builds the FULL netlist for both grips; routing is done
afterwards by route.sh (Freerouting) — this file adds only the deterministic copper
(USB same-net pad ties). KiCad 9 headless: DRC, zone fill and Specctra export all
work (the old KiCad-7 caveats are gone).

rev-A electrical scope (see docs/design-review.md):
  * Ebyte E73-2G4M08S1C antenna-DOWN at the bottom board edge (module keep-out zone
    crosses the edge; GND pours stay clear on all 4 layers).
  * Bridge = 16-pin 1.0 mm FFC ZIF (SMT, bottom contacts) on each grip's inner edge;
    a straight type-A FFC jumper crosses the spine. Left-grip pad nets are assigned
    by RIBBON GEOMETRY (conductor y-position match), not by pin number, so a straight
    jumper is correct by construction.
  * Battery = JST-PH SMT (polarized); MSK12C02 power slide switch between the cell
    and the VBAT rail (charger stays on the cell side -> charges while off).
  * MCP73831 with its stability caps AT the chip; USBLC6-2 inline in the data path;
    reset tact (shell pinhole); charge LED on STAT; battery divider + filter cap;
    SWD + spare-I2C/GPIO test pads.
  * Snap domes use the production snaptron_7mm_contact footprint (continuous leg
    ring, mask aperture, pour keep-out, vent).

Frame: KiCad Y-down (deck.py geometry is Y-up; flipped with _fy).
"""
from __future__ import annotations
import os
import pcbnew
from pcbnew import VECTOR2I as V, FromMM as MM
import deck

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "kicad", "generated"))
STOCK = "/usr/share/kicad/footprints"
LOCAL = os.path.abspath(os.path.join(HERE, "..", "footprints", "thumbdeck.pretty"))
NROWS, NCOLS_HALF = 9, 5
TRACE = 0.25   # mm signal trace (Default netclass)
PWR = 0.5      # mm power trace (Power netclass)

# ---- E73 pad -> net. Pad N == Ebyte datasheet pin N (marbastlib footprint,
# verified 1:1 vs the official Ebyte E73-2G4M08S1C User Manual pin table).
# Bridge columns (COL5-9) on castellated edge pads. COL9 moved off pad 11
# (P0.00/XL1) to pad 18 (P0.04/AIN2) so the XL pins stay free — firmware runs the
# LF clock from the internal RC, but keeping XTAL pins unused removes the failure
# mode entirely. Pads 15/4/8 (P0.05/P0.28/P0.29) are broken out to spare test pads
# (rev-B trackpad / expansion I2C + IRQ).
E73_PINMAP = {
    "1": "ROW0", "2": "ROW1", "6": "ROW2", "12": "ROW3", "14": "ROW4",
    "16": "ROW5", "17": "ROW6", "20": "ROW7", "22": "ROW8",
    "28": "COL0", "30": "COL1", "32": "COL2", "33": "COL3", "34": "COL4",
    "35": "COL5", "3": "COL6", "9": "COL7", "10": "COL8", "18": "COL9",
    "7": "VBAT_SENSE",                      # P0.02/AIN0, 1M/1M divider + 100nF
    "15": "SDA", "4": "SCL", "8": "TP_INT",  # spare I2C/IRQ breakout (rev-B)
    "19": "3V3", "23": "VBAT", "5": "GND", "21": "GND", "24": "GND",
    "27": "VBUS", "29": "USB_DM", "31": "USB_DP",
    "37": "SWDIO", "39": "SWDCLK", "26": "RESET",
}

LIBS = {"TD": LOCAL,
        "SOT": STOCK + "/Package_TO_SOT_SMD.pretty",
        "R": STOCK + "/Resistor_SMD.pretty",
        "C": STOCK + "/Capacitor_SMD.pretty",
        "LED": STOCK + "/LED_SMD.pretty",
        "USB": STOCK + "/Connector_USB.pretty",
        "FFC": STOCK + "/Connector_FFC-FPC.pretty",
        "JST": STOCK + "/Connector_JST.pretty",
        "SW": STOCK + "/Button_Switch_SMD.pretty",
        "TP": STOCK + "/TestPoint.pretty"}

FFC_FP = ("TD", "ffc_afa07_s16fcc")   # JUSHUO AFA07-S16FCC-00 (LCSC C13744)

USBC_NETS = {"A4": "VBUS", "B4": "VBUS", "A9": "VBUS", "B9": "VBUS",
             "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
             "A5": "CC1", "B5": "CC2",
             "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM"}

# JLC/LCSC part assignment (stamped on footprints + exported to the BOM by
# gen_fab.py). Values verified against the JLC parts library — see
# docs/fabrication-sourcing.md.
LCSC = {
    "E73-2G4M08S1C": "C356849",       # nRF52840 module (Standard assy, X-ray)
    "1N4148WS": "C2128",              # SOD-323, Basic
    "USB-C": "C165948",               # HRO TYPE-C-31-M-12 16P
    "MCP73831": "C424093",            # MCP73831T-2ACI/OT SOT-23-5
    "USBLC6-2SC6": "C7519",           # SOT-23-6 ESD
    "4k7": "C25900", "5k1": "C25905", "1M": "C26083", "1k": "C11702",
    "100nF": "C1525", "1uF": "C52923",
    "4u7/0805": "C1779",              # 0805 X5R >=16V
    "LED_RED": "C2286",               # 0603 red
    "FFC16": "C13744",                # JUSHUO AFA07-S16FCC-00, 1.0mm 16P bottom-contact
    "JST-PH-2": "C295747",            # S2B-PH-SM4-TB side entry
    "MSK12C02": "C431540",            # SPDT slide
    "TS-1187A": "C318884",            # reset tact
}


def _fy(y, H):
    return H - y


def vec(x, y):
    return V(MM(x), MM(y))


def elec_rc(i, side):
    """Electrical (row, col) for key index i on a grip — the ONE definition shared
    with gen_firmware.py so board and firmware cannot drift."""
    assert i < NROWS * NCOLS_HALF, f"key index {i} overflows the {NROWS}x{NCOLS_HALF} half-matrix"
    col_off = 0 if side == "right" else NCOLS_HALF
    return (i // NCOLS_HALF), col_off + (i % NCOLS_HALF)


class Board:
    def __init__(self, geo, side):
        self.geo = geo; self.side = side; self.H = geo["board_h"]
        self.b = pcbnew.BOARD()
        ds = self.b.GetDesignSettings()
        ds.m_CopperEdgeClearance = MM(0.2)   # JLC routed-edge spec
        ds.m_TrackMinWidth = MM(0.15)
        ds.m_MinClearance = MM(0.127)
        # 4-layer stackup: F.Cu(sig) / In1.Cu(GND plane) / In2.Cu(sig+pwr) / B.Cu(sig).
        # The GND plane gives the module antenna a reference + lowers matrix
        # crosstalk; the inner In2 signal layer makes the dense E73 fan-in routable.
        self.b.SetCopperLayerCount(4)
        self.nets = {}
        self.net("GND"); self.net("3V3"); self.net("VBAT"); self.net("VBUS")
        self.rows_csv = []
        self.j2_pads = None      # [(net_name, deck_y)] of the RIGHT grip's J2, for ribbon mapping

    def net(self, name):
        if name not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.b, name); self.b.Add(ni); self.nets[name] = ni
        return self.nets[name]

    # ---- graphics ----
    def outline(self):
        o = self.geo["outline"]; H = self.H
        for i in range(len(o)):
            x1, y1 = o[i]; x2, y2 = o[(i + 1) % len(o)]
            if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
                continue                       # skip zero-length segments (invalid_outline)
            s = pcbnew.PCB_SHAPE(self.b); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(vec(x1, _fy(y1, H))); s.SetEnd(vec(x2, _fy(y2, H)))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.15)); self.b.Add(s)

    def keepout(self, cx, cy, r):
        """Circular rule-area (no tracks/vias/pour) — Freerouting reads it from the DSN."""
        import math
        z = pcbnew.ZONE(self.b); z.SetLayerSet(pcbnew.LSET.AllCuMask())
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowPads(True)
        poly = pcbnew.VECTOR_VECTOR2I()
        for a in range(12):
            t = math.radians(a * 30)
            poly.append(vec(cx + r * math.cos(t), cy + r * math.sin(t)))
        z.AddPolygon(poly); self.b.Add(z)

    def mount_holes(self):
        # NPTH mount holes as Edge.Cuts circle cut-outs (the MountingHole *footprint*
        # breaks KiCad's Specctra/DSN export; Edge.Cuts circles round-trip fine) + a
        # keepout ring so the autorouter/pour stays clear of each hole. The shell
        # boss lands r=3.0 around each hole — gen_board asserts no components there.
        for h in self.geo["mount_holes"]:
            cx, cy = h["x"], _fy(h["y"], self.H)
            c = pcbnew.PCB_SHAPE(self.b); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
            c.SetCenter(vec(cx, cy)); c.SetEnd(vec(cx + h["d"] / 2, cy))
            c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(MM(0.15)); self.b.Add(c)
            self.keepout(cx, cy, h["d"] / 2 + 0.8)

    def track(self, x1, y1, x2, y2, layer, net, w=TRACE):
        t = pcbnew.PCB_TRACK(self.b); t.SetStart(vec(x1, y1)); t.SetEnd(vec(x2, y2))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net); self.b.Add(t)

    def gnd_zone(self, layer):
        z = pcbnew.ZONE(self.b); z.SetLayer(layer); z.SetNet(self.net("GND"))
        poly = pcbnew.VECTOR_VECTOR2I()
        for x, y in self.geo["outline"]:
            poly.append(vec(x, _fy(y, self.H)))
        z.AddPolygon(poly)
        z.SetLocalClearance(MM(0.25)); z.SetAssignedPriority(0)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # solid GND (no starved thermals)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)   # drop only padless islands
        self.b.Add(z)

    def silk(self, txt, x, y, size=0.8, front=False):
        """Reference text on the silkscreen (deck coords). Back-side text is mirrored."""
        t = pcbnew.PCB_TEXT(self.b)
        t.SetText(txt); t.SetPosition(vec(x, _fy(y, self.H)))
        t.SetTextSize(V(MM(size), MM(size))); t.SetTextThickness(MM(0.12))
        t.SetLayer(pcbnew.F_SilkS if front else pcbnew.B_SilkS)
        if not front:
            t.SetMirrored(True)
        self.b.Add(t)

    # ---- footprints ----
    def load(self, lib, name):
        fp = pcbnew.FootprintLoad(LIBS[lib], name)
        assert fp is not None, f"footprint {lib}/{name} not found"
        return fp

    def place(self, fp, ref, val, x, y, netmap=None, back=True, rot=0):
        """Place at deck (x,y). Flip first, then rotate — rotations are then in the
        flipped frame, which is what the empirical orientation constants assume."""
        fp.SetReference(ref); fp.SetValue(val)
        fp.SetPosition(vec(x, _fy(y, self.H))); self.b.Add(fp)
        if back:
            fp.Flip(fp.GetPosition(), False)   # NB: Flip() itself sets rot=180
        fp.SetOrientationDegrees(rot)          # always set — rot is in the flipped frame
        if netmap:
            for p in fp.Pads():
                nm = netmap.get(p.GetNumber())
                if nm:
                    p.SetNet(self.net(nm))
        if val in LCSC and LCSC[val]:
            set_field(fp, "LCSC", LCSC[val])
        return fp

    def assert_clear_of_bosses(self):
        """No component courtyard may enter the shell standoff-boss disc (r=4.0,
        v0.19: Ø7.5 M3 boss + 0.25 margin) around any mount hole — the PCB must
        seat flat on the bosses."""
        import math
        BOSS_R = 4.0
        for h in self.geo["mount_holes"]:
            hx, hy = h["x"], _fy(h["y"], self.H)
            for fp in self.b.GetFootprints():
                bb = fp.GetBoundingBox(False)
                cx = min(max(MM(hx), bb.GetLeft()), bb.GetRight())
                cy = min(max(MM(hy), bb.GetTop()), bb.GetBottom())
                d = math.hypot(cx - MM(hx), cy - MM(hy)) / 1e6
                assert d >= BOSS_R, (f"{self.side}: {fp.GetReference()} is {d:.2f}mm from "
                                     f"mount hole ({h['x']},{h['y']}) — inside the {BOSS_R}mm boss")

    def save(self):
        p = os.path.join(OUT, f"thumbdeck_{self.side}.kicad_pcb")
        pcbnew.SaveBoard(p, self.b)
        # Scoped DRC waiver: the USB-C receptacle's shield pads (GND) legitimately sit
        # closer to the board edge than the global 0.2mm rule (mouth flush with the
        # edge). GND *pads* only; traces-to-edge stay strict.
        dru = os.path.join(OUT, f"thumbdeck_{self.side}.kicad_dru")
        with open(dru, "w") as f:
            f.write('(version 1)\n'
                    '(rule "gnd_pad_edge"\n'
                    '  (condition "A.NetName == \'GND\' && (A.Type == \'Pad\' || B.Type == \'Pad\')")\n'
                    '  (constraint edge_clearance (min 0.05mm)))\n')
        return p


def set_field(fp, name, val):
    """Stamp a named field (e.g. LCSC) on a footprint, hidden."""
    fp.SetField(name, val)
    f = fp.GetFieldByName(name)
    if f is not None:
        f.SetVisible(False)


def build_matrix(bd):
    """PLACE switches (F, production ring-pad footprint: 13 overlapping circles
    spanning 292deg + a 67.5deg escape gap for the column trace) + diodes (B) at
    every key and assign row/col/diode-node nets. The overlapping ring circles are
    left as separate same-net pads — Freerouting joins them itself; pre-welding
    them with track chains crashes its trace-combine recursion."""
    geo = bd.geo; H = bd.H
    keys = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
    assert len(keys) <= NROWS * NCOLS_HALF, f"{bd.side}: {len(keys)} keys > matrix half capacity"
    for i, k in enumerate(keys):
        r, c = elec_rc(i, bd.side)
        x, y = k["x"], _fy(k["y"], H)
        dn = bd.net(f"DN_{bd.side[0].upper()}{i+1}")
        sw = bd.load("TD", "snaptron_7mm_contact")
        sw.SetReference(f"SW{i+1}"); sw.SetValue("SNAP7"); sw.SetPosition(vec(x, y)); bd.b.Add(sw)
        for p in sw.Pads():
            p.SetNet(bd.net(f"COL{c}") if p.GetNumber() == "1" else dn)
        d = pcbnew.FootprintLoad(STOCK + "/Diode_SMD.pretty", "D_SOD-323")
        d.SetReference(f"D{i+1}"); d.SetValue("1N4148WS"); d.SetPosition(vec(x, y - 3.0)); bd.b.Add(d)
        d.Flip(d.GetPosition(), False)   # to B.Cu
        for pad in d.Pads():
            pad.SetNet(bd.net(f"ROW{r}") if pad.GetNumber() == "1" else dn)  # K->row, A->node
        set_field(d, "LCSC", LCSC["1N4148WS"])
        bd.rows_csv.append((f"SW{i+1}", k.get("label", "?"), f"ROW{r}", f"COL{c}",
                            round(x, 2), round(y, 2)))


# Bridge contact nets in RIBBON ORDER (16 conductors): rows, left cols, 2x GND.
BRIDGE_NETS = [f"ROW{i}" for i in range(9)] + [f"COL{5+i}" for i in range(5)] + ["GND", "GND"]


def place_bridge(bd, right_j2_map):
    """FFC ZIF on the inner edge, contacts along Y, ribbon exit toward the spine.
    RIGHT grip: nets assigned pin1->ROW0 ... pin16->GND, and the (net, deck_y) list
    is returned. LEFT grip: each contact takes the net of the RIGHT contact at the
    same deck y — a straight type-A jumper is then correct by construction
    (both connectors are back-mounted bottom-contact, entries facing each other,
    so the flat ribbon meets both contact sets on the same conductor face)."""
    H = bd.H
    fp = bd.load(*FFC_FP)
    if bd.side == "right":
        # entry (ribbon) faces -x: contacts run along Y. Empirical rot below.
        bd.place(fp, "J2", "FFC16", 3.6, 24.5, back=True, rot=270)
    else:
        W = bd.geo["board_w"]
        bd.place(fp, "J2", "FFC16", W - 3.6, 24.5, back=True, rot=90)
    # collect the 16 signal pads sorted by y
    sig = [p for p in fp.Pads() if p.GetNumber().isdigit()]
    sig.sort(key=lambda p: p.GetPosition().y)
    assert len(sig) == 16, f"expected 16 FFC contacts, got {len(sig)}"
    if bd.side == "right":
        for p, net in zip(sig, BRIDGE_NETS):
            p.SetNet(bd.net(net))
        mapping = [(p.GetNetname(), round(_fy(p.GetPosition().y / 1e6, H), 3)) for p in sig]
    else:
        assert right_j2_map is not None, "right grip must be generated first"
        for p in sig:
            dy = round(_fy(p.GetPosition().y / 1e6, H), 3)
            net = min(right_j2_map, key=lambda m: abs(m[1] - dy))
            assert abs(net[1] - dy) < 0.5, f"no ribbon conductor at y={dy} (nearest {net})"
            p.SetNet(bd.net(net[0]))
        mapping = None
    for p in fp.Pads():                      # mechanical tabs -> GND
        if not p.GetNumber().isdigit():
            p.SetNet(bd.net("GND"))
    bd.silk("J2 FFC16 <- pin1", 3.6 if bd.side == "right" else bd.geo["board_w"] - 3.6, 36.0)
    return mapping


def place_components(bd):
    """Right grip: E73 + USB front-end, charger, battery connector + power switch,
    reset, LED, passives, test pads. All SMT, all on the BACK (single-sided reflow).
    Left grip: bridge only (passive).

    v0.17: the whole electronics cluster moved from the old BOTTOM strip up to the TOP
    zone (the vacated trackpad space) so the chin could be trimmed. It is implemented as
    a rigid 180-degree rotation of the exact, DRC-verified rev-A cluster about the board
    centre — P() places every part at the rotated (W-x, H-y) / rot+180, and the
    involution xf() carries the hand-routed USB fan-in copper along unchanged. The
    rotation lands the E73 antenna at the OUTER-top edge (farthest from the centred
    phone/LiPo = best RF) with the mouth of the USB-C on the top edge beside it."""
    if bd.side != "right":
        return
    H = bd.H
    W = bd.geo["board_w"]
    # The 180-deg cluster rotation lands the rev-A INNER-hugging parts (module, divider)
    # at the OUTER-top, clear of the rounded top corner. v0.19: the anchor is a FROZEN
    # absolute constant, not W-derived — the GBC outline narrowed board_w 79.493 -> 75.0
    # and a W-anchored cluster slid 5mm inboard, planting the charger caps on the
    # PGUP/PGDN dome courtyards (C5's GND escape had no legal via spot). AX reproduces
    # the v0.17-proven poses exactly (old W 79.493 - old DX 7.0); the top-edge outline
    # is nearly unchanged there (old bowed edge ~75 vs new straight 75.0).
    AX = 72.493

    def P(fp, ref, val, x, y, netmap=None, rot=0):
        """Place at the 180-deg-rotated, AX-anchored pose of the rev-A coordinate."""
        return bd.place(fp, ref, val, AX - x, H - y, netmap, rot=(rot + 180) % 360)

    def S(txt, x, y, **kw):
        bd.silk(txt, AX - x, H - y, **kw)

    def xf(x, y):
        """180-deg rotation about the frozen AX anchor (nm). Involution: xf(xf(p))==p.
        Un-rotates a placed pad back to the rev-A frame so the hand copper formulas below
        are byte-for-byte the verified ones; re-applied on every emitted segment/via."""
        return pcbnew.VECTOR2I(int(MM(AX) - x), int(MM(H) - y))

    # E73 module, antenna end at/over the TOP edge. rot=180 (in the flipped frame) points
    # the antenna zone off deck y>H and the USB/SWD pads inboard — verified empirically;
    # asserted below.
    u1 = P(bd.load("TD", "nRF52840_E73-2G4M08S1C"), "U1", "E73-2G4M08S1C",
           16.0, 8.5, E73_PINMAP, rot=0)
    zb = list(u1.Zones())[0].GetBoundingBox()
    assert zb.GetTop() < 0, "E73 antenna keep-out must cross the TOP board edge"

    # USB-C, mouth flush with the TOP edge. The rev-A rot=180 becomes rot=0 under P().
    P(bd.load("USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12"), "J1", "USB-C",
      37.0, 3.6, USBC_NETS, rot=180)
    # Deterministic ties for the interleaved same-net data-pad pairs (B6 A7 A6 B7 at
    # 0.5mm pitch) that no autorouter can join at these clearances. VBUS/GND pairs
    # (A9/B4 etc.) are co-located in this footprint and need no tie. Pattern (all
    # relative to the pad row so it tracks J1 moves): D- joins with a bar just below
    # the row; D+ hops over it on In2 via two vias. All resulting gaps >=0.25mm (DRC-checked).
    j1 = bd.b.FindFootprintByReference("J1")
    # Un-rotate the placed pads back to the rev-A frame so every formula below is the
    # verified original; seg()/via() re-apply xf on emit so the copper follows the parts.
    pads = {p.GetNumber(): xf(p.GetPosition().x, p.GetPosition().y) for p in j1.Pads()}
    dm_net, dp_net = bd.net("USB_DM"), bd.net("USB_DP")
    xa7, xb7 = pads["A7"].x, pads["B7"].x
    xa6, xb6 = pads["A6"].x, pads["B6"].x
    py = pads["A7"].y
    y_dm, y_dp, y_up = py - MM(1.31), py - MM(2.26), py + MM(1.24)

    def seg(x1, y1, x2, y2, net, layer=pcbnew.B_Cu):
        a, b = xf(x1, y1), xf(x2, y2)
        t = pcbnew.PCB_TRACK(bd.b)
        t.SetStart(a); t.SetEnd(b)
        t.SetWidth(MM(0.2)); t.SetLayer(layer); t.SetNet(net); bd.b.Add(t)

    def via(x, y, net):
        v = pcbnew.PCB_VIA(bd.b); v.SetPosition(xf(x, y))
        v.SetDrill(MM(0.3)); v.SetWidth(MM(0.6))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net); bd.b.Add(v)

    seg(xa7, py, xa7, y_dm, dm_net); seg(xb7, py, xb7, y_dm, dm_net)
    seg(xa7, y_dm, xb7, y_dm, dm_net)                     # D- bar
    seg(xb6, py, xb6, y_dp, dp_net)                       # B6 stub down
    seg(xa6, py, xa6, y_up, dp_net); via(xa6, y_up, dp_net)   # A6 stub up + via
    seg(xa6, y_up, xb6 - MM(0.55), y_dp, dp_net, pcbnew.In2_Cu)  # In2 hop over D- bar
    v2x = xb6 - MM(0.55)
    via(v2x, y_dp, dp_net)
    seg(v2x, y_dp, xb6, y_dp, dp_net)                     # close D+ pair

    # Deterministic inner-layer runs J1 -> module for the data pair (Freerouting
    # plateaus on this corridor; fixed copper is DRC-verified and it routes around).
    # Lanes on In2 below the module's USB pad rows; resurface next to pads 29/31.
    up = {p.GetNumber(): xf(p.GetPosition().x, p.GetPosition().y) for p in u1.Pads()}
    p29, p31 = up["29"], up["31"]                          # USB_DM / USB_DP pads
    assert abs(p29.x - p31.x) < 1000, "module USB pads expected on one column"
    In2 = pcbnew.In2_Cu
    yA, yB = py - MM(7.05), py - MM(6.25)                  # DM / DP In2 lanes
    vx = MM(23.2)                                          # resurface via column
    # D-: extend the B7 tie stub down, dive to In2, low lane west, up to p29
    via(xb7, py - MM(2.46), dm_net)
    seg(xb7, y_dm, xb7, py - MM(2.46), dm_net)
    seg(xb7, py - MM(2.46), xb7, yA, dm_net, In2)
    seg(xb7, yA, vx, yA, dm_net, In2)
    seg(vx, yA, vx, p29.y, dm_net, In2)
    via(vx, p29.y, dm_net)
    seg(vx, p29.y, p29.x, p29.y, dm_net)
    # D+: from the pair-close via, mid lane west, elbow north of the DM via, to p31
    seg(v2x, y_dp, v2x, yB, dp_net, In2)
    seg(v2x, yB, MM(24.0), yB, dp_net, In2)
    seg(MM(24.0), yB, MM(24.0), p31.y, dp_net, In2)
    seg(MM(24.0), p31.y, vx, p31.y, dp_net, In2)
    via(vx, p31.y, dp_net)
    seg(vx, p31.y, p31.x, p31.y, dp_net)

    # NOTE from here down: coords are the rev-A BOTTOM-strip layout; P()/S() rotate each
    # part 180 deg into the TOP zone, so the arrangement below reads exactly like rev-A.
    # USBLC6-2SC6 inline between the connector and the module's USB pads:
    # 1&6 = D+ pair, 3&4 = D- pair, 2=GND, 5=VBUS (verified vs ST datasheet).
    P(bd.load("SOT", "SOT-23-6"), "U3", "USBLC6-2SC6", 28.5, 3.5,
      {"1": "USB_DP", "6": "USB_DP", "3": "USB_DM", "4": "USB_DM",
       "2": "GND", "5": "VBUS"})

    # reset tact (top actuator -> pinhole in the shell floor), between module and USB-C
    P(bd.load("SW", "SW_Push_1P1T_XKB_TS-1187A"), "SW91", "TS-1187A", 27.5, 9.0,
      {"1": "RESET", "2": "GND"})
    S("RST", 27.5, 12.5)

    # charger MCP73831 (SOT-23-5): 1=STAT 2=VSS 3=VBAT(cell) 4=VDD(VBUS) 5=PROG,
    # with BOTH datasheet stability caps AT the chip (C3 VDD, C5 VBAT_CELL).
    P(bd.load("SOT", "SOT-23-5"), "U2", "MCP73831", 48.5, 7.5,
      {"1": "STAT", "2": "GND", "3": "VBAT_CELL", "4": "VBUS", "5": "PROG"})
    P(bd.load("C", "C_0805_2012Metric"), "C3", "4u7/0805", 44.6, 7.5, {"1": "VBUS", "2": "GND"})
    P(bd.load("C", "C_0805_2012Metric"), "C5", "4u7/0805", 52.4, 7.5, {"1": "VBAT_CELL", "2": "GND"})
    P(bd.load("R", "R_0402_1005Metric"), "R24", "5k1", 48.5, 10.5, {"1": "PROG", "2": "GND"})
    # charge LED: VBUS -> R25 -> LED -> STAT (STAT sinks while charging)
    P(bd.load("R", "R_0402_1005Metric"), "R25", "1k", 42.0, 10.5, {"1": "VBUS", "2": "LED_A"})
    P(bd.load("LED", "LED_0603_1608Metric"), "D80", "LED_RED", 45.0, 10.5,
      {"1": "STAT", "2": "LED_A"})   # pad1 = cathode
    S("CHG", 45.0, 12.3)

    # power slide switch at the TOP edge (knob through the shell wall):
    # cell side (VBAT_CELL, always on charger) -> switch -> VBAT rail (module+divider)
    P(bd.load("TD", "msk12c02_slide"), "SW90", "MSK12C02", 48.5, 2.0,
      {"1": "VBAT_CELL", "2": "VBAT"})
    S("PWR", 48.5, 5.0)

    # battery JST-PH (polarized, SMT side entry). Placed directly (NOT via the cluster
    # rotation): the rotated pose would collide with the inner-top page keys, so it lives
    # in the trimmed bottom chin instead — flat, out of the key field, LiPo wire reaches it
    # across the back cavity. VBAT_CELL routes up to the power switch in the top cluster.
    bd.place(bd.load("JST", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"),
             "J3", "JST-PH-2", 44.0, 5.5, {"1": "VBAT_CELL", "2": "GND"}, rot=0)
    bd.silk("+", 49.5, 4.7); bd.silk("-", 49.5, 6.7); bd.silk("BAT", 44.0, 2.4)

    # USB CC 5.1k pulldowns — east of the connector, OUT of the D+/D- escape
    # corridor (x 32-38 above the pad row must stay open for the data-pair fan-in)
    P(bd.load("R", "R_0402_1005Metric"), "R20", "5k1", 39.8, 11.8, {"1": "CC1", "2": "GND"})
    P(bd.load("R", "R_0402_1005Metric"), "R21", "5k1", 42.3, 11.8, {"1": "CC2", "2": "GND"})

    # battery divider (1M/1M -> AIN0) + SAADC filter cap, inner strip between the
    # FFC bridge (above) and the mount-hole boss / antenna zone (below+left)
    P(bd.load("R", "R_0402_1005Metric"), "R22", "1M", 7.9, 11.5, {"1": "VBAT", "2": "VBAT_SENSE"})
    P(bd.load("R", "R_0402_1005Metric"), "R23", "1M", 7.9, 9.5, {"1": "VBAT_SENSE", "2": "GND"})
    P(bd.load("C", "C_0402_1005Metric"), "C6", "100nF", 7.9, 7.5, {"1": "VBAT_SENSE", "2": "GND"})

    # module decoupling: 1uF at VDD (3V3 out), 100nF + 4u7 bulk at VDDH, 1uF at VBUS
    P(bd.load("C", "C_0402_1005Metric"), "C1", "1uF", 16.6, 19.0, {"1": "3V3", "2": "GND"})
    P(bd.load("C", "C_0402_1005Metric"), "C2", "100nF", 19.2, 19.0, {"1": "VBAT", "2": "GND"})
    P(bd.load("C", "C_0805_2012Metric"), "C4", "4u7/0805", 12.2, 19.0, {"1": "VBAT", "2": "GND"})
    P(bd.load("C", "C_0402_1005Metric"), "C7", "1uF", 24.3, 13.9, {"1": "VBUS", "2": "GND"})

    # 9 row pull-downs in the passive lane between module and key field
    for i in range(9):
        P(bd.load("R", "R_0402_1005Metric"), f"R{i+1}", "4k7",
          32.0 + i * 3.0, 21.3, {"1": f"ROW{i}", "2": "GND"})

    # SWD + spare-I2C test pads (back), labeled. x >= 10 keeps them clear of the
    # FFC bridge body on the inner edge; y 21.3 clears the cap row below and the
    # dome courtyards above.
    tps = [("TP1", "SWDIO", 10.0), ("TP2", "SWDCLK", 13.0), ("TP3", "RESET", 16.0),
           ("TP4", "3V3", 19.0), ("TP5", "GND", 22.0),
           ("TP6", "SDA", 24.8), ("TP7", "SCL", 27.3), ("TP8", "TP_INT", 29.8)]
    for ref, net, x in tps:
        tp = P(bd.load("TP", "TestPoint_Pad_1.5x1.5mm"), ref, net, x, 21.3, {"1": net})
        tp.SetExcludedFromPosFiles(True); tp.SetExcludedFromBOM(True)
        S(net if net != "TP_INT" else "INT", x, 23.4, size=0.8)


def gnd_escapes(bd):
    """Pre-routed GND plane tie for EVERY small-part GND pad: a short B.Cu track to
    a via into the solid In1 plane, placed while the board is still track-free (the
    only obstacles are pads/holes/rule-areas, all known). Without this, Freerouting
    non-deterministically walls in 1-4 of these pads' pour blobs per run and the
    post-route stitcher can find no legal via spot in the congestion."""
    import math
    b = bd.b; gnd = bd.net("GND")
    pads = [(p, p.GetBoundingBox()) for p in b.GetPads()]
    holes = [(p.GetPosition().x, p.GetPosition().y, p.GetDrillSize().x // 2)
             for p in b.GetPads() if p.GetDrillSize().x > 0]
    zones = [z for fp in b.GetFootprints() for z in fp.Zones()
             if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    zones += [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    W, H = bd.geo["board_w"], bd.H
    placed = []
    fixed = [t for t in b.Tracks() if t.GetNetname() != "GND"]  # pre-routed USB copper

    def _seg_dist(px2, py2, t):
        x1, y1 = t.GetStart().x, t.GetStart().y
        x2, y2 = t.GetEnd().x, t.GetEnd().y
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0.0, min(1.0, ((px2 - x1) * dx + (py2 - y1) * dy) / L2))
        return ((px2 - (x1 + u * dx)) ** 2 + (py2 - (y1 + u * dy)) ** 2) ** 0.5

    def clear_of_pads(x, y, r, own):
        for q, bb in pads:
            if q is own or q.GetNetname() == "GND":
                continue
            dx = max(bb.GetLeft() - x, 0, x - bb.GetRight())
            dy = max(bb.GetTop() - y, 0, y - bb.GetBottom())
            if (dx * dx + dy * dy) ** 0.5 < r + MM(0.2):
                return False
        return True

    def spot_ok(x, y, own):
        if not (MM(1.2) < x < MM(W - 1.2) and MM(1.2) < y < MM(H - 1.2)):
            return False
        if not clear_of_pads(x, y, MM(0.3), own):
            return False
        for hx, hy, hr in holes:
            if math.hypot(hx - x, hy - y) < MM(0.15) + hr + MM(0.25):
                return False
        for vx, vy in placed:
            if math.hypot(vx - x, vy - y) < MM(0.85):
                return False
        for t in fixed:
            if _seg_dist(x, y, t) < MM(0.3) + MM(0.2) + t.GetWidth() // 2:
                return False
        pt = pcbnew.VECTOR2I(int(x), int(y))
        for z in zones:
            if z.Outline().Collide(pt, int(MM(0.35))):
                return False
        return True

    n = 0
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("SW") and fp.GetValue() == "SNAP7":
            continue                              # domes: front side, no GND
        if ref.startswith(("TP", "D")) and fp.GetValue() in ("1N4148WS",):
            continue                              # diodes have no GND
        if ref in ("U1", "J1", "J2"):
            continue                              # module/USB/FFC: big pads, dense fan-in — stitcher territory
        for p in fp.Pads():
            if p.GetNetname() != "GND" or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            px, py = p.GetPosition().x, p.GetPosition().y
            spot = None
            for rad in (MM(1.0), MM(1.2), MM(1.5), MM(1.8), MM(2.2)):
                for k in range(16):
                    a = 2 * math.pi * k / 16
                    x, y = px + rad * math.cos(a), py + rad * math.sin(a)
                    if not spot_ok(x, y, p):
                        continue
                    okc = True                     # corridor pad centre -> via
                    steps = 6
                    for s2 in range(steps + 1):
                        cx = px + (x - px) * s2 / steps
                        cy = py + (y - py) * s2 / steps
                        if not clear_of_pads(cx, cy, MM(0.15), p):
                            okc = False; break
                    if okc:
                        spot = (x, y); break
                if spot:
                    break
            assert spot, f"{bd.side}: no GND escape spot for {ref} pad {p.GetNumber()}"
            x, y = spot
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(p.GetPosition()); t.SetEnd(pcbnew.VECTOR2I(int(x), int(y)))
            t.SetWidth(MM(0.3)); t.SetLayer(pcbnew.B_Cu); t.SetNet(gnd); b.Add(t)
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
            v.SetDrill(MM(0.3)); v.SetWidth(MM(0.6))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
            placed.append((x, y)); n += 1
    if n:
        print(f"  {bd.side}: {n} GND escape vias pre-placed")


def gen(side, right_j2_map=None):
    geo = deck.build(deck.Config(side=side))
    bd = Board(geo, side)
    bd.outline(); bd.mount_holes()
    build_matrix(bd)
    j2map = place_bridge(bd, right_j2_map)
    place_components(bd)
    gnd_escapes(bd)
    bd.assert_clear_of_bosses()
    # GND: pours on F/B + a SOLID plane on In1.Cu (RF ref + return path).
    # In2.Cu stays bare = the inner signal layer for the module fan-in.
    bd.gnd_zone(pcbnew.F_Cu); bd.gnd_zone(pcbnew.B_Cu); bd.gnd_zone(pcbnew.In1_Cu)
    p = bd.save()
    rb = pcbnew.LoadBoard(p); rb.BuildConnectivity()
    unc = rb.GetConnectivity().GetUnconnectedCount(False)
    print(f"{side}: {len(bd.rows_csv)} keys, {rb.GetNetCount()} nets, "
          f"unrouted ratsnest={unc} ({geo['board_w']:.1f}x{geo['board_h']:.1f}mm)")
    # per-key placement/legend CSV (docs + firmware cross-check)
    import csv
    with open(os.path.join(OUT, f"thumbdeck_{side}_placement.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ref", "legend", "row", "col", "x_mm", "y_mm"])
        w.writerows(bd.rows_csv)
    return j2map


def main():
    os.makedirs(OUT, exist_ok=True)
    j2map = gen("right")
    gen("left", right_j2_map=j2map)


if __name__ == "__main__":
    main()
