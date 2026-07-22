#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""report_open.py <board> — print any non-GND nets that are still open (>1 copper
component), so the loop honestly reports what Freerouting left for the GUI finish."""
import sys, os, importlib.util, pcbnew

_spec = importlib.util.spec_from_file_location(
    "rn", os.path.join(os.path.dirname(__file__), "route_nets.py"))
rn = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rn)


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    gnd = b.FindNet("GND").GetNetCode()
    open_nets = []
    for code in range(1, b.GetNetInfo().GetNetCount()):
        if code == gnd:
            continue
        c = rn.components(b, code)
        if len(c) > 1:
            open_nets.append(b.GetNetInfo().GetNetItem(code).GetNetname())
    if open_nets:
        print(f"    STILL OPEN ({len(open_nets)} signal nets): {', '.join(sorted(open_nets))}")
    else:
        print("    all signal nets fully routed")


if __name__ == "__main__":
    main()
