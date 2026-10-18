# -*- coding: utf-8 -*-
"""Obal (thumbnail) dielu pre TikTok: prvy zaber dielu + velke PART N + nazov dielu, 1080x1920.
Text je v strede (TikTok mriezka profilu oreze 9:16 na 3:4).
    python tools/cover.py N [vystup.jpg]"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import bible, img_dir, load, part_path  # noqa: E402

W, H = 1080, 1920
GOLD, CREAM = (244, 180, 26), (242, 234, 219)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]


def font(size):
    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


def fit(draw, text, size, maxw):
    while size > 40 and draw.textlength(text, font=font(size)) > maxw:
        size -= 6
    return font(size)


def centered(draw, y, text, fnt, fill):
    x = (W - draw.textlength(text, font=fnt)) / 2
    draw.text((x, y), text, font=fnt, fill=fill, stroke_width=max(4, fnt.size // 18), stroke_fill=(0, 0, 0))
    return y + fnt.size * 1.15


def make_cover(n, out):
    part, b = load(part_path(n)), bible()
    shot = next(x["shot"] for x in part["beats"] if not x["shot"].startswith("card:"))
    bg = Image.open(img_dir(n) / f"{shot}.jpg").convert("RGB")
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    shade = Image.new("L", (W, H), 0)   # tmavy pas za textom, aby bol citatelny na kazdom obrazku
    ImageDraw.Draw(shade).rectangle((0, 460, W, 1080), fill=150)
    bg = Image.composite(Image.new("RGB", (W, H)), bg, shade.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(bg)
    y = centered(d, 500, b["series"].upper(), fit(d, b["series"].upper(), 64, W - 160), CREAM)
    y = centered(d, y + 10, f"PART {n}", font(230), GOLD)
    centered(d, y + 10, part["title"].upper(), fit(d, part["title"].upper(), 110, W - 120), CREAM)
    bg.save(out, quality=92)
    return out


if __name__ == "__main__":
    k = int(sys.argv[1])
    print(make_cover(k, sys.argv[2] if len(sys.argv) > 2 else f"cover-part{k:02d}.jpg"))
