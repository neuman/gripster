#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Eric Neuman
"""gen_screen.py — generate the phone-screen texture (assets/screen_app.jpg).

Uses Google's Gemini 2.5 Flash Image ("nano banana") to render a minimal
landscape writing-app screenshot, then rotates it to the phone's PORTRAIT
1080x2400 texture space (the S25U is modelled portrait; the deck mounts it
landscape, so the app is turned 90deg here to read upright once mounted).

The image is baked onto the phone's "display" material at model-build time by
site/scripts/optimize-models.mjs — so this only needs re-running to change the
ON-SCREEN CONTENT, not on every model rebuild.

    export NANO_BANANA_KEY=...          # kept in ../.env, never committed
    hardware/cad/.venv/bin/python hardware/cad/gen_screen.py
    npm --prefix site run models        # bakes it into the GLB + og-card
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.error
from io import BytesIO
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "screen_app.jpg")
MODEL = os.environ.get("NB_MODEL", "gemini-2.5-flash-image")
TW, TH = 1080, 2400  # phone display texture size (portrait)

PROMPT = os.environ.get("SCREEN_PROMPT", (
    "A clean UI screenshot of a minimalist distraction-free writing app in "
    "LANDSCAPE orientation, filling the entire frame edge to edge with NO phone "
    "bezel, NO status bar, NO rounded corners. Warm off-white paper background. "
    "A single centered column (about 60% width) of dark charcoal SERIF body "
    "text: a short medium-weight title line, then 4-5 short paragraphs of calm "
    "placeholder prose with generous line spacing, and a thin text cursor "
    "mid-sentence. A very subtle slim top bar: tiny document title at left, "
    "faint word count at right. No images, no colorful buttons, no toolbar "
    "clutter. iA Writer / Ulysses aesthetic. Flat, crisp, high resolution."))


def generate(prompt: str) -> Image.Image:
    key = os.environ["NANO_BANANA_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"],
                             "imageConfig": {"aspectRatio": "21:9"}},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        sys.exit(f"nano-banana HTTP {e.code}: {e.read().decode()[:600]}")
    for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        blob = p.get("inlineData") or p.get("inline_data")
        if blob and blob.get("data"):
            return Image.open(BytesIO(base64.b64decode(blob["data"]))).convert("RGB")
    sys.exit("nano-banana returned no image")


def to_texture(landscape: Image.Image) -> Image.Image:
    """Rotate 90deg CCW into portrait, then center-crop to 1080x2400."""
    port = landscape.transpose(Image.Transpose.ROTATE_90)
    w, h = port.size
    port = port.resize((TW, round(h * TW / w)), Image.LANCZOS)
    w, h = port.size
    top = max(0, (h - TH) // 2)
    return port.crop((0, top, TW, top + TH))


def main():
    prompt = " ".join(sys.argv[1:]) or PROMPT
    tex = to_texture(generate(prompt))
    tex.save(OUT, "JPEG", quality=88, optimize=True)
    print(f"wrote {OUT} ({tex.size[0]}x{tex.size[1]})")


if __name__ == "__main__":
    main()
