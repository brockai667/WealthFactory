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

MIN_HOURS = 6        # ochrana pred dvojitym behom (posted_at je buduci cas -> zaporne h); 6 h, aby diel o 20:00 nezablokoval nocny cron o 03:15
POST_HOUR = 10       # Europe/Bratislava (user 19.10.: YT + IG rano o 10:00)
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


def release(n, title, od, mp4s):
    """Video + popisok do GitHub Release part-NN (repo je verejne -> stiahnutie z mobilu bez prihlasenia)."""
    tag = f"part-{n:02d}"
    txts = [m[:-4] + ".txt" for m in mp4s]
    caption = "\n\n".join((od / t).read_text(encoding="utf-8").split("\n", 1)[1].strip() for t in txts)
    notes = od / "release-notes.md"
    notes.write_text("Popisok (skopiruj cely blok):\n\n```\n" + caption + "\n```\n\n"
                     "Obal: subor `-cover.jpg` (TikTok > Vybrat obal > z galerie).\n", encoding="utf-8")
    cover = od / (mp4s[0][:-4] + "-cover.jpg")
    try:
        from cover import make_cover
        make_cover(n, cover)
    except Exception as e:   # obal nie je kriticky - diel ide aj bez neho
        print("obal zlyhal:", e)
    assets = [str(od / f) for f in mp4s + txts] + ([str(cover)] if cover.exists() else [])
    if sh("gh", "release", "view", tag, cwd=REPO) == 0:   # opakovany beh -> prepisat subory a text
        rc = sh("gh", "release", "upload", tag, *assets, "--clobber", cwd=REPO) or \
            sh("gh", "release", "edit", tag, "--title", title, "--notes-file", str(notes), cwd=REPO)
    else:
        rc = sh("gh", "release", "create", tag, *assets, "--title", title, "--notes-file", str(notes), cwd=REPO)
    if rc:
        sys.exit("GitHub Release zlyhal")


def buffer_push(files, asap=False, first_comment=""):
    """files = {mp4 v output/: sluzby}. Kazdy subor len na svoje siete cez push_to_buffer. asap = najblizsia cela hodina
    (dobeh), inak POST_HOUR. Vrati (poslane sluzby, planovany cas ISO UTC)."""
    sys.path.insert(0, str(REPO))
    os.chdir(REPO)
    if not (REPO / "config.json").exists():
        shutil.copy(REPO / "config.example.json", REPO / "config.json")
    import push_to_buffer as pb
    pb.FIRST_COMMENT = first_comment
    if asap:
        from zoneinfo import ZoneInfo
        pb.SLOT_HOURS = [(dt.datetime.now(ZoneInfo("Europe/Bratislava")).hour + 1) % 24]
    else:   # --hour H = rucny beh na konkretnu hodinu (user 24.10.: Part 2 este dnes vecer)
        pb.SLOT_HOURS = [int(sys.argv[sys.argv.index("--hour") + 1]) if "--hour" in sys.argv else POST_HOUR]
    due = pb.next_slots(1)[0]
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
    return done, due


def main():
    force, no_post = "--force" in sys.argv, "--no-post" in sys.argv
    manual = "--manual" in sys.argv   # len TikTok verzia -> GitHub Release, Damian nahra z mobilu (bez Buffra a hlasov)
    hybrid = "--hybrid" in sys.argv   # od 19.10. default: YT + IG cez Buffer o 10:00, TikTok verzia do Releases (Damian nahra z mobilu)
    repost = int(sys.argv[sys.argv.index("--repost") + 1]) if "--repost" in sys.argv else None   # dohnat hotovy diel N na YT + IG hned
    st, b = state(), bible()
    if st.get("hold") and not repost:   # user 20.10.: "vyjde az ked to bude hotove" -> cron caka na schvalenie
        print("Pozastavene:", st["hold"])
        return
    n = repost or st["next_part"]
    if n > b["parts_max"]:
        print(f"Seria {b['series']} je dokoncena ({b['parts_max']} dielov) - treba novu bibliu serie.")
        return
    if repost and not part_path(n).exists():
        sys.exit(f"--repost {n}: diel este nie je napisany")
    if n > 1 and not repost:
        prev = st["parts"].get(str(n - 1), {})
        h = hours_since(prev["posted_at"]) if prev.get("posted_at") else 999
        if h < MIN_HOURS and not force:
            print(f"Part {n - 1} je vonku len {h:.1f} h - hlasovanie este bezi.")
            return
        if not part_path(n).exists():
            last = load(part_path(n - 1))
            v = None if manual else votes.votes(b["series"], n - 1, last["vote"])
            if v is None and h < 48 and not force and not manual:
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
            if b.get("author") == "claude":   # user 24.10.: "nech sa vzdy vyda video" -> bez Claude dielu pise Groq, seria nestoji
                print(f"Part {n} od Clauda chyba (vitaz {winner}) - zalozne ho pise Groq.")
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
    variants = [("", "", VOTE_SERVICES), ("--novote", "-tt", NOVOTE_SERVICES)]
    if not part.get("vote"):
        variants = variants[:1]   # finale nema hlasovanie -> jedna verzia pre vsetkych
    elif manual:
        variants = variants[1:]   # len TikTok verzia
    elif repost:
        variants = variants[:1]   # dobeh na YT + IG = len verzia s hlasovanim
    for variant, suffix, services in variants:
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
    if hybrid or repost:   # YT + IG automaticky cez Buffer o POST_HOUR, TikTok verzia do Releases na rucne nahratie
        vote_f = f"{name}.mp4"
        tt_f = f"{name}-tt.mp4" if f"{name}-tt.mp4" in files else vote_f   # finale = jedna verzia pre vsetkych
        if not repost:
            release(n, title, od, [tt_f])
        fc = ""   # IG prvy komentar: Buffer free plan ho odmieta ("First comment requires a paid plan", 20.10.)
        done, due = buffer_push({vote_f: VOTE_SERVICES}, asap=bool(repost) or "--asap" in sys.argv, first_comment=fc)
        if not done:
            sys.exit("Buffer: nic sa neposlalo - skusi sa znova pri dalsom behu" +
                     ("" if repost else " (TikTok verzia uz je v Releases)"))
        prev = st["parts"].get(str(n), {})
        services = sorted(set(prev.get("services", [])) | done | ({"tiktok-manual"} if not repost else set()))
        st["parts"][str(n)] = {**prev, "title": part["title"], "vote": part["vote"], "posted_at": due, "services": services}
        if not repost:
            st["next_part"] = n + 1
        save(STATE, st)
        print(f"HOTOVO: Part {n} -> {', '.join(sorted(done))} na {due}" + ("" if repost else f" + TikTok v Releases (part-{n:02d})"))
        return
    if manual:
        release(n, title, od, list(files))
        st["parts"][str(n)] = {"title": part["title"], "vote": part["vote"],
                               "posted_at": now().isoformat(timespec="seconds"), "services": ["tiktok-manual"]}
        st["next_part"] = n + 1
        save(STATE, st)
        print(f"HOTOVO: Part {n} v GitHub Releases (part-{n:02d}) na rucne nahratie.")
        return
    done, _ = buffer_push(files)
    if not done:
        sys.exit("Buffer: nic sa neposlalo - skusi sa znova pri dalsom behu")
    st["parts"][str(n)] = {"title": part["title"], "vote": part["vote"], "posted_at": now().isoformat(timespec="seconds"),
                           "services": sorted(done)}
    st["next_part"] = n + 1
    save(STATE, st)
    print(f"HOTOVO: Part {n} naplanovany ({', '.join(sorted(done))}).")


if __name__ == "__main__":
    main()
