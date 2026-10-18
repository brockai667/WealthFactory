# -*- coding: utf-8 -*-
"""Obrazky dielu cez Cloudflare FLUX.2 klein 9B s referenciou postavy (biblia serie = styl, postava, miesta).
    python tools/gen_images.py 2 [img03 img07] [--force]
Hotove obrazky preskoci. Ked minu vsetky ucty denny limit, skonci s kodom 3 (dorobi sa zajtra)."""
import os
import sys

os.environ.setdefault("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-9b")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_image  # noqa: E402
from common import bible, img_dir, load, part_path, series_dir  # noqa: E402


def prompt_for(b, s, has_ref):
    im = b["image"]
    loc = im["locations"].get(s["location"], s["location"])
    who = im["hands_only"] if s.get("hands_only") else ("" if s.get("no_character") else im["character"])
    style = im["style"] if has_ref else im["style"].replace(", exactly the art style of image 1", "")
    return " ".join(x for x in [s["camera"], "SCENE: " + s["scene"], who, loc, style, im["negative"]] if x)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    n = int(args[0])
    b, part = bible(), load(part_path(n))
    out = img_dir(n)
    out.mkdir(parents=True, exist_ok=True)
    ref = str(series_dir() / b["image"]["ref"])
    w, h = b["image"]["size"]
    ids = args[1:] or list(part["shots"])
    made = 0
    for k in ids:
        dst = out / f"{k}.jpg"
        if dst.exists() and not force:
            continue
        s = part["shots"][k]
        refs = [ref] if "char" in s.get("refs", []) and not s.get("hands_only") else []
        seed = 100 * n + int("".join(c for c in k if c.isdigit()) or 0) + (7 if force else 0)
        try:
            cf_image.generate(prompt_for(b, s, bool(refs)), str(dst), refs, width=w, height=h, seed=seed)
        except cf_image.LimitReached as e:
            print("LIMIT:", e)
            sys.exit(3)
        made += 1
        print("obr", k)
    print(f"hotovo: {made} novych, spolu {len(list(out.glob('*.jpg')))}/{len(part['shots'])}")


if __name__ == "__main__":
    main()
