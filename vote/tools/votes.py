# -*- coding: utf-8 -*-
"""Hlasy z komentarov YouTube (YT Data API, staci API kluc YT_API_KEY - verejne komentare).
    python tools/votes.py 1 CLAIM WAIT
Najde video dielu na kanali (uploads playlist, nazov obsahuje 'Part N'), precita komentare, 1 hlas na autora
(posledny komentar s prave jednou z moznosti). Vrati {"video_id", "counts", "total"} alebo None (video zatial nie je)."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402,F401  (nacita .env)

YT_CHANNEL = os.environ.get("YT_CHANNEL_ID", "UCoFCurtPMDdJTDUsea9iCMQ")  # WealthMindset
API = "https://www.googleapis.com/youtube/v3/"


def _get(path, **q):
    q["key"] = os.environ["YT_API_KEY"]
    with urllib.request.urlopen(API + path + "?" + urllib.parse.urlencode(q), timeout=30) as r:
        return json.loads(r.read())


def find_video(series, n):
    pat = re.compile(rf"part\s*{n}\b", re.I)
    key = series.split()[0].lower()
    items = _get("playlistItems", part="snippet", playlistId="UU" + YT_CHANNEL[2:], maxResults=50).get("items", [])
    for it in items:
        t = it["snippet"]["title"]
        if pat.search(t) and key in t.lower():
            return it["snippet"]["resourceId"]["videoId"]
    return None


def count(video_id, options):
    words = {o: re.compile(rf"\b{re.escape(o)}\b", re.I) for o in options}
    last = {}   # autor -> (cas, volba)
    token, pages = None, 0
    while pages < 20:
        q = dict(part="snippet", videoId=video_id, maxResults=100, textFormat="plainText", order="time")
        if token:
            q["pageToken"] = token
        d = _get("commentThreads", **q)
        for it in d.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            author = (s.get("authorChannelId") or {}).get("value", s.get("authorDisplayName", ""))
            if author == YT_CHANNEL:
                continue
            hit = [o for o, rx in words.items() if rx.search(s.get("textOriginal", ""))]
            if len(hit) == 1 and (author not in last or s["publishedAt"] > last[author][0]):
                last[author] = (s["publishedAt"], hit[0])
        token, pages = d.get("nextPageToken"), pages + 1
        if not token:
            break
    counts = {o: 0 for o in options}
    for _, o in last.values():
        counts[o] += 1
    return counts


def tally(comments, options, skip=()):
    """comments = [(autor, cas, text)] -> {volba: pocet}; 1 hlas na autora (posledny platny)."""
    words = {o: re.compile(rf"\b{re.escape(o)}\b", re.I) for o in options}
    last = {}
    for author, ts, text in comments:
        if author in skip:
            continue
        hit = [o for o, rx in words.items() if rx.search(text or "")]
        if len(hit) == 1 and (author not in last or ts > last[author][0]):
            last[author] = (ts, hit[0])
    c = {o: 0 for o in options}
    for _, o in last.values():
        c[o] += 1
    return c


def ig_counts(options):
    """Instagram (Instagram Login API, scope instagram_business_manage_comments). Token IG_TOKEN plati 60 dni.
    Prispevok dielu = caption obsahuje 'X or Y' (volby dielu). Chyba / bez tokenu -> None."""
    tok = os.environ.get("IG_TOKEN")
    if not tok:
        return None
    g = "https://graph.instagram.com/v21.0/"
    try:
        def get(url):
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        media = get(g + "me/media?" + urllib.parse.urlencode({"fields": "id,caption", "limit": 25, "access_token": tok}))
        key = f"{options[0]} or {options[1]}".lower()
        mid = next((m["id"] for m in media.get("data", []) if key in (m.get("caption") or "").lower()), None)
        if not mid:
            print("votes: IG prispevok dielu nenajdeny")
            return None
        out, url = [], g + f"{mid}/comments?" + urllib.parse.urlencode(
            {"fields": "text,username,timestamp", "limit": 50, "access_token": tok})
        for _ in range(20):
            d = get(url)
            out += [(c.get("username", ""), c.get("timestamp", ""), c.get("text", "")) for c in d.get("data", [])]
            url = (d.get("paging") or {}).get("next")
            if not url:
                break
        return tally(out, options)
    except Exception as e:   # expirovany token, blokovana app...
        print("votes: Instagram sa neda citat:", str(e)[:120])
        return None


def votes(series, n, options):
    total = {o: 0 for o in options}
    src, vid = [], None
    if os.environ.get("YT_API_KEY"):
        vid = find_video(series, n)
        if vid:
            try:
                c = count(vid, options)
                src.append("youtube")
                total = {o: total[o] + c[o] for o in options}
            except urllib.error.HTTPError as e:   # komentare vypnute / docasna chyba
                print("votes: YT komentare sa nedaju citat", e.code)
        else:
            print(f"votes: video Part {n} na YouTube zatial nie je")
    else:
        print("votes: chyba YT_API_KEY")
    ig = ig_counts(options)
    if ig:
        src.append("instagram")
        total = {o: total[o] + ig[o] for o in options}
    if not vid and not ig:
        return None
    print(f"votes: {total} z {src}")
    return {"video_id": vid, "counts": total, "total": sum(total.values()), "sources": src}


if __name__ == "__main__":
    print(json.dumps(votes("SUDDENLY RICH", int(sys.argv[1]), sys.argv[2:]), indent=1))
