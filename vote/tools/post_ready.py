# -*- coding: utf-8 -*-
"""Hotovy diel z GitHub Release (renderovany mimo denneho behu, napr. seria 2) -> YT + IG cez Buffer na hodinu H
a TikTok verzia do vote/tiktok.json pre appku TikTokNahravac.
    python vote/tools/post_ready.py TAG KLUC HODINA      napr. s2-part-01 101 10
Release TAG musi mat <meno>.mp4 + <meno>.txt (verzia s hlasovanim) a <meno>-tt.mp4 + <meno>-tt.txt (TikTok).
KLUC = cislo epizody v tiktok.json; appka berie len cisla a hotovo si pamata podla cisla -> seria 2 = 101, 102..."""
import datetime as dt
import json
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from common import REPO, VOTE  # noqa: E402
from run import VOTE_SERVICES, buffer_push  # noqa: E402

tag, key, hour = sys.argv[1], sys.argv[2], int(sys.argv[3])
od = REPO / "output"
od.mkdir(exist_ok=True)
if subprocess.run(["gh", "release", "download", tag, "--dir", str(od), "--clobber", "--pattern", "*.mp4",
                   "--pattern", "*.txt"], cwd=REPO).returncode:
    sys.exit("stiahnutie release zlyhalo")
vote_f = next(f.name for f in od.glob("*.mp4") if not f.stem.endswith("-tt"))
tt_f = vote_f[:-4] + "-tt.mp4"
if not (od / tt_f).exists():
    sys.exit(f"chyba {tt_f} v release {tag}")

sys.argv = ["post_ready.py", "--hour", str(hour)]   # buffer_push cita --hour (Europe/Bratislava)
done, due = buffer_push({vote_f: VOTE_SERVICES})
print("Buffer:", sorted(done), "na", due)
if not VOTE_SERVICES <= done:
    sys.exit("Buffer nenaplanoval vsetky siete")

title, text = (od / (tt_f[:-4] + ".txt")).read_text(encoding="utf-8").split("\n", 1)
tt_due = dt.datetime.now(ZoneInfo("Europe/Bratislava")).replace(hour=hour, minute=0, second=0, microsecond=0)
if tt_due < dt.datetime.now(ZoneInfo("Europe/Bratislava")):
    tt_due += dt.timedelta(days=1)
feed_f = VOTE / "tiktok.json"
feed = json.loads(feed_f.read_text(encoding="utf-8")) if feed_f.exists() else {"episodes": {}}
feed["episodes"][key] = {"id": tag, "title": title.strip(), "text": text.strip(),
                         "video": f"https://github.com/brockai667/WealthFactory/releases/download/{tag}/{tt_f}",
                         "due": tt_due.astimezone(dt.timezone.utc).isoformat(timespec="seconds")}
feed_f.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
print("TikTok feed:", key, feed["episodes"][key]["due"])
