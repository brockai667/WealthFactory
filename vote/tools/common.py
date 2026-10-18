# -*- coding: utf-8 -*-
"""Spolocne veci vote-story fabriky: cesty, stav serie, nacitanie .env (kluce sa nikdy nevypisuju)."""
import json
import os
from pathlib import Path

VOTE = Path(__file__).resolve().parents[1]          # WealthFactory/vote
REPO = VOTE.parent                                   # WealthFactory
STATE = VOTE / "state.json"

for _env in (REPO / ".env", VOTE / ".env", Path.home() / ".config/watch/.env", Path.home() / "FactoryAnim/.env"):
    if _env.exists():
        for _l in _env.read_text(encoding="utf-8").splitlines():
            if "=" in _l and not _l.lstrip().startswith("#"):
                _k, _v = _l.split("=", 1)
                if _v.strip():
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"'))


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def save(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def state():
    if STATE.exists():
        return load(STATE)
    return {"series": "suddenly-rich", "next_part": 1, "parts": {}}


def series_dir(st=None):
    return VOTE / "series" / (st or state())["series"]


def bible(st=None):
    return load(series_dir(st) / "bible.json")


def part_path(n, st=None):
    return series_dir(st) / "parts" / f"part{n}.json"


def img_dir(n, st=None):
    return series_dir(st) / "img" / f"part{n}"
