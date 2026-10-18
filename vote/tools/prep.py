#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vote-story (format saveo.house) - priprava dielu pre Remotion.
    python tools/prep.py 2   -> vote/build/part2/ (episode.json, voice.mp3, music.mp3, sfx/, img/, caption.txt)
    python tools/prep.py 2 --novote -> vote/build/part2_novote/ (koniec bez hlasovania: "Part 3 drops tomorrow", pre TikTok)
Hlas = edge-tts, jeden mp3 na beat, WordBoundary = casy slov. Hudba = Kevin MacLeod (CC BY)."""
import asyncio, hashlib, json, os, re, shutil, subprocess, sys, time
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import bible, img_dir, load, part_path  # noqa: E402
FF = shutil.which("ffmpeg") or "ffmpeg"
SR = 24000
GAP = 0.2
MUSIC = os.path.join(ROOT, "assets", "music", "Crypto.mp3")
MUSIC_CREDIT = 'Music: "Crypto" - Kevin MacLeod (incompetech.com) · Licensed under CC BY 4.0'


async def _edge(text, out, voice, rate):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"w": ch["text"], "s": ch["offset"] / 1e7, "e": (ch["offset"] + ch["duration"]) / 1e7})
    return words


def punct(words, text):
    toks = text.split()
    norm = lambda s: re.sub(r"[^\w']", "", s).lower()
    j = 0
    for w in words:
        nw = norm(w["w"])
        for k in range(j, min(j + 3, len(toks))):
            nt = norm(toks[k])
            if nt == nw or (nw and nt.startswith(nw)):
                w["w"] = toks[k]; j = k + 1; break
    return words


def main():
    n = int(sys.argv[1])
    novote = "--novote" in sys.argv
    b = bible()
    spec = load(part_path(n))
    spec.update({k: b[k] for k in ("series", "tagline", "voice", "rate", "hud_labels")})
    spec["part"] = n
    if novote and spec.get("vote"):   # siet, kde hlasy necitame: rovnaky diel, iny koniec
        nxt = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][n + 1] if n < 10 else str(n + 1)
        spec["beats"][-2].pop("vote", None)
        spec["beats"][-1]["text"] = f"Part {nxt} drops tomorrow. Follow, so you don't miss what happens."
        spec["cards"]["end"]["foot"] = "Follow so you don't miss it.\nFind out what happens tomorrow."
        spec["vote"] = []
        spec["caption"] = "\n".join(l if "Comment" not in l else f"Part {n + 1} drops tomorrow. Follow so you don't miss it."
                                     for l in spec["caption"].split("\n"))
    out = os.path.join(ROOT, "build", f"part{n}" + ("_novote" if novote else ""))
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    shutil.copytree(os.path.join(ROOT, "assets", "sfx"), os.path.join(out, "sfx"))
    shutil.copytree(str(img_dir(n)), os.path.join(out, "img"))
    cache = os.path.join(ROOT, "tts_cache"); os.makedirs(cache, exist_ok=True)
    parts, words, cur = [], [], 0.0
    for i, b in enumerate(spec["beats"]):
        h = hashlib.md5((spec["voice"] + spec["rate"] + b["text"]).encode()).hexdigest()[:16]
        mp3, js = os.path.join(cache, h + ".mp3"), os.path.join(cache, h + ".json")
        if not os.path.exists(js):
            for a in range(4):
                try:
                    w = asyncio.run(_edge(b["text"], mp3, spec["voice"], spec["rate"]))
                    if not w or os.path.getsize(mp3) < 2000:
                        raise RuntimeError("prazdne")
                    json.dump(w, open(js, "w", encoding="utf-8")); break
                except Exception as e:
                    print("tts retry", e); time.sleep(4 + 4 * a)
            else:
                sys.exit("TTS zlyhalo")
        w = json.load(open(js, encoding="utf-8"))
        wav = os.path.join(cache, "tmp.wav")
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", wav], check=True)
        x, _ = sf.read(wav)
        nz = np.nonzero(np.abs(x) > 0.01)[0]
        if len(nz):
            x = x[max(0, nz[0] - int(0.03 * SR)): nz[-1] + int(0.10 * SR)]
            off = max(0, nz[0] - int(0.03 * SR)) / SR
        else:
            off = 0
        b["t0"] = round(cur, 3)
        for ww in punct(w, b["text"]):
            words.append({"w": ww["w"], "s": round(cur + ww["s"] - off, 3), "e": round(cur + min(ww["e"] - off, len(x) / SR), 3), "b": i})
        parts.append(x); cur += len(x) / SR
        gap = b.get("pause", 0.45 if (b.get("shot", "").startswith("card:") or b.get("day") or b["text"].rstrip().endswith(("?", "isn't.", "yet."))) else GAP)
        parts.append(np.zeros(int(gap * SR))); cur += gap
        b["t1"] = round(cur, 3)
    sf.write(os.path.join(cache, "voice.wav"), np.concatenate(parts), SR)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", os.path.join(cache, "voice.wav"), "-b:a", "160k",
                    os.path.join(out, "voice.mp3")], check=True)
    shutil.copy(MUSIC, os.path.join(out, "music.mp3"))
    tail = 2.6  # koncova karta dobehne
    ep = {k: spec[k] for k in ("series", "tagline", "part", "title", "vote", "hud_labels", "cards", "beats", "bubble") if k in spec}
    ep.update({"fps": 30, "duration": round(cur + tail, 2), "voice": "voice.mp3", "music": "music.mp3",
               "music_gain": 0.16, "words": words})
    json.dump(ep, open(os.path.join(out, "episode.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cap = spec["caption"] + "\n\n" + MUSIC_CREDIT + "\n"
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(cap)
    print(f"hlas {cur:.1f}s, {len(words)} slov, video {ep['duration']}s")


if __name__ == "__main__":
    main()
