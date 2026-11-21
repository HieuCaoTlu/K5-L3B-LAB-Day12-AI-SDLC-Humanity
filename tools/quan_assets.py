"""Build the small Quán pixel sprites matching the repository's canvas mock.

Requires Pillow. Run: python3 tools/quan_assets.py build|check|preview
All drawing uses native integer pixels, then nearest-neighbor at exactly 4x.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "chonoi/web/assets/quan"
PROOF = ROOT / "docs/proof"
MANIFEST = ASSETS / "manifest.json"
P = {
    "night": "#0d2a38", "water": "#14485a", "wave": "#1c6676",
    "wood": "#a8703c", "wood_light": "#bb8248", "wood_dark": "#6e4422",
    "rim": "#4a2b14", "rim_dark": "#2e1a0c", "ink": "#241410",
    "skin": "#e8b07a", "skin_dark": "#c98a55",
    "hat": "#e8cf8a", "hat_dark": "#bf9f55",
    "shirt": "#2f7f78", "shirt_dark": "#1f5a56",
    "apron": "#efe6d0", "stain": "#b9854c",
    "red": "#d6402f", "red_dark": "#8f2a1f", "gold": "#ffd36b",
    "fire": "#ff8a1f", "yellow": "#ffd23f", "green": "#7bd66b",
    "steam": "#e9f2f0", "metal": "#5a5f66", "metal_dark": "#34383e",
}


def blank(size):
    return Image.new("RGBA", size)


def r(image, color, x, y, width=1, height=1):
    if width > 0 and height > 0:
        ImageDraw.Draw(image).rectangle((x, y, x + width - 1, y + height - 1), fill=P.get(color, color))


def person(direction="front", phase=None, carrying=False):
    if direction == "left":
        return ImageOps.mirror(person("side", phase, carrying))
    image = blank((24, 32))
    x, y = 12, 27
    bob = phase if phase is not None else 0
    yy = y - 16 + bob
    # Same blocks, palette and proportions as drawPerson in the canvas mock.
    r(image, "skin_dark", x - 4, y - 3 + (0 if phase == 1 else 1), 3, 4)
    r(image, "skin_dark", x + 1, y - 3 + (1 if phase == 1 else 0), 3, 4)
    r(image, "shirt", x - 5, yy + 8, 10, 8)
    r(image, "shirt_dark", x - 5, yy + 8, 10, 1)
    if direction == "back":
        r(image, "shirt_dark", x - 4, yy + 9, 8, 6)
        r(image, "apron", x - 4, yy + 12, 8, 1)
        r(image, "apron", x - 1, yy + 12, 2, 3)
    else:
        r(image, "apron", x - 3, yy + 9, 6, 7)
        r(image, "stain", x - 1, yy + 12, 3, 2)
        r(image, "stain", x - 3, yy + 15, 2, 1)
    swing = (1 if phase == 1 else 0) if not carrying else 0
    r(image, "skin", x - 7, yy + 9 + swing, 2, 4)
    r(image, "skin", x + 5, yy + 10 - swing, 2, 4)
    r(image, "skin_dark", x - 5, yy + 2, 10, 8)
    r(image, "skin", x - 4, yy + 3, 8, 6)
    if direction == "back":
        r(image, "#3a2416", x - 4, yy + 3, 8, 6)
    else:
        for ex in ([-3, 1] if direction == "front" else [1]):
            r(image, "ink", x + ex, yy + 5, 2, 2)
            r(image, "#ffffff", x + ex, yy + 5)
        r(image, "#c8504a", x + (-1 if direction == "front" else 2), yy + 8, 2, 1)
    for color, dx, dy, width, height in (
        ("hat_dark", -9, 3, 18, 2), ("hat", -8, 2, 16, 1),
        ("hat_dark", -6, 0, 12, 2), ("hat", -4, -2, 8, 2),
        ("hat_dark", -2, -4, 4, 2), ("hat", -1, -5, 2, 1),
        ("red", -5, 5, 1, 4), ("red", 4, 5, 1, 4),
    ):
        r(image, color, x + dx, yy + dy, width, height)
    if carrying:
        if direction == "back":
            r(image, "skin", x - 7, yy + 9, 3, 2)
            r(image, "skin", x + 4, yy + 9, 3, 2)
            r(image, "apron", x - 6, yy + 8, 2, 1)
            r(image, "apron", x + 4, yy + 8, 2, 1)
        else:
            bx = x - 6 if direction == "front" else x
            r(image, "skin", bx - 1, yy + 11, 2, 3)
            r(image, "skin", bx + 10, yy + 11, 2, 3)
            r(image, "ink", bx, yy + 10, 11, 3)
            r(image, "ink", bx + 1, yy + 13, 9, 2)
            r(image, "#fffaf0", bx + 1, yy + 11, 9, 2)
            r(image, "apron", bx + 2, yy + 13, 7, 1)
    return image


def customer(kind, mood="cho", phase=0):
    image = blank((24, 32))
    x, y = 12, 13
    fur, shade, shirt = [
        ("#d9a466", "#a9743c", "#9b4d3b"),
        ("#fff1d0", "#d9b98b", "#a84f68"),
        ("#fff2cf", "#decf9d", "#477d73"),
        ("#85b45d", "#567c42", "#99623c"),
    ][kind]
    r(image, "rim", x - 8, y + 7, 16, 12)
    r(image, shirt, x - 7, y + 8, 14, 10)
    r(image, shade, x - 7, y + 17, 5, 2)
    r(image, shade, x + 2, y + 17, 5, 2)
    if kind == 0:
        r(image, "wood_dark", x - 12, y - 4, 5, 11)
        r(image, "wood_dark", x + 7, y - 4, 5, 11)
    elif kind == 1:
        for dy in range(5):
            r(image, shade, x - 8, y - 10 + dy, dy + 1, 1)
            r(image, shade, x + 7 - dy, y - 10 + dy, dy + 1, 1)
    elif kind == 3:
        r(image, shade, x - 9, y - 9, 6, 5)
        r(image, shade, x + 3, y - 9, 6, 5)
    r(image, shade, x - 8, y - 6, 16, 15)
    r(image, fur, x - 7, y - 5, 14, 13)
    if kind == 0:
        r(image, "apron", x - 4, y + 2, 8, 6)
        r(image, "ink", x - 2, y + 2, 4, 2)
        r(image, "hat_dark", x - 8, y - 8, 16, 2)
        r(image, "hat", x - 6, y - 10, 12, 2)
    elif kind == 1:
        r(image, "#e8b47a", x + 2, y - 5, 4, 3)
        r(image, "#d77f8f", x - 1, y + 2, 2, 1)
        r(image, "apron", x + 5, y - 9, 3, 2)
        r(image, shirt, x + 7, y - 10, 2, 2)
        r(image, shade, x - 10, y + 3, 3, 1)
        r(image, shade, x + 7, y + 3, 3, 1)
    elif kind == 2:
        r(image, "#dc8539", x - 5, y + 2, 10, 3)
        r(image, "#f5b454", x - 4, y + 2, 8, 1)
        r(image, "hat", x - 7, y - 8, 14, 2)
    else:
        r(image, "hat_dark", x - 10, y - 8, 20, 2)
        r(image, "hat", x - 7, y - 10, 14, 2)
        r(image, "hat", x - 3, y - 12, 6, 2)
    for ex in (-6, 2):
        if mood == "an":
            r(image, "ink", x + ex, y, 4, 1)
            r(image, "ink", x + ex + 1, y - 1, 2, 1)
        else:
            r(image, "#ffffff", x + ex, y - 2, 4, 4)
            r(image, "ink", x + ex + 1, y - 1 + (mood == "gian"), 2, 2)
            if mood == "gian":
                r(image, "ink", x + ex - 1, y - 4, 5, 1)
                r(image, "ink", x + ex, y - 3, 3, 1)
    if mood == "an":
        r(image, "ink", x - 3, y + 6, 6, 2 + phase)
        r(image, "#e8798c", x - 2, y + 7, 4, 1 + phase)
        r(image, fur, x - 8, y + 10, 3, 3)
        r(image, fur, x + 5, y + 10, 3, 3)
    elif mood == "vui":
        r(image, "ink", x - 4, y + 6, 8, 1)
        r(image, "ink", x - 3, y + 7, 6, 2)
        r(image, "#e8798c", x - 2, y + 8, 4, 1)
        r(image, "#f2a0a8", x - 7, y + 3, 2, 1)
        r(image, "#f2a0a8", x + 5, y + 3, 2, 1)
    elif mood == "gian":
        r(image, "ink", x - 3, y + 7, 6, 1)
        r(image, "ink", x - 4, y + 8)
        r(image, "ink", x + 3, y + 8)
    else:
        r(image, "ink", x - 2, y + 7, 4, 1)
    return image


def stove(state="idle", phase=0):
    image = blank((32, 32))
    r(image, "metal_dark", 6, 16, 20, 13)
    r(image, "metal", 7, 17, 18, 11)
    for index in range(3):
        x = 9 + index * 6
        r(image, "metal_dark", x, 21, 3, 5)
        if state != "idle":
            height = 3 + (phase + index) % 3
            r(image, "fire", x, 26 - height, 3, height)
            r(image, "yellow", x + 1, 27 - height, 1, height - 1)
    r(image, "ink", 8, 27, 16, 1)
    r(image, "metal_dark", 8, 10, 16, 7)
    r(image, "#8a6a3a" if state == "ready" else "#3b3f46", 9, 11, 14, 4)
    r(image, "metal_dark", 4, 12, 4, 2)
    r(image, "metal_dark", 24, 12, 4, 2)
    if state == "cooking":
        for index in range(3):
            x = 12 + index * 4
            y = 3 + (phase + index * 2) % 5
            r(image, "steam", x, y, 1, 2)
            r(image, "steam", x + (1 if phase % 2 else -1), y - 1)
    if state == "ready":
        r(image, "green", 11, 12, 10, 2)
        r(image, "metal", 18, 6, 8, 3)
        r(image, "metal_dark", 20, 5, 4, 1)
        r(image, "green", 7, 5 + phase, 1, 3)
        r(image, "green", 6, 6 + phase, 3, 1)
    return image


def table():
    image = blank((32, 32))
    r(image, "rim_dark", 10, 24, 12, 6)
    r(image, "wood_dark", 11, 24, 10, 4)
    for y in range(-12, 13):
        width = round(math.sqrt(144 - y * y) * 1.12)
        r(image, "wood_dark", 16 - width - 1, 15 + y, 2 * width + 2, 1)
        r(image, "wood" if abs(y) % 4 == 0 else "wood_light", 16 - width, 15 + y, 2 * width, 1)
    r(image, "#8d5a2e", 11, 13, 8, 1)
    return image


def water(phase=0):
    image = Image.new("RGBA", (64, 64), P["night"])
    for y in range(4, 60, 4):
        for x in range(4, 56, 4):
            if ((x // 4 + y // 4 * 3 + phase) & 7) == 0:
                r(image, "wave", x, y, 4, 1)
            if (x // 4 * 5 + y // 4 + phase) % 13 == 0:
                r(image, "water", x, y + 2, 6, 1)
    for x, y in ((12, 16), (44, 44)):
        r(image, "#8d7034", x + phase, y, 3, 1)
        r(image, "#bf9f55", x + phase + 1, y + 2, 2, 1)
    return image


def deck():
    image = blank((256, 160))
    r(image, "rim_dark", 1, 1, 254, 158)
    r(image, "rim", 2, 2, 252, 156)
    for y in range(6, 154, 8):
        r(image, "wood" if (y // 8) % 2 else "#b07a44", 5, y, 246, min(7, 154 - y))
        if y + 7 < 154:
            r(image, "wood_dark", 5, y + 7, 246, 1)
        for x in range(5 + (y // 8 * 53) % 96, 251, 96):
            r(image, "wood_dark", x, y, 1, min(7, 154 - y))
        for index in range(3):
            x = 6 + (y * 7 + index * 83) % 242
            r(image, "#8d5a2e", x, y + 3, 2, 1)
    for x, y in ((9, 9), (246, 9), (9, 150), (246, 150)):
        for dy in range(-7, 8):
            for dx in range(-7, 8):
                if abs(dx) + abs(dy) < 10 and (dx + dy) % 2 == 0:
                    r(image, "#bc8d47", x + dx, y + dy)
    return image


def ingredient(name):
    image = blank((16, 16))
    if name in ("ca_loc", "ca_linh"):
        rows = [(2, 5, 10)] if name == "ca_loc" else [(2, 2, 7), (4, 6, 7), (2, 10, 7)]
        for x, y, width in rows:
            r(image, "#3f6b2c" if name == "ca_loc" else "#8d9399", x, y, width, 5)
            r(image, "#7c9a52" if name == "ca_loc" else "#cfd3d6", x, y + 1, width, 3)
            r(image, "#d6e0a0" if name == "ca_loc" else "#f4f4e8", x + 1, y + 3, width - 2, 1)
            r(image, "ink", x + 1, y + 1)
            r(image, "#3f6b2c" if name == "ca_loc" else "#8d9399", x + width, y - 1, 2, 7)
    elif name == "bong_dien_dien":
        r(image, "#477d39", 7, 5, 2, 9)
        for x, y in ((3, 3), (8, 2), (5, 7), (10, 6), (2, 10)):
            r(image, "#6b9a42", x + 1, y + 2, 3, 1)
            r(image, "#f2c230", x, y, 4, 3)
            r(image, "#ffe27a", x + 1, y, 2, 1)
    else:
        r(image, "#477d39", 7, 9, 2, 5)
        r(image, "#79a153", 9, 11, 4, 2)
        for x, y, width in ((6, 2, 3), (3, 4, 9), (2, 6, 11), (4, 8, 7)):
            r(image, "#ad527c", x, y, width, 2)
            r(image, "#e8799c", x + 1, y, max(1, width - 2), 1)
        r(image, "#ffd23f", 6, 6, 3, 2)
    return image


def dish(name):
    image = blank((16, 16))
    if name == "ca_loc_nuong_trui":
        r(image, "#d6e0a0", 2, 5, 12, 5)
        r(image, "#7c9a52", 3, 6, 9, 3)
        r(image, "#65472a", 4, 6, 7, 2)
        r(image, "ink", 4, 6)
        r(image, "#7c9a52", 12, 4, 2, 7)
        r(image, "#3f6b2c", 3, 10, 10, 1)
    elif name == "goi_bong_sung":
        r(image, "ink", 3, 7, 10, 5)
        r(image, "apron", 3, 7, 10, 3)
        r(image, "apron", 4, 10, 8, 2)
        r(image, "#e8799c", 5, 5, 6, 3)
        r(image, "green", 6, 8, 4, 2)
        r(image, "wood_dark", 11, 10)
    else:
        r(image, "metal_dark", 3, 7, 10, 5)
        r(image, "metal_dark", 1, 8, 2, 2)
        r(image, "metal_dark", 13, 8, 2, 2)
        r(image, "#e8933a", 4, 6, 8, 3)
        r(image, "#f2c230", 5, 6, 2, 1)
        r(image, "green", 9, 7, 2, 1)
        r(image, "#cfd3d6", 7, 8, 2, 1)
        r(image, "steam", 6, 3, 1, 2)
        r(image, "steam", 9, 2, 1, 2)
    return image


def lantern(phase=0):
    image = blank((16, 24))
    r(image, "rim_dark", 7, 2, 2, 4)
    r(image, "red_dark", 4, 6, 8, 11)
    r(image, "red", 5, 6, 6, 10)
    r(image, "gold", 7, 9, 2, 4 + phase)
    r(image, "rim_dark", 5, 6, 6, 1)
    r(image, "rim_dark", 5, 15, 6, 1)
    r(image, "gold", 8, 17, 1, 3)
    return image


def ui(name):
    size = (24, 24) if name == "bong_bong_dat_mon" else (128, 24) if name == "khung_hud" else (16, 16) if name.startswith("emote") else (12, 12)
    image = blank(size)
    if name == "bong_bong_dat_mon":
        r(image, "ink", 1, 1, 22, 18)
        r(image, "#fffaf0", 2, 2, 20, 16)
        r(image, "ink", 4, 18, 4, 4)
        r(image, "#fffaf0", 5, 18, 2, 3)
    elif name == "khung_hud":
        r(image, "rim_dark", 0, 1, 128, 22)
        r(image, "wood_dark", 1, 2, 126, 20)
        r(image, "wood", 2, 2, 124, 2)
        r(image, "rim", 2, 20, 124, 2)
        ImageDraw.Draw(image).rectangle((4, 5, 123, 18), fill=(0, 0, 0, 0))
        for x in (2, 124):
            r(image, "hat_dark", x, 4, 2, 2)
            r(image, "hat_dark", x, 18, 2, 2)
    elif name == "dong_xu":
        r(image, "ink", 1, 1, 10, 10)
        r(image, "#f2c230", 2, 2, 8, 8)
        r(image, "#ffe27a", 3, 3, 3, 3)
        r(image, "#b8861a", 6, 4, 1, 5)
    elif name == "dong_ho":
        r(image, "ink", 1, 1, 10, 10)
        r(image, "#fff6d8", 2, 2, 8, 8)
        r(image, "ink", 5, 3, 1, 4)
        r(image, "ink", 5, 6, 3, 1)
    elif name == "phim_e":
        r(image, "ink", 1, 1, 10, 10)
        r(image, "#fff6d8", 2, 2, 8, 7)
        r(image, "#d9c58a", 2, 9, 8, 1)
        r(image, "ink", 4, 3, 1, 5)
        for y, width in ((3, 4), (5, 3), (7, 4)):
            r(image, "ink", 4, y, width, 1)
    elif name.startswith("sao"):
        points = [(5, 1), (6, 1), (5, 2), (6, 2)]
        for y, start, stop in ((3, 4, 7), (4, 1, 10), (5, 2, 9), (6, 3, 8), (7, 3, 8), (8, 3, 8), (9, 2, 4), (9, 7, 9)):
            points.extend((x, y) for x in range(start, stop + 1))
        points = set(points)
        for x, y in points:
            edge = any((x + dx, y + dy) not in points for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if not name.endswith("rong") or edge:
                r(image, "#bf9f55" if name.endswith("rong") else "yellow", x, y)
    elif name == "emote_vui":
        for y, start, width in ((3, 3, 4), (3, 9, 4), (4, 2, 12), (5, 2, 12), (6, 3, 10), (7, 4, 8), (8, 5, 6), (9, 6, 4), (10, 7, 2)):
            r(image, "#e8798c", start, y, width, 1)
        r(image, "#ffd2d4", 4, 4, 2, 1)
    elif name == "emote_doi":
        r(image, "ink", 5, 1, 6, 10)
        r(image, "yellow", 6, 2, 4, 8)
        r(image, "ink", 5, 12, 6, 3)
        r(image, "yellow", 6, 12, 4, 2)
    else:
        r(image, "metal_dark", 3, 4, 10, 5)
        r(image, "metal", 5, 2, 6, 7)
        r(image, "metal_dark", 2, 5, 12, 3)
        r(image, "red", 6, 9, 3, 2)
        r(image, "red", 5, 11, 3, 2)
        r(image, "yellow", 7, 10, 2, 1)
    return image


def prop(name):
    if name == "xuong_khach":
        image = blank((48, 24))
        for y in range(7, 19):
            inset = abs(y - 12) // 2
            r(image, "rim_dark", 2 + inset, y, 44 - inset * 2, 1)
        r(image, "wood_dark", 7, 9, 34, 7)
        r(image, "wood", 8, 10, 32, 2)
        for x in (13, 32):
            r(image, "rim_dark", x, 9, 3, 7)
        for index in range(10):
            r(image, "hat_dark", 6 + index * 2, 19 - index, 3, 1)
        return image
    image = blank((24, 24))
    if name == "trang_tri_1":
        r(image, "ink", 5, 7, 14, 13)
        r(image, "#7ba3a4", 6, 8, 12, 11)
        r(image, "#b8d3cb", 7, 9, 3, 8)
        r(image, "#547d83", 6, 17, 12, 3)
        r(image, "ink", 6, 5, 12, 3)
        r(image, "#b8d3cb", 7, 5, 10, 1)
        r(image, "night", 8, 6, 8, 1)
        r(image, "ink", 16, 5, 2, 2)
    else:
        r(image, "rim_dark", 4, 11, 16, 10)
        r(image, "stain", 5, 12, 14, 8)
        for x in (7, 11, 15):
            r(image, "wood_dark", x, 13, 1, 7)
        for x, y in ((5, 8), (9, 5), (13, 7)):
            r(image, "#477d39", x, y, 6, 6)
            r(image, "#90b957", x + 1, y, 3, 2)
        r(image, "hat_dark", 4, 11, 16, 2)
    return image


def effect(name, phase=0):
    image = blank((16, 16))
    if name == "khoi":
        for index in range(3):
            x = 5 + ((index + phase) % 3) * 2
            y = 11 - index * 4
            r(image, (233, 242, 240, 160), x - 1, y, 4, 2)
            r(image, "steam", x, y - 1, 2, 2)
    elif name == "lua":
        for y in range(3, 14):
            half = min(5, (y - 2) // 2 + 1, 14 - y)
            shift = (phase - 1) if y < 7 else 0
            r(image, "fire", 8 - half + shift, y, half * 2, 1)
            if y > 7:
                r(image, "yellow", 7, y, 2, 1)
    else:
        r(image, "#5fc4c4", 3, 12, 10, 1)
        for index, x in enumerate((3, 7, 11)):
            y = 3 + (phase + index) % 3 * 2
            r(image, "#5fc4c4", x, y, 2, 3)
            r(image, "#c7f0e3", x, y, 1, 2)
        r(image, "wave", 5, 10, 2, 2)
        r(image, "wave", 10, 9, 2, 2)
    return image


def end_card():
    image = water().resize((200, 113), Image.Resampling.NEAREST)
    image.alpha_composite(deck().resize((190, 100), Image.Resampling.NEAREST), (5, 7))
    for x in (16, 168):
        image.alpha_composite(lantern(), (x, 5))
    for kind, x in enumerate((23, 64, 106, 148)):
        image.alpha_composite(customer(kind, "vui"), (x, 58))
        image.alpha_composite(table(), (x - 4, 79))
    image.alpha_composite(person("front", carrying=True), (88, 30))
    return image


def build():
    assets, animations = [], {}

    def save(path, image, priority, opaque=False, size=None, anchor=None):
        target = ASSETS / path
        target.parent.mkdir(parents=True, exist_ok=True)
        result = image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST)
        if size:
            result = result.crop((0, 0, *size))
        result.save(target, optimize=True)
        record = {"path": path, "width": result.width, "height": result.height, "priority": priority, "opaque": opaque,
                  "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        if anchor:
            record["anchor"] = anchor
        assets.append(record)
        return path

    def cycle(name, frames, milliseconds=125):
        animations[name] = {"frames": frames, "frame_ms": milliseconds, "loop": True}

    save("env/san_xuong.png", deck(), "P0")
    water_frames = [save("env/nuoc_tile" + ("" if index == 0 else f"_{index + 1}") + ".png", water(index), "P0" if index == 0 else "P2", True) for index in range(3)]
    cycle("water", water_frames, 200)
    for direction in ("front", "back", "side", "left"):
        idle = save(f"char/ut_sen_{direction}.png", person(direction), "P0" if direction != "left" else "P1", anchor=[48, 124])
        walk = [save(f"char/ut_sen_walk_{direction}_{phase + 1}.png", person(direction, phase), "P1", anchor=[48, 124]) for phase in range(2)]
        carry_name = "char/ut_sen_cam_do" + ("" if direction == "front" else "_" + direction) + ".png"
        carry_idle = save(carry_name, person(direction, carrying=True), "P1", anchor=[48, 124])
        carry_walk = [save(f"char/ut_sen_cam_do_walk_{direction}_{phase + 1}.png", person(direction, phase, True), "P1", anchor=[48, 124]) for phase in range(2)]
        cycle(f"ut_sen.idle.{direction}", [idle])
        cycle(f"ut_sen.walk.{direction}", walk)
        cycle(f"ut_sen.carry_idle.{direction}", [carry_idle])
        cycle(f"ut_sen.carry_walk.{direction}", carry_walk)
    save("station/bep_idle.png", stove(), "P0")
    for state, count in (("cooking", 3), ("ready", 2)):
        frames = [save(f"station/bep_{state}" + ("" if index == 0 else f"_{index + 1}") + ".png", stove(state, index), "P0" if index == 0 else "P1") for index in range(count)]
        cycle(f"stove.{state}", frames, 150)
    save("station/ban.png", table(), "P0")
    for kind in range(4):
        for mood in ("cho", "vui", "gian", "an"):
            path = f"customer/khach_{kind + 1}" + ("" if mood == "cho" else "_" + mood) + ".png"
            first = save(path, customer(kind, mood), "P0" if kind < 2 and mood == "cho" else "P1", anchor=[48, 128])
            if mood == "an":
                second = save(f"customer/khach_{kind + 1}_an_2.png", customer(kind, mood, 1), "P1", anchor=[48, 128])
                cycle(f"customer.{kind + 1}.eat", [first, second], 220)
    for name in ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung"):
        save(f"item/{name}.png", ingredient(name), "P0")
    for name in ("ca_loc_nuong_trui", "goi_bong_sung", "lau_ca_linh_dien_dien"):
        save(f"dish/{name}.png", dish(name), "P0")
    for name in ("bong_bong_dat_mon", "emote_vui", "emote_doi", "emote_gian", "dong_xu", "sao_uy_tin", "sao_uy_tin_rong", "dong_ho", "phim_e", "khung_hud"):
        save(f"ui/{name}.png", ui(name), "P1")
    cycle("lantern", [save("env/den_long" + ("" if phase == 0 else "_2") + ".png", lantern(phase), "P1") for phase in range(2)], 350)
    for name in ("trang_tri_1", "trang_tri_2", "xuong_khach"):
        save(f"env/{name}.png", prop(name), "P2" if name == "xuong_khach" else "P1")
    for name in ("khoi", "lua", "nuoc_bat"):
        frames = [save(f"fx/{name}" + ("" if phase == 0 else f"_{phase + 1}") + ".png", effect(name, phase), "P2") for phase in range(3)]
        cycle("fx." + name, frames, 140)
    # 450 is not divisible by four: the last native row is cropped to two pixels.
    save("ui/man_ket_thuc.png", end_card(), "P2", True, size=(800, 450))
    manifest = {"scale": 4, "style": "small_flat_pixel_canvas_mock", "assets": sorted(assets, key=lambda asset: (asset["priority"], asset["path"])),
                "animations": animations, "hud_slice": [16, 20, 16, 20]}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seen = set()
    for asset in manifest["assets"]:
        path = ASSETS / asset["path"]
        assert asset["path"] not in seen, f"Duplicate: {path}"
        seen.add(asset["path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"], f"Changed: {path}"
        with Image.open(path) as image:
            assert image.size == (asset["width"], asset["height"]), f"Size: {path}"
            assert image.mode == "RGBA", f"Mode: {path}"
            alpha = image.getchannel("A")
            assert alpha.getextrema() == ((255, 255) if asset["opaque"] else (0, 255)), f"Alpha: {path}"
            if not asset["opaque"]:
                assert image.getpixel((0, 0))[3] == 0, f"Opaque corner: {path}"
            height = image.height // 4 * 4
            core = image.crop((0, 0, image.width, height))
            rebuilt = core.resize((image.width // 4, height // 4), Image.Resampling.NEAREST).resize(core.size, Image.Resampling.NEAREST)
            assert core.tobytes() == rebuilt.tobytes(), f"Pixel grid: {path}"
            if asset["path"].startswith("env/nuoc_tile"):
                assert image.crop((0, 0, 1, image.height)).tobytes() == image.crop((image.width - 1, 0, image.width, image.height)).tobytes(), f"Water left/right seam: {path}"
                assert image.crop((0, 0, image.width, 1)).tobytes() == image.crop((0, image.height - 1, image.width, image.height)).tobytes(), f"Water top/bottom seam: {path}"
    assert {p.relative_to(ASSETS).as_posix() for p in ASSETS.rglob("*.png")} == seen, "Manifest coverage"
    for name, animation in manifest["animations"].items():
        assert all(frame in seen for frame in animation["frames"]), f"Missing animation frame: {name}"
        assert animation["frame_ms"] > 0, f"Invalid frame duration: {name}"
        if len(animation["frames"]) > 1:
            assert len({hashlib.sha256((ASSETS / frame).read_bytes()).hexdigest() for frame in animation["frames"]}) > 1, f"Static animation: {name}"
    for direction in ("front", "back", "side", "left"):
        for action in ("idle", "walk", "carry_idle", "carry_walk"):
            assert f"ut_sen.{action}.{direction}" in manifest["animations"], f"Missing {action}/{direction}"
    print(f"PASS: {len(seen)} PNGs; {len(manifest['animations'])} animation groups; sizes, alpha, 4x4 grid, hashes, references and water seams")
    return manifest


def preview(manifest):
    assets = manifest["assets"]
    columns, cell_w, cell_h = 6, 208, 176
    sheet = Image.new("RGB", (columns * cell_w, 44 + ((len(assets) + columns - 1) // columns) * cell_h), "#102f37")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 16), f"QUAN | {len(assets)} separate PNGs | small flat pixels | complete movement", fill="#ffdc91")
    for index, asset in enumerate(assets):
        x, y = (index % columns) * cell_w, 44 + (index // columns) * cell_h
        draw.rectangle((x + 4, y + 4, x + cell_w - 4, y + cell_h - 4), fill="#1a4248")
        with Image.open(ASSETS / asset["path"]) as image:
            thumb = ImageOps.contain(image, (192, 128), Image.Resampling.NEAREST)
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 8 + (128 - thumb.height) // 2), thumb)
        draw.text((x + 9, y + 139), asset["path"], fill="#ffe4b5")
        draw.text((x + 9, y + 154), f"{asset['priority']} | {asset['width']} x {asset['height']}", fill="#8fc4ba")
    PROOF.mkdir(parents=True, exist_ok=True)
    sheet.save(PROOF / "quan-assets-preview.png")
    frames = []
    for phase in range(6):
        frame = Image.new("RGB", (640, 560), "#102f37")
        draw = ImageDraw.Draw(frame)
        draw.text((16, 12), "UT SEN: WALK / CARRY WALK | fixed canvas and foot anchor", fill="#ffdc91")
        for row, action in enumerate(("walk", "carry_walk")):
            for col, direction in enumerate(("front", "back", "side", "left")):
                paths = manifest["animations"][f"ut_sen.{action}.{direction}"]["frames"]
                with Image.open(ASSETS / paths[phase % len(paths)]) as sprite:
                    frame.paste(sprite, (col * 160 + 32, row * 166 + 36), sprite)
                draw.text((col * 160 + 26, row * 166 + 170), action + " " + direction, fill="#ffe4b5")
        for col, name in enumerate(("stove.cooking", "stove.ready", "fx.lua", "fx.khoi")):
            paths = manifest["animations"][name]["frames"]
            with Image.open(ASSETS / paths[phase % len(paths)]) as sprite:
                frame.paste(sprite, (col * 160 + (160 - sprite.width) // 2, 378), sprite)
            draw.text((col * 160 + 22, 520), name, fill="#ffe4b5")
        frames.append(frame)
    frames[0].save(PROOF / "quan-motion-preview.gif", save_all=True, append_images=frames[1:], duration=160, loop=0, disposal=2)
    frames[0].save(PROOF / "quan-motion-preview.png")
    print("Previews: docs/proof/quan-assets-preview.png and quan-motion-preview.gif")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check", "preview"))
    args = parser.parse_args()
    if args.command == "build":
        build()
    manifest = check()
    if args.command in ("build", "preview"):
        preview(manifest)
