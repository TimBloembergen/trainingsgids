#!/usr/bin/env python3
"""Draw the app icon: an orange dumbbell on the dark top-bar colour.

    python3 tools/icon.py   # writes apple-touch-icon.png, icon-192.png, icon-512.png

Needs Pillow (pip install pillow). The PNGs are committed, so this only
runs when the icon changes. The icon is full-bleed and square: iOS and
Android round the corners themselves. The dumbbell stays inside the
middle 70 % so Android's round "maskable" crop keeps all of it.
"""
import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
S = 2048  # drawn large, scaled down for smooth edges

TOP, BOTTOM = (43, 43, 48), (17, 17, 19)        # dark gradient, like the top bar
ORANGE, ORANGE_DARK = (249, 115, 22), (194, 65, 12)
STEEL = (228, 228, 231)


def background():
    img = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / (S - 1)
        d.line([(0, y), (S, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)))
    return img


def dumbbell():
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = S / 2
    u = S / 1024  # design units on a 1024 grid

    def box(x0, y0, x1, y1, r, fill):
        d.rounded_rectangle([c + x0 * u, c + y0 * u, c + x1 * u, c + y1 * u], radius=r * u, fill=fill)

    box(-250, -34, 250, 34, 30, STEEL)                  # handle
    for sx in (-1, 1):
        # inner (big) and outer (small) plates, with a darker edge for depth
        x0, x1 = sorted((sx * 150, sx * 245))
        box(x0, -200, x1, 200, 34, ORANGE_DARK)
        box(x0 + 10, -190, x1 - 10, 190, 28, ORANGE)
        x0, x1 = sorted((sx * 255, sx * 320))
        box(x0, -140, x1, 140, 28, ORANGE_DARK)
        box(x0 + 9, -131, x1 - 9, 131, 22, ORANGE)
        x0, x1 = sorted((sx * 320, sx * 350))
        box(x0, -34, x1, 34, 14, STEEL)                 # end cap
    return layer.rotate(35, resample=Image.BICUBIC, center=(S / 2, S / 2))


def main():
    img = background().convert("RGBA")
    img.alpha_composite(dumbbell())
    # an orange line along the bottom, like the top bar's border
    ImageDraw.Draw(img).rectangle([0, S * 0.955, S, S], fill=ORANGE)
    img = img.convert("RGB")
    for name, size in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
        img.resize((size, size), Image.LANCZOS).save(ROOT / name, optimize=True)
        print(name)


if __name__ == "__main__":
    main()
