# -*- coding: utf-8 -*-
"""Seria 2 bez PC: kazde rano spocita hlasy predosleho dielu a pusti vitaznu verziu dalsieho dielu.
    python vote/tools/s2_daily.py            (spusta workflow s2-daily.yml)
Plan je vo vote/s2_plan.json: {"series": "SUDDENLY RICH", "items": [{"date": "2026-11-06", "vote_part": 1,
  "options": ["TELL", "HIDE"], "tags": {"TELL": "s2-part-02-tell", "HIDE": "s2-part-02-hide"}, "key": "102", "hour": 10}]}
Polozka s dnesnym datumom (Europe/Bratislava) a bez "done" sa vykona: hlasy z YouTube + Instagramu (votes.py), vitaz
(pri remize prva moznost) -> post_ready.py TAG KLUC HODINA. Vysledok sa zapise do polozky ("done", "winner", "counts")."""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import VOTE  # noqa: E402
import votes  # noqa: E402

plan_f = VOTE / "s2_plan.json"
plan = json.loads(plan_f.read_text(encoding="utf-8"))
today = dt.datetime.now(ZoneInfo("Europe/Bratislava")).date().isoformat()
todo = [it for it in plan["items"] if it["date"] == today and not it.get("done")]
if not todo:
    print("s2: dnes nic", today)
    sys.exit(0)
for it in todo:
    opts = it["options"]
    v = votes.votes(plan["series"], it["vote_part"], opts) or {"counts": {o: 0 for o in opts}, "total": 0}
    counts = v["counts"]
    winner = max(opts, key=lambda o: (counts[o], -opts.index(o)))   # remiza -> prva moznost
    print(f"s2: Part {it['vote_part']} hlasy {counts} -> {winner}")
    rc = subprocess.run([sys.executable, "-u", str(Path(__file__).with_name("post_ready.py")), it["tags"][winner],
                         str(it["key"]), str(it["hour"])]).returncode
    it.update({"winner": winner, "counts": counts})
    if rc == 0:
        it["done"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    plan_f.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    if rc:
        sys.exit(f"s2: post_ready zlyhal ({rc})")
