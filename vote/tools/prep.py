#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vote-story (format saveo.house) - priprava dielu pre Remotion.
    python tools/prep.py 2   -> vote/build/part2/ (episode.json, voice.mp3, music.mp3, sfx/, img/, caption.txt)
    python tools/prep.py 2 --novote -> vote/build/part2_novote/ (koniec bez hlasovania: "Part 3 drops tomorrow", pre TikTok)
    python tools/prep.py 1 --file part1_60 -> scenar parts/part1_60.json, vystup vote/build/part1_60/ (obrazky stale z img/part1)
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


def _orpheus(text, out, voice, emo):
    """Groq Orpheus (user 20.10.: edge je monotonny, hlas troy). emo = pokyn v hranatych zatvorkach ([excited],
    [shocked]...), nahlas sa necita. Kluc = MODELS_TOKEN (Groq). Casy slov neda -> estimate()."""
    import requests
    r = requests.post("https://api.groq.com/openai/v1/audio/speech",
                      headers={"Authorization": f"Bearer {os.environ['MODELS_TOKEN']}"},
                      json={"model": "canopylabs/orpheus-v1-english", "voice": voice, "response_format": "wav",
                            "input": (f"[{emo}] " if emo else "") + text}, timeout=90)
    time.sleep(6.5)   # free tier ~10 poziadaviek/min (test 20.10.: 11. hned 429)
    if r.status_code != 200:
        raise RuntimeError(f"orpheus {r.status_code} {r.text[:450]}")   # 429 na konci hovori "try again in ..."
    open(out, "wb").write(r.content)
    return None


def squeeze(x, keep=0.16, longer=0.26):
    """Orpheus hra dlhe dramaticke pauzy (whisper beat 7 s na 9 slov) -> ticho dlhsie ako `longer` skrati na `keep`."""
    w = int(0.02 * SR)
    loud = np.convolve(np.abs(x) > 0.012, np.ones(w), "same") > 0
    out, i = [], 0
    while i < len(x):
        j = i
        while j < len(x) and loud[j] == loud[i]:
            j += 1
        seg = x[i:j]
        if not loud[i] and len(seg) > longer * SR:
            h = int(keep * SR / 2)
            seg = np.concatenate([seg[:h], seg[-h:]])
        out.append(seg); i = j
    return np.concatenate(out) if out else x


def estimate(text, dur):
    """Casy slov podla dlzky slova + pauzy za interpunkciou (Orpheus nema WordBoundary)."""
    toks = text.split()
    wts = [len(re.sub(r"[^\w]", "", t)) + 2 + (4 if t.endswith((".", "?", "!")) else 2 if t.endswith((",", ";", ":")) else 0)
           for t in toks]
    k, t, words = dur / max(1, sum(wts)), 0.0, []
    for tok, wt in zip(toks, wts):
        words.append({"w": tok, "s": round(t, 3), "e": round(t + k * (len(re.sub(r"[^\w]", "", tok)) + 2), 3)})
        t += k * wt
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


def synth(spec, cache, tts):
    """Hlas po beatoch -> (kusy audia, casy slov, dlzka). tts = None -> edge-tts, inak Orpheus s beat["emo"]."""
    parts, words, cur = [], [], 0.0
    for i, b in enumerate(spec["beats"]):
        key = f"orpheus:{tts['voice']}:{b.get('emo', '')}:" if tts else spec["voice"] + spec["rate"]
        h = hashlib.md5((key + b["text"]).encode()).hexdigest()[:16]
        mp3, js = os.path.join(cache, h + ".mp3"), os.path.join(cache, h + ".json")
        if not os.path.exists(js):
            for a in range(4):
                try:
                    if tts:
                        w = _orpheus(b["text"], mp3, tts["voice"], b.get("emo"))
                    else:
                        w = asyncio.run(_edge(b["text"], mp3, spec["voice"], spec["rate"]))
                        if not w:
                            raise RuntimeError("prazdne")
                    if os.path.getsize(mp3) < 2000:
                        raise RuntimeError("prazdne")
                    json.dump(w, open(js, "w", encoding="utf-8")); break
                except Exception as e:
                    print("tts retry", e); time.sleep(4 + 8 * a)
            else:
                raise RuntimeError("TTS zlyhalo")
        w = json.load(open(js, encoding="utf-8"))
        wav = os.path.join(cache, "tmp.wav")
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3] + (["-af", f"atempo={tts.get('tempo', 1.15)}"] if tts else [])
                       + ["-ar", str(SR), "-ac", "1", wav], check=True)
        x, _ = sf.read(wav)
        nz = np.nonzero(np.abs(x) > 0.01)[0]
        if len(nz):
            x = x[max(0, nz[0] - int(0.03 * SR)): nz[-1] + int(0.10 * SR)]
            off = max(0, nz[0] - int(0.03 * SR)) / SR
        else:
            off = 0
        if tts:
            x = squeeze(x)
        if w is None:   # Orpheus: odhad v ramci orezaneho kusu (bez dychu na konci)
            w = [{**ww, "s": ww["s"] + off + 0.03, "e": ww["e"] + off + 0.03}
                 for ww in estimate(b["text"], max(0.3, len(x) / SR - 0.13))]
        b["t0"] = round(cur, 3)
        for ww in punct(w, b["text"]):
            words.append({"w": ww["w"], "s": round(cur + ww["s"] - off, 3), "e": round(cur + min(ww["e"] - off, len(x) / SR), 3), "b": i})
        parts.append(x); cur += len(x) / SR
        gap = b.get("pause", 0.45 if (b.get("shot", "").startswith("card:") or b.get("day") or b["text"].rstrip().endswith(("?", "isn't.", "yet."))) else GAP)
        parts.append(np.zeros(int(gap * SR))); cur += gap
        b["t1"] = round(cur, 3)
    return parts, words, cur


def main():
    n = int(sys.argv[1])
    novote = "--novote" in sys.argv
    b = bible()
    fname = sys.argv[sys.argv.index("--file") + 1] if "--file" in sys.argv else None
    spec = load(part_path(n).with_name(fname + ".json") if fname else part_path(n))
    spec.update({k: b[k] for k in ("series", "tagline", "voice", "rate", "hud_labels")})
    spec["part"] = n
    if novote and spec.get("vote"):   # siet, kde hlasy necitame: rovnaky diel, iny koniec
        nxt = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][n + 1] if n < 10 else str(n + 1)
        spec["beats"][-2].pop("vote", None)
        spec["beats"][-1]["text"] = f"Part {nxt} drops tomorrow. Follow, so you don't miss what happens."
        spec["cards"]["end"]["foot"] = "Follow so you don't miss it.\nFind out what happens tomorrow."
        spec["vote"] = []
        spec["caption"] = "\n".join(l if not re.search(r"Comment|One word", l) else f"Part {n + 1} drops tomorrow. Follow so you don't miss it."
                                     for l in spec["caption"].split("\n"))
    out = os.path.join(ROOT, "build", (fname or f"part{n}") + ("_novote" if novote else ""))
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    shutil.copytree(os.path.join(ROOT, "assets", "sfx"), os.path.join(out, "sfx"))
    shutil.copytree(str(img_dir(n)), os.path.join(out, "img"))
    cache = os.path.join(ROOT, "tts_cache"); os.makedirs(cache, exist_ok=True)
    tts = b.get("tts")   # {"engine": "orpheus", "voice": "troy"}; bez neho edge-tts
    try:
        parts, words, cur = synth(spec, cache, tts)
    except RuntimeError as e:   # Orpheus vypadol (limit) -> cely diel edge, nie mix dvoch hlasov
        if not tts:
            sys.exit(str(e))
        print("Orpheus zlyhal, cely diel ide edge-tts:", e)
        parts, words, cur = synth(spec, cache, None)
    sf.write(os.path.join(cache, "voice.wav"), np.concatenate(parts), SR)
    sf.write(os.path.join(cache, "voice.wav"), np.concatenate(parts), SR)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", os.path.join(cache, "voice.wav"), "-b:a", "160k",
                    os.path.join(out, "voice.mp3")], check=True)
    shutil.copy(MUSIC, os.path.join(out, "music.mp3"))
    tail = 2.6  # koncova karta dobehne
    ep = {k: spec[k] for k in ("series", "tagline", "part", "title", "vote", "hud_labels", "cards", "beats", "bubble", "hook") if k in spec}
    ep.update({"fps": 30, "duration": round(cur + tail, 2), "voice": "voice.mp3", "music": "music.mp3",
               "music_gain": 0.16, "words": words})
    json.dump(ep, open(os.path.join(out, "episode.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cap = spec["caption"] + "\n\n" + MUSIC_CREDIT + "\n"
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(cap)
    print(f"hlas {cur:.1f}s, {len(words)} slov, video {ep['duration']}s")


if __name__ == "__main__":
    main()
