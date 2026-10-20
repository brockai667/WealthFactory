# -*- coding: utf-8 -*-
"""Autor dalsieho dielu = bezplatny model (Groq gpt-oss-120b). Biblia serie + doterajsie diely + vysledok hlasovania
-> series/<slug>/parts/partN.json (beaty, karty, zabery pre FLUX). Kontrola je mechanicka (check()), max 4 pokusy s opravou.
    python tools/write_part.py 2 WAIT [--votes '{"CLAIM": 3, "WAIT": 9}']
Titulnu kartu, kartu vysledku hlasovania a koncovu kartu sklada kod (ziadne vymyslene percenta)."""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import bible, load, part_path, save, state  # noqa: E402

MODELS = [os.environ.get("MODELS_MODEL", "openai/gpt-oss-120b"), os.environ.get("MODELS_FALLBACK", "openai/gpt-oss-20b")]
BASE = os.environ.get("MODELS_BASE_URL", "https://api.groq.com/openai/v1")
FX = {"rain", "dust", "glow", "handheld", "calls", "bubble", "steam"}
SFX = {"impact", "whoosh", "riser"}
ATTEMPTS = 8   # Groq free: kazdy pokus ~1-2 min, cloud timeout 90 min
CARD_KINDS = {
    "jackpot": "big dollar amount counts up, gets struck through, then a new amount appears below. fields: label, from (int $), to (int $), note (<=4 words), alt (<=5 words)",
    "tax": "huge percentage + a bar split between two sides. fields: label, line (<=5 words), pct (int), amount (int $ taken), left (int $ left), bar ([taker, you], each <=6 chars, e.g. [\"IRS\",\"YOU\"])",
    "bracket": "huge percentage, then 'You still owe' + red amount + rotated stamp. fields: label, line (<=5 words), pct (int), owe (int $), stamp (<=14 chars)",
    "public": "white box -> arrow -> red box -> stamp, cause and consequence. fields: label, line (<=4 words), arrow (<=3 words), stamp (<=14 chars), foot (<=10 words)",
    "rule": "dark card with a gold 'RULE N' badge and 1-3 very short lines (last line gold). fields: small ('RULE N'), text (lines joined with \\n, <=8 words total)",
}

RULES = """You write the next part of "{series}" - an interactive vertical video series in the style of @saveo.house
("Every Dollar Leaves a Trail"). Second person ("You just won..."), present tense, short punchy spoken sentences, dry dark humor,
real tension, cliffhangers. Each part TEACHES one true money lesson through the story. Viewers vote in comments; the winner
decides what you do next.

PREMISE: {premise}
HERO: {hero}
RECURRING CAST: {cast}

STRUCTURE of part {n} (250-300 spoken words, never under {wmin}, {bmin}-{bmax} beats, each beat = 1-2 sentences, max 22 words):
1. Beat 1: a 1-sentence recap hook of where we are (an image shot).
2. Beat 2: shot "card:result" - you say what the viewers chose ({winner}) and set it in motion ("You chose to wait." / "Most of you said wait.").
   {votes_line}
3. Beat 3 or 4: shot "card:title" (series title card) with one tense line.
4. Middle: the consequence of choosing {winner}. Teach THIS lesson with "Problem one / Problem two" (beat "label": "PROBLEM 1"...)
   and data cards. Every fact and number must come from LESSON FACTS below or from the story money; never invent statistics.
   Add exactly one rule card (RULE {rule_no}) that is the practical takeaway; its beat says the rule out loud as advice
   ("Rule two. Never sign anything the same day."), never "a rule appears". Use "day" beats ("Day four.", beat field "day": 4)
   to jump forward; days continue from day {day_from}.
5. Escalate to a cliffhanger, then a beat with "vote": true that clearly asks the choice between {opt_hint}
   ("So what do you do? X... or Y..."), then the LAST beat with shot "card:end" and text
   "Comment X or Y. The majority writes part {next}." (with your two real option words).
{finale_rule}

LESSON {n} - {theme}. LESSON FACTS (the only facts you may teach):
{facts}

THE MONEY (HUD at the top of the video): labels {hud_labels}. At the end of part {prev} the HUD was {hud_prev}
(cash $, tax due $, attention % 0-100). Give "hud": [cash, tax_due, attention] on beats where it changes; keep money consistent.
"attention" is how much unwanted attention you get (it rises with mistakes, can fall when you protect yourself).

IMAGES: every image beat uses a shot id ("img01".."img11"). Use 8-11 different shots, each used 1-3 times (never more than 3), never two
shots that look alike. For every shot id give a one-line brief in "shot_briefs": "<location> | <camera angle> | <who + emotion + key object>".
Locations: {locations} (or a new place name). Vary camera: extreme wide, low angle, high angle, over the shoulder, face close-up,
through a window, top-down hands, macro of an object. Never the same angle twice in a row. No text can be shown in images.

BEAT FIELDS: text (ALWAYS the spoken narration, also on card beats - never the shot id), shot ("imgXX" or "card:<id>"), optional: hud [3 ints], label ("PROBLEM 1"), day (int), vote (true),
fx (list from {fx}; "glow" needs "glow": [x 0-1, y 0-1, "#hex"] = where a phone/lamp light is in the picture), zoom ("in"/"out"),
sfx ("impact"|"whoosh"|"riser"), knock (a word from the text where a door knock hits), phase (2 on the 2nd beat of the same card).
Use the same card in 2 consecutive beats when the card has two steps (jackpot, bracket).

DATA CARD KINDS you may define in "cards" (any ids except title/result/end):
{kinds}
Card labels look like "PROBLEM 1 · THE TEAM" (monospace, upper case).

Return ONLY JSON:
{{"title": "2-3 WORDS UPPER CASE", "vote": ["OPTION1", "OPTION2"] (single upper-case words, max 8 letters; [] in the finale),
"result_foot": "<=8 words shown under the vote result", "caption": "1-2 lines for the post (hook + 'Comment X or Y. The majority writes Part {next}.')",
"summary": "3-4 sentences: what happened in this part and the open cliffhanger", "hud_end": [cash, tax_due, attention],
"bubble": null or {{"from": "Name", "text": "short chat message", "word": "a word from the beat text where it pops"}} (then that beat has fx "bubble"),
"cards": {{...}}, "shot_briefs": {{"img01": "...", ...}}, "beats": [...]}}"""

SHOT_RULES = """You turn shot briefs of a cartoon video series into detailed prompts for an image model (FLUX). Each shot = ONE vertical
9:16 illustration. Return ONLY JSON {{"shots": {{"img01": {{...}}, ...}}}} with, for every brief:
 - "location": one of {locations}; if the brief needs another place use a new snake_case key AND add "new_location":
   a full visual description of that place (25-45 words, concrete furniture, colors, light) that stays the same in later parts.
 - "camera": starts with "CAMERA:" + exact framing and angle (15-35 words).
 - "scene": starts with the emotion that fits the story moment (one word + period), then exactly what is visible: who, pose, face,
   hands, objects, light sources and colors. 45-80 words. No readable text, numbers or logos: papers, phones, screens show only shapes.
 - "refs": ["char"] when the hero (round white egg head, mustard beanie, olive jacket) is visible - then the scene names him
   "the hero"; [] when he is not (a lawyer/advisor/mom alone = refs [] + no_character true).
 - optional "hands_only": true when only his hands are visible (then location "table", refs []).
 - optional "no_character": true when the hero is not in the image (e.g. his mom alone); describe that person fully and write that
   they do NOT wear a mustard beanie or olive jacket.
Other people are drawn in the same cartoon style (round pale egg head, dot eyes, no ears, no nose) - say it in the scene.
Facial expression must match the spoken line (no angry face on good news)."""


def groq(messages, model, max_tokens):
    """Groq free tier: 8k tokenov/min vratane max_tokens -> male volania, pri 429/413 cakat."""
    key = os.environ.get("MODELS_TOKEN") or os.environ.get("GROQ_API_KEY")
    if not key:
        sys.exit("chyba MODELS_TOKEN / GROQ_API_KEY")
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.8, "reasoning_effort": "low",
                       "response_format": {"type": "json_object"}, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "WealthVote/1.0"})
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode(errors="replace")
            if e.code not in (413, 429, 500, 502, 503) or i == 4:
                raise RuntimeError(f"groq {e.code}: {msg}")
            print(f"groq {e.code}, cakam 65 s", file=sys.stderr)
            time.sleep(65)


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def say(n):
    """Cele cislo slovami (pre hlas)."""
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return ONES[n // 100] + " hundred" + (" " + say(n % 100) if n % 100 else "")
    for div, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= div:
            return say(n // div) + " " + name + (" " + say(n % div) if n % div else "")


def spell(text):
    """$38 million / 24% / 19,000 / 2011 -> slova. Desatinne cisla necha (kontrola ich vrati modelu)."""
    units = {"m": "million", "mm": "million", "b": "billion", "bn": "billion", "k": "thousand"}

    def money(m):
        num = say(int(m.group(1).replace(",", ""))) + (" point " + " ".join(ONES[int(d)] for d in m.group(2)) if m.group(2) else "")
        unit = (m.group(3) or "").lower()
        unit = units.get(unit, unit)
        return num + (" " + unit if unit else "") + " dollars"
    # $38 million, $38M, $380K, $1.5 billion, $5bn
    text = re.sub(r"\$(\d[\d,]*)(?:\.(\d+))?(?:\s*(million|billion|thousand|mm|bn|[MBKmbk])\b)?(?!\d|[.,]\d)", money, text)
    text = re.sub(r"(?<![\d.])(\d[\d,]*)%", lambda m: say(int(m.group(1).replace(",", ""))) + " percent", text)

    def year(m):
        hi, lo = int(m.group(1)), int(m.group(2))
        return say(hi) + " hundred" if lo == 0 else (say(hi * 100 + lo) if lo < 10 else say(hi) + " " + say(lo))
    text = re.sub(r"(?<![\d.$,])(19|20)(\d\d)(?!\d|[.,]\d|%)", year, text)
    text = re.sub(r"(?<![\d.$,])(\d[\d,]*)(?!\d|[.,]\d|%)", lambda m: say(int(m.group(1).replace(",", ""))), text)
    return text


def nums_in(card):
    return [v for k, v in card.items() if k in ("from", "to", "pct", "amount", "left", "owe") and isinstance(v, (int, float))]


def check_story(p, ctx):
    e = []
    beats, cards, briefs = p.get("beats") or [], p.get("cards") or {}, p.get("shot_briefs") or {}
    words = sum(len(str(b.get("text", "")).split()) for b in beats)
    if not ctx["wmin"] <= words <= ctx["wmax"]:
        e.append(f"total spoken words {words}, need {ctx['wmin']}-{ctx['wmax']}")
    if not ctx["bmin"] <= len(beats) <= ctx["bmax"]:
        e.append(f"{len(beats)} beats, need {ctx['bmin']}-{ctx['bmax']}")
    finale = ctx["finale"]
    vote = p.get("vote") or []
    if not finale and (len(vote) != 2 or any(not re.fullmatch(r"[A-Z]{2,8}", str(v)) for v in vote) or vote[0] == vote[1]):
        e.append('"vote" must be 2 different single UPPER-CASE words (2-8 letters)')
    allowed = set(ctx["numbers"])
    for i, b in enumerate(beats):
        t = str(b.get("text", ""))
        if len(t.split()) > 24:
            e.append(f"beat {i + 1} has {len(t.split())} words (max 22)")
        if re.search(r"\d", t):
            e.append(f"beat {i + 1}: write numbers as words for the voice, no digits")
        if len(t.split()) < 3 or re.search(r"card:|\bimg\d|\bdollars [A-Za-z]\b|·", t) or t.isupper():
            e.append(f"beat {i + 1}: text must be a full spoken sentence (3+ words), never a shot id")
        s = str(b.get("shot", ""))
        if s.startswith("card:"):
            if s[5:] not in cards and s[5:] not in ("title", "result", "end"):
                e.append(f"beat {i + 1}: card '{s[5:]}' not defined in cards")
        elif s not in briefs:
            e.append(f"beat {i + 1}: shot '{s}' has no entry in shot_briefs")
        for f in b.get("fx") or []:
            if f not in FX:
                e.append(f"beat {i + 1}: unknown fx '{f}'")
        if "glow" in (b.get("fx") or []):
            g = b.get("glow")
            if not (isinstance(g, list) and len(g) == 3 and all(isinstance(x, (int, float)) for x in g[:2])):
                e.append(f"beat {i + 1}: fx glow needs \"glow\": [x, y, \"#hex\"]")
        if b.get("sfx") and b["sfx"] not in SFX:
            e.append(f"beat {i + 1}: sfx must be one of {sorted(SFX)}")
        if b.get("knock") and str(b["knock"]).lower() not in t.lower():
            e.append(f"beat {i + 1}: knock word not in the text")
        h = b.get("hud")
        if h is not None:
            if not (isinstance(h, list) and len(h) == 3 and all(isinstance(x, (int, float)) for x in h) and 0 <= h[2] <= 100):
                e.append(f"beat {i + 1}: hud must be [cash, tax_due, attention 0-100]")
            else:
                allowed.update(h[:2])
    shots_seq = [b.get("shot") for b in beats]
    if beats:
        if shots_seq.count("card:result") != 1 or len(beats) < 2 or beats[1].get("shot") != "card:result":
            e.append('beat 2 (and only beat 2) must use shot "card:result"')
        if "card:title" not in shots_seq[2:5]:
            e.append('beat 3, 4 or 5 must use shot "card:title"')
        if beats[-1].get("shot") != "card:end":
            e.append('last beat must use shot "card:end"')
        if not finale:
            if not (len(beats) > 2 and beats[-2].get("vote") and not str(beats[-2].get("shot", "")).startswith("card:")):
                e.append('the beat before the last needs "vote": true and an image shot')
            for v in vote:
                if str(v).lower() not in str(beats[-1].get("text", "")).lower():
                    e.append(f'last beat text must contain the option "{v}"')
                if not re.search(rf"\b{re.escape(str(v).lower())}", str(beats[-2].get("text", "")).lower()):
                    e.append(f'the vote question (beat before the last) must say the option word "{v}" itself')
    days = [b.get("day") for b in beats if b.get("day")]
    if any(not isinstance(d, int) for d in days) or any(d < ctx["day_from"] + i for i, d in enumerate(days)):
        e.append(f"days must be ints that continue from day {ctx['day_from']} and go up")
    rules = 0
    used_cards = {s[5:] for s in shots_seq if str(s).startswith("card:")}
    for cid, c in cards.items():
        k = c.get("kind") if isinstance(c, dict) else None
        if cid in ("title", "result", "end"):
            e.append(f"do not define card '{cid}' (made by code)")
            continue
        if k == "rule":
            rules += 1
            if c.get("small") != f"RULE {ctx['rule_no']}" or len(str(c.get("text", "")).split()) > 12:
                e.append(f"rule card: small must be 'RULE {ctx['rule_no']}', text max 8 words")
        elif k not in CARD_KINDS:
            e.append(f"card '{cid}': unknown kind '{k}'")
            continue
        else:
            need = re.findall(r"(\w+) \(", CARD_KINDS[k].split("fields:")[1]) + ["label"]
            miss = [f for f in need if f not in c]
            if miss:
                e.append(f"card '{cid}' ({k}) misses fields {miss}")
            for f in ("from", "to", "pct", "amount", "owe"):
                if f in c and not (isinstance(c[f], (int, float)) and c[f] > 0):
                    e.append(f"card '{cid}': {f} must be a real number above 0 - if no lesson number fits, use another card kind")
            for x in nums_in(c):
                if not any(abs(x - a) <= max(1, 0.02 * abs(a)) for a in allowed):
                    e.append(f"card '{cid}': number {x} is not from the lesson facts or the story money")
        if cid not in used_cards:
            e.append(f"card '{cid}' is never used")
    if rules != 1:
        e.append(f"exactly one rule card (RULE {ctx['rule_no']}), you have {rules}")
    if not ctx["finale"] and not any(isinstance(c, dict) and c.get("kind") in CARD_KINDS and c.get("kind") != "rule"
                                     for c in cards.values()):
        e.append("teach with at least one data card (jackpot/tax/bracket/public) besides the rule card")
    used = [s for s in shots_seq if not str(s).startswith("card:")]
    if not 7 <= len(briefs) <= 12:
        e.append(f"{len(briefs)} shots, need 8-11")
    for k in briefs:
        if not re.fullmatch(r"img\d\d", k):
            e.append(f"shot id '{k}' must look like img01")
        if k not in used:
            e.append(f"shot '{k}' is never used")
        elif used.count(k) > 4:
            e.append(f"shot '{k}' used {used.count(k)} times (max 3)")
    if not (isinstance(p.get("hud_end"), list) and len(p["hud_end"]) == 3):
        e.append("hud_end must be [cash, tax_due, attention]")
    for f in ("title", "caption", "summary", "result_foot"):
        if not p.get(f):
            e.append(f'missing "{f}"')
    if p.get("bubble") and not any("bubble" in (x.get("fx") or []) for x in beats):
        e.append("bubble defined but no beat has fx bubble")
    return e


def check_shots(shots, briefs, locs):
    e = []
    for k in briefs:
        s = shots.get(k)
        if not isinstance(s, dict):
            e.append(f"shot '{k}' missing")
            continue
        if s.get("location") not in locs and not s.get("new_location"):
            e.append(f"shot '{k}': location must be one of {sorted(locs)} or give new_location")
        if not str(s.get("camera", "")).startswith("CAMERA:"):
            e.append(f"shot '{k}': camera must start with 'CAMERA:'")
        if len(str(s.get("scene", "")).split()) < 30:
            e.append(f"shot '{k}': scene too short (45-80 words)")
        if s.get("refs") not in (["char"], []):
            e.append(f"shot '{k}': refs must be [\"char\"] or []")
        elif s["refs"] and "hero" not in str(s.get("scene", "")).lower():
            e.append(f"shot '{k}': refs [\"char\"] draws the HERO - use it only when the scene shows 'the hero'; "
                     "for another person alone use refs [] and no_character true")
    return e


def ask(system, user, checker, max_tokens, label):
    """Volanie + kontrola; oprava = novy pokus so zoznamom chyb (bez dlhej predoslej odpovede - TPM limit)."""
    errs = []
    for attempt in range(ATTEMPTS):
        model = MODELS[0]
        u = user if not errs else user + "\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED. Avoid these mistakes:\n- " + "\n- ".join(errs[:15])
        try:
            raw = groq([{"role": "system", "content": system}, {"role": "user", "content": u}], model, max_tokens)
            p = json.loads(raw)
            errs = checker(p)
        except (json.JSONDecodeError, AttributeError, TypeError, KeyError, RuntimeError) as ex:
            p, errs = None, [f"invalid JSON or structure: {str(ex)[:200]}"]
        print(f"{label} pokus {attempt + 1} ({model}): {len(errs)} chyb", *errs[:10], sep="\n  ")
        if not errs:
            return p
        time.sleep(60)   # TPM okno
    sys.exit(f"{label}: autor nezvladol kontrolu ani na {ATTEMPTS}. pokus")


def build_cards(p, ctx):
    """Karty title/result/end sklada kod: ziadne vymyslene percenta."""
    b, n = ctx["bible"], ctx["n"]
    words = b["tagline"].split()
    big = [words[0], words[1], " ".join(words[2:-1])] if len(words) == 5 else words[:-1]
    p["cards"]["title"] = {"kind": "title", "small": f"PART {n} · {p['title']}", "big": big, "accent": words[-1]}
    vr = ctx["vote_result"]
    opts = [{"name": o} for o in vr["options"]]
    if vr.get("counts") and vr["total"] >= 5:
        opts[0]["pct"] = round(100 * vr["counts"][opts[0]["name"]] / vr["total"])
        opts[1]["pct"] = 100 - opts[0]["pct"]
    p["cards"]["result"] = {"kind": "result", "label": f"PART {n - 1} · YOU VOTED", "options": opts,
                            "winner": vr["options"].index(vr["winner"]), "foot": p.get("result_foot", "")}
    small = f"{b['series']} · {b['tagline']}"
    if ctx["finale"]:
        p["vote"] = []
        p["cards"]["end"] = {"kind": "end", "small": small, "big": "THE END", "accent": "FOR NOW",
                             "foot": "Follow for the next story.\nWhat should it be? Comment below."}
    else:
        v = p["vote"]
        p["cards"]["end"] = {"kind": "end", "small": small, "big": f"PART {n + 1}", "accent": "TOMORROW",
                             "foot": f"Comment {v[0]} or {v[1]}.\nThe majority writes Part {n + 1}."}
    return p


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n, winner = int(args[0]), args[1].upper()
    counts = json.loads(sys.argv[sys.argv.index("--votes") + 1]) if "--votes" in sys.argv else None
    b = bible()
    prev = [load(part_path(i)) for i in range(1, n)]
    last = prev[-1]
    lesson = b["lessons"][str(n)]
    finale = n >= b["parts_max"]
    rule_no = 1 + sum(1 for q in prev for c in q["cards"].values() if c.get("kind") == "rule")
    day_from = 1 + max([1] + [x.get("day", 0) for q in prev for x in q["beats"]])
    hud_prev = last.get("hud_end") or [0, 0, 0]
    numbers = set(lesson.get("numbers", [])) | set(hud_prev[:2])
    for q in prev:
        numbers |= {x for c in q["cards"].values() for x in nums_in(c)}
    total = sum(counts.values()) if counts else 0
    locs = set(b["image"]["locations"])
    ctx = {"n": n, "bible": b, "finale": finale, "rule_no": rule_no, "day_from": day_from, "numbers": numbers,
           "wmin": 205, "wmax": 320, "bmin": 18, "bmax": 32,   # 18: Groq casto pise 18-19 beatov, slov je dost
           "vote_result": {"options": last["vote"], "winner": winner, "counts": counts, "total": total}}
    if total >= 5:
        pct = round(100 * counts[winner] / total)
        votes_line = f"Real result: {winner} won with {pct}% of {total} votes - you may say 'most of you'."
    else:
        votes_line = "Only a few votes came in - say 'You chose ...', never mention vote counts or percentages."
    story = "\n".join(f"PART {i + 1} ({q['title']}): {q['summary']} Vote options: {q['vote']}." for i, q in enumerate(prev))
    last_text = " ".join(x["text"] for x in last["beats"][-6:])
    sysmsg = RULES.format(
        series=b["series"], premise=b["premise"], hero=b["hero"], cast=json.dumps(b["cast"]), n=n, prev=n - 1, next=n + 1,
        wmin=ctx["wmin"], wmax=ctx["wmax"], bmin=ctx["bmin"], bmax=ctx["bmax"], winner=winner, votes_line=votes_line,
        rule_no=rule_no, day_from=day_from, opt_hint="two concrete, opposite, tempting actions (each risky in its own way)",
        finale_rule=("6. THIS IS THE FINALE: resolve the story, no vote: last beat 'card:end' says the story ends here; no beat has vote."
                     if finale else ""),
        theme=lesson["theme"], facts="\n".join("- " + f for f in lesson["facts"]), hud_labels=b["hud_labels"],
        hud_prev=hud_prev, locations=sorted(locs), fx=sorted(FX),
        kinds="\n".join(f"- {k}: {v}" for k, v in CARD_KINDS.items()))
    ex = prev[0]
    example = {"title": ex["title"], "vote": ex["vote"], "cards": {k: ex["cards"][k] for k in ("jackpot", "rule1")},
               "beats": ex["beats"][4:11]}
    user = (f"STORY SO FAR:\n{story}\n\nLAST LINES OF PART {n - 1}: {last_text}\n\nVIEWERS CHOSE: {winner} "
            f"(options were {last['vote']}).\n\nSTYLE EXAMPLE (a few beats of part 1 - copy the rhythm, not the content):\n"
            f"{json.dumps(example, ensure_ascii=False)}\n\nWrite part {n} now.")

    def fix_and_check(p):
        """Drobnosti opravi kod sam, modelu sa vracaju len skutocne chyby."""
        beats = p.get("beats") or []
        cards = p.get("cards") or {}
        for cid in ("title", "result", "end"):
            cards.pop(cid, None)
        if len(beats) > 2 and "card:result" not in [x.get("shot") for x in beats]:
            beats[1]["shot"] = "card:result"
        last_img = None
        for i, x in enumerate(beats):
            x["text"] = spell(str(x.get("text", "")))
            x["fx"] = [f for f in (x.get("fx") or []) if f in FX]
            g = x.get("glow")
            if "glow" in x["fx"] and not (isinstance(g, list) and len(g) == 3):
                x["fx"].remove("glow")
            if x.get("sfx") not in SFX:
                x.pop("sfx", None)
            s = str(x.get("shot", ""))
            if s.startswith("card:") and s[5:] not in cards and s[5:] not in ("title", "result", "end") and last_img:
                x["shot"] = s = last_img   # model si vymyslel kartu (napr. card:vote) -> predosly obrazok
            if not s.startswith("card:"):
                last_img = s
            t = x["text"]
            if len(t.split()) < 3 or t.startswith("card:") or "·" in t or t.isupper():   # karta bez vety -> veta kodom
                if s == "card:result":
                    x["text"] = f"You chose {winner.lower()}."
                elif s == "card:title":
                    x["text"] = b["tagline"].rstrip(".").capitalize() + "."
        vote = p.get("vote") or []
        if not finale and len(beats) > 3 and len(vote) == 2:   # 20.10.: diel 2 padol 8x na tychto drobnostiach -> opravi kod
            q = beats[-2]
            if str(q.get("shot", "")).startswith("card:") and last_img:
                q["shot"] = last_img
            if not str(q.get("shot", "")).startswith("card:"):
                q["vote"] = True
            for x, tail in ((q, f" {vote[0].capitalize()} or {vote[1].lower()}?"),
                            (beats[-1], f" Comment {vote[0]} or {vote[1]}.")):
                if any(not re.search(rf"\b{re.escape(v.lower())}", str(x.get("text", "")).lower()) for v in vote):
                    x["text"] = str(x.get("text", "")).rstrip() + tail
        rules = [c for c in cards.values() if isinstance(c, dict) and c.get("kind") == "rule"]
        if len(rules) == 1:
            rules[0]["small"] = f"RULE {ctx['rule_no']}"
        used = {x.get("shot") for x in beats}
        p["shot_briefs"] = {k: v for k, v in (p.get("shot_briefs") or {}).items() if k in used}
        return check_story(p, ctx)

    draft = part_path(n).with_suffix(".draft.json")   # hotovy scenar sa pri opakovani znova nepise
    if draft.exists():
        p = load(draft)
    else:
        p = ask(sysmsg, user, fix_and_check, 4200, "scenar")
        save(draft, p)
        time.sleep(60)
    beat_lines = {}
    for x in p["beats"]:
        beat_lines.setdefault(x["shot"], []).append(x["text"])
    briefs = "\n".join(f"{k}: {v}  | spoken over it: {' '.join(beat_lines.get(k, []))}" for k, v in p["shot_briefs"].items())
    shot_sys = SHOT_RULES.format(locations=sorted(locs))
    ex_shots = {k: ex["shots"][k] for k in ("img03", "img04")}
    shot_user = (f"HERO: {b['image']['character']}\nPLACES (fixed look):\n" +
                 "\n".join(f"- {k}: {v[:160]}" for k, v in b["image"]["locations"].items()) +
                 f"\n\nEXAMPLE OUTPUT FOR TWO SHOTS:\n{json.dumps(ex_shots, ensure_ascii=False)}\n\nSHOT BRIEFS:\n{briefs}")
    def shots_of(q):
        return q.get("shots") if isinstance(q.get("shots"), dict) else {k: v for k, v in q.items() if k.startswith("img")}
    s = ask(shot_sys, shot_user, lambda q: check_shots(shots_of(q), p["shot_briefs"], locs), 4500, "zabery")
    p["shots"] = {k: shots_of(s)[k] for k in p["shot_briefs"]}
    for k, sh in p["shots"].items():
        if sh.get("hands_only"):
            sh["refs"], sh["location"] = [], "table" if "table" in locs else sh["location"]
        if sh.get("new_location") and sh["location"] not in b["image"]["locations"]:
            b["image"]["locations"][sh["location"]] = "SETTING: " + sh["new_location"]
        sh.pop("new_location", None)
    save(part_path(1).parent.parent / "bible.json", b)
    p = build_cards(p, ctx)
    p["part"], p["winner"], p["lesson"] = n, winner, lesson["theme"]
    p["caption"] = p["caption"].strip() + "\n\n" + b["hashtags"]
    save(part_path(n), p)
    draft.unlink(missing_ok=True)
    print("ulozene", part_path(n), sum(len(x["text"].split()) for x in p["beats"]), "slov,", len(p["shots"]), "zaberov")


if __name__ == "__main__":
    main()
