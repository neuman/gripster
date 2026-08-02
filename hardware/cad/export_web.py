#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""export_web.py — web-optimised assembly for the project homepage viewer.

Reads models/thumbdeck_full_asm.glb (the full nested assembly) and re-emits
models/thumbdeck_web_raw.glb with the SAME geometry collapsed to a small set of
named "mover" meshes — one logical group per explodable part. Node names are
slash-free ("<mover>__<key>") so three.js keeps them verbatim (its property-path
binder mangles "/" and "."). The browser viewer groups meshes back into movers
by that name prefix (see site/public/models/explode.json, authored downstream).

This file does NO coordinate math and NO compression — decimation, quantization,
meshopt compression, the explode vectors and the light proxy all happen in
site/scripts/optimize-models.mjs, which reads coordinates in the SAME space
three.js sees. Run it under the CAD venv (needs trimesh):

    hardware/cad/.venv/bin/python hardware/cad/export_web.py

Node/mesh count drops from ~270 to ~30. The full 24 MB asm stays untouched as
the download / fidelity master; this is the interactive web master (pre-compress).
"""
import os
import re
import collections
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")
SRC = os.path.join(MODELS, "thumbdeck_full_asm.glb")
OUT = os.path.join(MODELS, "thumbdeck_web_raw.glb")

# leaf nodes that ARE their own mover (single printed/loose part)
SINGLE = ("back_left", "back_right", "grip_lid_left",
          "grip_lid_right", "nub_spring", "nub_cap", "keymat_left",
          "keymat_right", "gripper_left", "gripper_right",
          "battery", "flex", "power")

# component nodes kept UN-merged (slash-free rename) so hotspot pins can anchor
# to them precisely; they still ride the pcb_right mover during explode.
PRESERVE = {
    "pcb_right/components/U1": "pcb_right__U1",   # nRF52840 module (E73)
    "pcb_right/components/U2": "pcb_right__U2",   # TMAG5273 hall sensor (nub)
    "pcb_right/components/J1": "pcb_right__J1",   # USB-C receptacle
}

# The KiCad board layers are exported COPLANAR with the FR4 body surface, which
# z-fights in a realtime viewer. Lift each surface layer a few hundredths of a
# mm OUTWARD (along its own normal, so both board faces separate correctly) so
# nothing is coplanar — invisible on a 1.6 mm board, but no depth-buffer tie.
LAYER_LIFT = {"copper": 0.06, "soldermask": 0.12, "silkscreen": 0.18}


def _lift(mv, key, m):
    """Displace a board surface layer outward along its normals (see LAYER_LIFT)."""
    if mv in ("pcb_right", "pcb_left") and key in LAYER_LIFT:
        m = m.copy()
        nrm = m.vertex_normals.copy()
        m.vertices = m.vertices + nrm * LAYER_LIFT[key]
    return m


def mover_of(node):
    """Full-assembly node name -> explode mover id (or None to drop)."""
    if node.startswith("phone"):
        return "phone"
    if node.startswith("pcb_right"):
        return "pcb_right"
    if node.startswith("pcb_left"):
        return "pcb_left"
    if node.startswith("screws"):
        return "screws"
    if node.startswith("spring"):
        return "springs"
    if node in SINGLE:
        return node
    return None


def suffix_of(mv, node, g):
    """Mesh-name suffix (also the merge bucket). The four KiCad board layers are
    kept SEPARATE — body / copper / soldermask / silkscreen — so the web viewer
    can depth-bias them (polygonOffset) instead of letting their coplanar
    surfaces z-fight. Everything else merges by material/appearance."""
    if mv in ("pcb_right", "pcb_left"):
        if "/board/" in node:
            lbl = re.sub(r"_\d+$", "", node.rsplit("/board/", 1)[1])
            return "body" if lbl == "board_body" else lbl  # copper|soldermask|silkscreen
        if "/components/" in node:
            return "components"
    v = g.visual
    if isinstance(v, trimesh.visual.TextureVisuals):
        return getattr(v.material, "name", "pbr") or "pbr"
    return "vc"   # loose vertex-coloured bodies (battery, flex, ring)


def main():
    scene = trimesh.load(SRC, process=False)

    members = collections.defaultdict(list)   # mover -> [(node, geom)]
    preserved = []                            # [(new_name, geom)]
    dropped = []
    for node in scene.graph.nodes_geometry:
        T, gname = scene.graph[node]
        g = scene.geometry[gname].copy()
        if not np.allclose(T, np.eye(4)):
            g.apply_transform(T)              # safety: bake residual transform
        if node in PRESERVE:
            preserved.append((PRESERVE[node], g))
            continue
        mv = mover_of(node)
        if mv is None:
            dropped.append(node)
            continue
        members[mv].append((node, g))

    out = trimesh.Scene()

    def add(geom, name):
        out.add_geometry(geom, node_name=name, geom_name=name)

    for mv, items in members.items():
        if mv == "phone":
            # keep phone submeshes (own materials: screen texture / glass / cameras)
            for i, (node, g) in enumerate(items):
                add(g, f"phone__{i}")
            continue
        buckets = collections.defaultdict(list)
        for node, g in items:
            buckets[suffix_of(mv, node, g)].append(g)
        for key, gs in buckets.items():
            try:
                m = gs[0] if len(gs) == 1 else trimesh.util.concatenate(gs)
            except Exception:
                for j, gg in enumerate(gs):
                    add(_lift(mv, key, gg), f"{mv}__{key}_{j}")
                continue
            add(_lift(mv, key, m), f"{mv}__{key}")

    for name, g in preserved:
        add(g, name)

    os.makedirs(MODELS, exist_ok=True)
    out.export(OUT)
    b = out.bounds
    print(f"wrote {OUT}")
    print(f"  movers   : {sorted(members.keys())}")
    print(f"  preserved: {[n for n, _ in preserved]}")
    print(f"  dropped  : {dropped if dropped else 'none'}")
    print(f"  nodes    : {len(out.graph.nodes_geometry)}  geoms: {len(out.geometry)}")
    print(f"  bounds mm: {np.round(b[0], 1)} .. {np.round(b[1], 1)}  "
          f"extent {np.round(b[1] - b[0], 1)}")
    return out


if __name__ == "__main__":
    main()
