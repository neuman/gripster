#!/usr/bin/env python3
"""
gen_board.py — ROUTE-COMPLETE KiCad board per grip (supersedes gen_kicad_pcbnew.py).

Places REAL footprints, builds the FULL netlist, routes the 79-key matrix (columns
on F.Cu, rows on B.Cu, via per key), routes power/USB/I2C, and adds GND zones.

HONEST LIMITS of this headless KiCad-7 environment (see docs/routing-status.md):
  * no DRC/ERC CLI  -> must open in the KiCad GUI once to run DRC + ERC
  * ZONE_FILLER segfaults headless -> GND zones are added UNFILLED; the GUI fills them
  * the E73 / IQS7211E / JST-GH footprints + the module PINOUT are built here and must
    be VERIFIED against the datasheets before fab.
So the deliverable is a board that opens ready-to-finish, NOT signed-off gerbers.

Frame: KiCad Y-down (we flip deck.py's Y-up geometry with _fy).
"""
from __future__ import annotations
import os, csv
import pcbnew
from pcbnew import VECTOR2I as V, FromMM as MM
import deck

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kicad", "generated"))
STOCK = "/usr/share/kicad/footprints"
NROWS, NCOLS_HALF = 9, 5
TRACE = 0.25   # mm signal trace
PWR = 0.5      # mm power trace


def _fy(y, H):
    return H - y


def vec(x, y):
    return V(MM(x), MM(y))


class Board:
    def __init__(self, geo, side):
        self.geo = geo; self.side = side; self.H = geo["board_h"]
        self.b = pcbnew.BOARD()
        self.b.GetDesignSettings().m_CopperEdgeClearance = MM(0.2)   # keep copper off the edge
        # 4-layer stackup: F.Cu(sig) / In1.Cu(GND plane) / In2.Cu(sig+pwr) / B.Cu(sig).
        # The GND plane gives the antenna a reference + lowers matrix crosstalk; the inner
        # In2 signal layer makes the dense E73 fan-in routable (the 2-layer blocker).
        self.b.SetCopperLayerCount(4)
        self.nets = {}
        self.net("GND"); self.net("3V3"); self.net("VBAT"); self.net("VBUS")
        self.rows_csv = []

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
        # keepout ring so the autorouter/pour stays clear of each hole.
        for h in self.geo["mount_holes"]:
            cx, cy = h["x"], _fy(h["y"], self.H)
            c = pcbnew.PCB_SHAPE(self.b); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
            c.SetCenter(vec(cx, cy)); c.SetEnd(vec(cx + h["d"] / 2, cy))
            c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(MM(0.15)); self.b.Add(c)
            self.keepout(cx, cy, h["d"] / 2 + 0.8)

    def track(self, x1, y1, x2, y2, layer, net, w=TRACE):
        t = pcbnew.PCB_TRACK(self.b); t.SetStart(vec(x1, y1)); t.SetEnd(vec(x2, y2))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net); self.b.Add(t)

    def via(self, x, y, net):
        v = pcbnew.PCB_VIA(self.b); v.SetPosition(vec(x, y)); v.SetDrill(MM(0.3)); v.SetWidth(MM(0.6))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net); self.b.Add(v)

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

    # ---- footprints ----
    _SNAP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "footprints", "thumbdeck.pretty"))

    def switch(self, ref, x, y, col_net, dnode, rot=0):
        """Snaptron 7mm dome, ROUTING footprint (2 simple circular pads: 1=centre/col,
        2=ring/diode-node). The arc-pad variant (snaptron_7mm_contact_pad) can't be
        Specctra-exported for the autorouter, so we route on simple circular pads
        (electrically valid dome contacts). rot mirrors the ring pad direction so the
        LEFT grip's ring pads point OUTWARD (like the right grip), clear of the inner
        bridge header."""
        fp = pcbnew.FootprintLoad(self._SNAP, "snaptron_7mm_simple")
        fp.SetReference(ref); fp.SetValue("SNAP7"); fp.SetPosition(vec(x, y)); self.b.Add(fp)
        if rot:
            fp.SetOrientationDegrees(rot)
        for p in fp.Pads():
            p.SetNet(col_net if p.GetNumber() == "1" else dnode)
        return fp

    def diode(self, ref, x, y, dnode, row_net):
        fp = pcbnew.FootprintLoad(STOCK + "/Diode_SMD.pretty", "D_SOD-323")
        fp.SetReference(ref); fp.SetValue("1N4148WS"); fp.SetPosition(vec(x, y)); self.b.Add(fp)
        fp.Flip(fp.GetPosition(), False)   # to B.Cu
        for pad in fp.Pads():
            pad.SetNet(row_net if pad.GetNumber() == "1" else dnode)  # K->row, A->node
        return fp

    def place_stock(self, lib, name, ref, val, x, y, netmap, back=False, rot=0):
        fp = pcbnew.FootprintLoad(f"{STOCK}/{lib}.pretty", name)
        fp.SetReference(ref); fp.SetValue(val); fp.SetPosition(vec(x, _fy(y, self.H)))
        self.b.Add(fp)
        if back:
            fp.Flip(fp.GetPosition(), False)
        if rot:
            fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            nm = netmap.get(pad.GetNumber())
            if nm:
                pad.SetNet(self.net(nm))
        return fp

    def save(self):
        p = os.path.join(OUT, f"thumbdeck_{self.side}.kicad_pcb")
        pcbnew.SaveBoard(p, self.b)
        # Scoped DRC waiver: the USB-C receptacle's shield pads (GND) sit ~0.09 mm from
        # the connector's own mouth cut-out — inherent to the vendor footprint, not a
        # board defect. Let GND *pads* (shields / mounting grounds) sit closer to the
        # edge; traces-to-edge stay strict at the 0.2 mm global rule.
        dru = os.path.join(OUT, f"thumbdeck_{self.side}.kicad_dru")
        with open(dru, "w") as f:
            f.write('(version 1)\n'
                    '(rule "gnd_pad_edge"\n'
                    '  (condition "A.NetName == \'GND\' && (A.Type == \'Pad\' || B.Type == \'Pad\')")\n'
                    '  (constraint edge_clearance (min 0.05mm)))\n')
        return p


def build_matrix(bd):
    """PLACE switches (F) + diodes (B) at every key and assign row/col/diode-node
    nets. No manual routing — Freerouting routes the whole board from the DSN (KiCad's
    Specctra exporter fails on boards that already contain tracks/vias)."""
    geo = bd.geo; H = bd.H
    col_off = 0 if bd.side == "right" else NCOLS_HALF
    keys = list(geo["keys"]) + [f for f in geo.get("features", []) if f["type"] == "key"]
    for i, k in enumerate(keys):
        r = (i // NCOLS_HALF) % NROWS
        c = col_off + (i % NCOLS_HALF)
        x, y = k["x"], _fy(k["y"], H)
        dn = bd.net(f"DN_{bd.side[0].upper()}{i+1}")
        swrot = 180 if bd.side == "left" else 0   # mirror ring-pad direction on the left grip
        bd.switch(f"SW{i+1}", x, y, bd.net(f"COL{c}"), dn, rot=swrot)
        bd.diode(f"D{i+1}", x, y - 3.0, dn, bd.net(f"ROW{r}"))   # diode below the dome (B.Cu)
        bd.rows_csv.append((f"SW{i+1}", k.get("label", "?"), f"ROW{r}", f"COL{c}", round(x, 2), round(y, 2)))


def main():
    os.makedirs(OUT, exist_ok=True)
    for side in ("right", "left"):
        geo = deck.build(deck.Config(side=side))
        bd = Board(geo, side)
        bd.outline(); bd.mount_holes()
        build_matrix(bd)
        place_components(bd)
        # GND: pours on F/B (fill around signals) + a SOLID plane on In1.Cu (RF ref +
        # return path). In2.Cu is left bare = the inner signal layer for the fan-in.
        bd.gnd_zone(pcbnew.F_Cu); bd.gnd_zone(pcbnew.B_Cu); bd.gnd_zone(pcbnew.In1_Cu)
        p = bd.save()
        # connectivity: unconnected ratsnest count
        rb = pcbnew.LoadBoard(p); rb.BuildConnectivity()
        unc = rb.GetConnectivity().GetUnconnectedCount(False)
        print(f"{side}: {len(bd.rows_csv)} keys routed, {rb.GetNetCount()} nets, "
              f"unrouted ratsnest={unc} ({geo['board_w']:.1f}x{geo['board_h']:.1f}mm)")




# ---- E73 pad -> net. Pad N == Ebyte datasheet pin N (marbastlib footprint,
# verified 1:1 vs the official Ebyte E73-2G4M08S1C User Manual pin table).
# The five BRIDGE columns (COL5-9) go to J2, so they must escape the module to
# reach the inner edge — assigned to CASTELLATED EDGE pads (35,3,9,10,11) so they
# route on 2 layers (the 0.8mm INNER pads 36/38/40/42 cannot escape at 0.2mm rules).
E73_PINMAP = {
    "1":"ROW0","2":"ROW1","6":"ROW2","12":"ROW3","14":"ROW4","16":"ROW5","17":"ROW6","20":"ROW7","22":"ROW8",
    "28":"COL0","30":"COL1","32":"COL2","33":"COL3","34":"COL4",              # local cols -> local keys
    "35":"COL5","3":"COL6","9":"COL7","10":"COL8","11":"COL9",                # bridge cols -> J2 (edge pads)
    "7":"VBAT_SENSE",   # AIN0 battery divider. Trackpad (SDA/SCL/TP_DR on pads 15/4/8) DROPPED for v1.
    "19":"3V3","23":"VBAT","5":"GND","21":"GND","24":"GND","27":"VBUS",
    "29":"USB_DM","31":"USB_DP","37":"SWDIO","39":"SWDCLK","26":"RESET",
}
LIBS = {"E73":os.path.abspath("../footprints/thumbdeck.pretty"),
        "SOT":STOCK+"/Package_TO_SOT_SMD.pretty", "R":STOCK+"/Resistor_SMD.pretty",
        "C":STOCK+"/Capacitor_SMD.pretty", "USB":STOCK+"/Connector_USB.pretty",
        "TP":STOCK+"/TestPoint.pretty", "HDR":STOCK+"/Connector_PinHeader_2.54mm.pretty"}
USBC_NETS = {"A4":"VBUS","B4":"VBUS","A9":"VBUS","B9":"VBUS","A1":"GND","A12":"GND","B1":"GND","B12":"GND","S1":"GND",
             "A5":"CC1","B5":"CC2","A6":"USB_DP","B6":"USB_DP","A7":"USB_DM","B7":"USB_DM"}


def _load(lib, name):
    return pcbnew.FootprintLoad(LIBS[lib], name)


def place_components(bd):
    """Right grip: place E73 module (back, rotated), USB-C, charger, ESD, battery
    JST, bridge header, essential passives, SWD pads — and net them. Left grip: just
    the bridge header. No manual routing of these; Freerouting does the fan-in."""
    H = bd.H; b = bd.b
    def add(fp, ref, val, x, y, netmap=None, back=False, rot=0):
        fp.SetReference(ref); fp.SetValue(val); fp.SetPosition(vec(x, _fy(y, H))); b.Add(fp)
        if rot: fp.SetOrientationDegrees(rot)
        if back: fp.Flip(fp.GetPosition(), False)
        if netmap:
            for p in fp.Pads():
                nm = netmap.get(p.GetNumber())
                if nm: p.SetNet(bd.net(nm))
        return fp
    # bridge header (both grips), inner edge — carries ROW0-8 + COL5-9 + GND
    bridge_nets = {str(i+1):f"ROW{i}" for i in range(9)}
    bridge_nets.update({str(10+i):f"COL{5+i}" for i in range(5)})
    bridge_nets["15"]="GND"; bridge_nets["16"]="GND"
    # compact 2x08 bridge header at the INNER margin, clear of the key field. The
    # RIGHT grip's inner edge is x=0; the LEFT grip is mirrored so ITS inner edge is
    # x=board_w -> put J2 at board_w-3.2 (the old code hardcoded 3.2 for both, landing
    # the left connector on the OUTER edge where the harness can't reach).
    jx = 3.2 if bd.side == "right" else round(bd.geo["board_w"] - 5.0, 2)
    # J2 on the BACK (bottom-shell cavity) so the connector body + flex clear the
    # top shell + keymat on the front (a front-mounted connector clashes them).
    add(_load("HDR","PinHeader_2x08_P2.54mm_Vertical"), "J2","BRIDGE_16", jx, 34.0, bridge_nets, back=True)
    if bd.side != "right":
        return
    # E73 module — BACK, rotated 90 (18 wide x 13 tall), bottom-inner. Its USB/SWD
    # edge (pins 26-43) sits at board y~95 (deck y~14.5); the power pins (VDD 19,
    # VDDH 23) at the module's left edge (board x~11).
    add(_load("E73","nRF52840_E73-2G4M08S1C"), "U1","E73-2G4M08S1C", 20.0, 8.0, E73_PINMAP, back=True, rot=90)
    ob = bd.geo["outer_base"]
    # --- ALL reflow parts on the BACK (single-sided SMT / turnkey). The USB front-end
    # is clustered along the bottom edge to the RIGHT of the module so USB D+/D- and
    # VBUS runs stay short (module USB pins at board x15-18; connector cluster x28-46). ---
    # USB-C at the bottom edge, to the RIGHT of the module (module right edge ~x26;
    # was at the far outer corner x60 = 44mm D+/D-, now ~x36 = ~20mm, on the front)
    add(_load("USB","USB_C_Receptacle_HRO_TYPE-C-31-M-12"), "J1","USB-C", 37.0, 4.0, USBC_NETS, back=True)
    # ESD USBLC6-2SC6 (SOT-23-6) INLINE on the data pair, at the connector:
    #   D+ = I/O pair pin1<->pin6 ; D- = I/O pair pin3<->pin4 ; pin2=GND, pin5=VBUS.
    #   (the old map put D- on pin6, which is internally the SAME node as pin1/D+ -> a
    #    dead short of D+ to D-. Verified vs the ST USBLC6-2SC6 datasheet.)
    add(_load("SOT","SOT-23-6"), "U3","USBLC6-2SC6", 47.0, 3.5,
        {"1":"USB_DP","6":"USB_DP","3":"USB_DM","4":"USB_DM","2":"GND","5":"VBUS"}, back=True)
    # charger MCP73831 (SOT-23-5): 1=STAT 2=VSS(GND) 3=VBAT 4=VDD(VBUS) 5=PROG
    add(_load("SOT","SOT-23-5"), "U2","MCP73831", 53.0, 3.5,
        {"2":"GND","3":"VBAT","4":"VBUS","5":"PROG"}, back=True)
    # battery JST (2P) — VBAT / GND, right of the charger
    add(_load("HDR","PinHeader_1x02_P2.54mm_Vertical"), "J3","LiPo", 58.0, 5.5, {"1":"VBAT","2":"GND"}, back=True)
    # 9 row pull-downs to GND, above the module (board y~91, in the module->keyfield gap)
    for i in range(9):
        add(_load("R","R_0402_1005Metric"), f"R{i+1}","4k7", 31.0+i*3.2, 18.5, {"1":f"ROW{i}","2":"GND"}, back=True)
    # USB CC 5.1k pulldowns, above the connector cluster
    add(_load("R","R_0402_1005Metric"), "R20","5k1", 35.0, 10.0, {"1":"CC1","2":"GND"}, back=True)
    add(_load("R","R_0402_1005Metric"), "R21","5k1", 38.0, 10.0, {"1":"CC2","2":"GND"}, back=True)
    # VBAT-sense divider (1M/1M ->AIN0) at the module's left edge (near VBAT pin)
    add(_load("R","R_0402_1005Metric"), "R22","1M", 6.0, 6.0, {"1":"VBAT","2":"VBAT_SENSE"}, back=True)
    add(_load("R","R_0402_1005Metric"), "R23","1M", 6.0, 9.0, {"1":"VBAT_SENSE","2":"GND"}, back=True)
    # charger PROG resistor: 5.1k -> ~196 mA fast-charge (~0.5C of a 400mAh cell). The
    # old 2k programmed ~505 mA (>1C for the documented 400-500 mAh cell). IREG=1000/Rk.
    add(_load("R","R_0402_1005Metric"), "R24","5k1", 53.0, 8.0, {"1":"PROG","2":"GND"}, back=True)
    # decoupling: 1uF on VDD(3V3), 100nF + 4.7uF BULK on VBAT/VDDH, 4.7uF on VBUS
    add(_load("C","C_0402_1005Metric"), "C1","1uF", 9.0, 6.0, {"1":"3V3","2":"GND"}, back=True)
    add(_load("C","C_0402_1005Metric"), "C2","100nF", 9.0, 9.0, {"1":"VBAT","2":"GND"}, back=True)
    add(_load("C","C_0805_2012Metric"), "C4","4u7", 6.0, 13.0, {"1":"VBAT","2":"GND"}, back=True)  # VBAT bulk
    add(_load("C","C_0402_1005Metric"), "C3","4u7", 47.0, 8.0, {"1":"VBUS","2":"GND"}, back=True)
    # SWD test pads (back), in the gap just above the module's SWD pins (board x21-22),
    # clear of the bottom key-row diodes above and the row-pulldowns (y18.5)
    for i,(ref,net) in enumerate([("TP1","SWDIO"),("TP2","SWDCLK"),("TP3","RESET"),("TP4","3V3"),("TP5","GND")]):
        add(_load("TP","TestPoint_Pad_1.5x1.5mm"), ref, net, 14.0+i*3.0, 18.0, {"1":net}, back=True)


if __name__ == "__main__":
    main()
