# -*- coding: utf-8 -*-
"""Denny beh vote-story fabriky (GitHub Actions, bez PC, 0 Claude tokenov):
  1) hlasy pod predoslym dielom (YouTube komentare)  2) Groq napise dalsi diel  3) obrazky Cloudflare FLUX
  4) hlas + Remotion render  5) Buffer (IG/YT/TikTok) na 18:00  6) stav do state.json (commitne workflow)
    python tools/run.py [--force] [--no-post]
--force = nevaha 20 h od predosleho dielu, --no-post = len vyrobi video (test)."""
import datetime as dt
import os
import random
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import REPO, VOTE, bible, load, part_path, save, state, STATE  # noqa: E402
import votes  # noqa: E402

MIN_HOURS = 20       # najskor po tolkych hodinach od zverejnenia predosleho dielu
POST_HOUR = 18       # Europe/Bratislava
VOTE_SERVICES = {"youtube", "instagram"}   # tu sa hlasy citaju (YT API, IG Graph) -> koniec s hlasovanim
NOVOTE_SERVICES = {"tiktok"}               # tu nie -> koniec "Part N+1 drops tomorrow"
PY = sys.executable


def now():
    return dt.datetime.now(dt.timezone.utc)


def hours_since(iso):
    return (now() - dt.datetime.fromisoformat(iso)).total_seconds() / 3600


def sh(*cmd, cwd=VOTE):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode


def main():
    force, no_post = "--force" in sys.argv, "--no-post" in sys.argv
    st, b = state(), bible()
    n = st["next_part"]
    if n > b["parts_max"]:
        print(f"Seria {b['series']} je dokoncena ({b['parts_max']} dielov) - treba novu bibliu serie.")
        return
    if n > 1:
        prev = st["parts"].get(str(n - 1), {})
        h = hours_since(prev["posted_at"]) if prev.get("posted_at") else 999
        if h < MIN_HOURS and not force:
            print(f"Part {n - 1} je vonku len {h:.1f} h - hlasovanie este bezi.")
            return
        if not part_path(n).exists():
            last = load(part_path(n - 1))
            v = votes.votes(b["series"], n - 1, last["vote"])
            if v is None and h < 48 and not force:
                print("Video na YouTube este nie je (Buffer ho mozno publikuje neskor) - skusim zajtra.")
                return
            counts = v["counts"] if v else {o: 0 for o in last["vote"]}
            total = sum(counts.values())
            if total and counts[last["vote"][0]] != counts[last["vote"][1]]:
                winner = max(last["vote"], key=lambda o: counts[o])
            else:   # ziadne / nerozhodne hlasy -> pevna nahoda podla cisla dielu (opakovatelne)
                winner = random.Random(n).choice(last["vote"])
            prev.update({"votes": counts, "winner": winner, "video_id": (v or {}).get("video_id")})
            st["parts"][str(n - 1)] = prev
            save(STATE, st)
            print(f"Hlasy Part {n - 1}: {counts} -> {winner}")
            import json
            if sh(PY, "tools/write_part.py", str(n), winner, "--votes", json.dumps(counts)):
                sys.exit("autor zlyhal")
    rc = sh(PY, "tools/gen_images.py", str(n))
    if rc == 3:
        print("Cloudflare denny limit - obrazky sa dorobia zajtra, diel ide potom.")
        return
    if rc:
        sys.exit("obrazky zlyhali")
    part = load(part_path(n))
    name = f"{b['slug']}-part{n:02d}"
    od = REPO / "output"
    od.mkdir(exist_ok=True)
    title = f"{b['series'].title()} · Part {n}: {part['title'].title()}"
    npx = shutil.which("npx") or "npx"
    files = {}   # subor -> sluzby
    for variant, suffix, services in (("", "", VOTE_SERVICES), ("--novote", "-tt", NOVOTE_SERVICES)):
        if not part.get("vote") and variant:
            continue   # finale nema hlasovanie -> jedna verzia pre vsetkych
        args = [PY, "tools/prep.py", str(n)] + ([variant] if variant else [])
        if sh(*args):
            sys.exit("prep zlyhal")
        bdir = f"part{n}" + ("_novote" if variant else "")
        mp4 = VOTE / "build" / f"{bdir}.mp4"
        if sh(npx, "remotion", "render", "src/index.ts", "Episode", str(mp4), f"--public-dir=build/{bdir}",
              "--crf=22", "--concurrency=100%"):
            sys.exit("render zlyhal")
        shutil.copy(mp4, od / f"{name}{suffix}.mp4")
        caption = (VOTE / "build" / bdir / "caption.txt").read_text(encoding="utf-8")
        (od / f"{name}{suffix}.txt").write_text(title + "\n" + caption, encoding="utf-8")
        files[f"{name}{suffix}.mp4"] = services if part.get("vote") else VOTE_SERVICES | NOVOTE_SERVICES
        print("video:", od / f"{name}{suffix}.mp4", round((od / f"{name}{suffix}.mp4").stat().st_size / 1e6, 1), "MB")
    if no_post:
        print("--no-post: nezverejnujem")
        return
    sys.path.insert(0, str(REPO))
    os.chdir(REPO)
    if not (REPO / "config.json").exists():
        shutil.copy(REPO / "config.example.json", REPO / "config.json")
    import push_to_buffer as pb
    pb.SLOT_HOURS = [POST_HOUR]
    base_cfg = pb.load_cfg
    done = set()
    for f, services in files.items():   # kazdy subor len na svoje siete
        pb.load_cfg = lambda s=services: {**base_cfg(), "buffer_channels": [c for c in base_cfg()["buffer_channels"]
                                                                             if c["service"].lower() in s]}
        keep = {x: [] for x in os.listdir(REPO / "output") if x.endswith(".mp4") and x != f}
        for x in keep:   # push_to_buffer berie vsetky mp4 v output/ -> ostatne docasne odlozit
            os.replace(REPO / "output" / x, REPO / "output" / (x + ".hold"))
        sys.argv = ["push_to_buffer.py", "1"]
        try:
            pb.main()
        finally:
            for x in keep:
                os.replace(REPO / "output" / (x + ".hold"), REPO / "output" / x)
        done |= set(pb.load_pushed().get(f, []))
    if not done:
        sys.exit("Buffer: nic sa neposlalo - skusi sa znova pri dalsom behu")
    st["parts"][str(n)] = {"title": part["title"], "vote": part["vote"], "posted_at": now().isoformat(timespec="seconds"),
                           "services": sorted(done)}
    st["next_part"] = n + 1
    save(STATE, st)
    print(f"HOTOVO: Part {n} naplanovany ({', '.join(sorted(done))}).")


if __name__ == "__main__":
    main()
