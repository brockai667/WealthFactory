#!/usr/bin/env python3
"""
Doplni banku tem (topics_bank.json) cez GitHub Models (zadarmo) ak je malo nepouzitych.
Nika: PENIAZE / mindset bohatych (vseobecne principy, NIE konkretne investicne rady).
Spusta sa v GitHub Actions (token z GITHUB_TOKEN, permission models: read).
Lokalne: nastav MODELS_TOKEN na GitHub PAT s pravom 'models'.
"""
import json
import os
import re
import sys

import requests

try:
    import trends                      # trend scanner (Reddit + YouTube), voliteľný
except Exception:
    trends = None

ROOT = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(ROOT, "topics_bank.json")
STATE = os.path.join(ROOT, "used_topics.json")

# Nika: PENIAZE / wealth-mindset -> kde ľudia o peniazoch reálne diskutujú / čo pozerajú
TREND_SUBREDDITS = ["personalfinance", "Frugal", "financialindependence",
                    "Entrepreneur", "FinancialPlanning"]
TREND_YT_QUERIES = ["money habits", "wealth mindset", "how the rich think"]

TARGET = int(os.environ.get("TOPICS_TARGET", "15"))   # min. pocet nepouzitych tem
MODEL = os.environ.get("MODELS_MODEL", "openai/gpt-4o-mini")
BASE = os.environ.get("MODELS_BASE_URL", "https://models.github.ai/inference")
TOKEN = os.environ.get("MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN")

SYSTEM = ("You are a viral short-form video scriptwriter for a money & wealth-mindset brand. "
          "You teach timeless money psychology and habits in plain language. You ONLY use "
          "widely-accepted principles (no invented numbers, no specific stock/crypto picks, "
          "no promises of returns). You output strict JSON, nothing else.")

EXAMPLE = {
    "title": "3 Money Habits of the Rich",
    "segments": [
        {"text": "The rich don't budget to save money — they budget to invest it.", "keywords": "money cash"},
        {"text": "And the next habit is why most people stay broke.", "keywords": "city skyline night"},
        {"text": "They pay themselves first, before any bill or treat.", "keywords": "person counting money"},
        {"text": "They buy assets that earn while they sleep.", "keywords": "luxury house real estate"},
        {"text": "And they treat their time as more valuable than cash.", "keywords": "luxury watch"},
        {"text": "Follow for the money mindset they don't teach you.", "keywords": "business man suit"},
    ],
    "description": "The rich budget to invest, not just to save. Mindset is everything. Follow for daily money wisdom!",
    "hashtags": ["#money", "#wealthmindset", "#millionairemindset", "#success", "#finance", "#shorts", "#fyp", "#motivation"],
}


import random  # CTAS_ROTATE

CTAS = [
    "Follow for the money mindset they don't teach you.",
    "Follow for daily money habits that actually work.",
    "Follow if you're done staying broke.",
    "Follow for the wealth lessons school skipped.",
    "Follow and your future rich self will thank you.",
]


def build_prompt(n, existing_titles, trending=None):
    trend_block = ""
    if trending:
        joined = "\n".join(f"- {t}" for t in trending)
        trend_block = (
            "\nWHAT REAL PEOPLE ARE WORRIED ABOUT / WATCHING THIS WEEK (live headlines from Reddit "
            "money communities and top YouTube money videos — this is what the audience ACTUALLY "
            "cares about right now):\n"
            f"{joined}\n"
            "IMPORTANT: at least HALF of the topics you generate MUST be directly inspired by a "
            "SPECIFIC worry, question or desire in the list above (e.g. emergency funds, fear of "
            "retiring with nothing, renting vs buying, getting out of debt, lifestyle creep, "
            "lending money to family). Take that real-life worry and turn it into a money-MINDSET "
            "hook — a timeless principle or psychology angle, NOT specific financial advice. "
            "Do NOT copy any headline word-for-word, and NEVER mention Reddit or YouTube.\n"
        )
    return (
        f"Generate {n} NEW faceless short-form video topics for a MONEY & WEALTH-MINDSET brand "
        "(TikTok / Reels / YouTube Shorts).\n"
        "Niche: how the rich think, money habits, wealth psychology, money mistakes, and timeless "
        "financial principles (saving vs investing, assets, compounding, paying yourself first).\n"
        "Return ONLY a JSON array (no markdown, no commentary). Each item EXACTLY this schema:\n"
        f"{json.dumps(EXAMPLE, ensure_ascii=False, indent=2)}\n\n"
        "Rules (make it feel PRO and VIRAL):\n"
        "- title: catchy, like '3 Money Habits of the Rich' or '3 Reasons You Stay Broke'.\n"
        "- exactly 6 segments. Segment 1 is THE HOOK: a single counterintuitive money truth, "
        "under 12 words, that makes the viewer think 'wait, really?'. Never start with 'Did you know'.\n"
        "- segment 2 is a short open-loop tease that keeps people watching (e.g. 'But the reason why "
        "is the part nobody explains.', 'And the last one feels totally normal.').\n"
        "- the SECOND-TO-LAST segment should loop back to the opening hook (circle back to the money "
        "truth you started with) so a rewatch feels seamless.\n"
        "- the LAST segment text MUST be exactly: 'Follow for the money mindset they don't teach you.'\n"
        "- write for a SPOKEN voiceover: short, punchy, confident sentences, simple words.\n"
        "- TEACH TIMELESS PRINCIPLES AND MINDSET ONLY. Absolutely NO specific investment advice, NO "
        "stock/crypto/fund picks, NO 'do this to get rich quick', NO promises or guarantees of returns, "
        "NO invented statistics. Keep it general, motivational and educational.\n"
        "- each segment 'keywords': 1-3 ENGLISH words for real Pexels footage that VISUALLY MATCHES "
        "what that line talks about (money/luxury/business themed), so viewers picture it (e.g. line "
        "about compounding -> 'growing plant money', about assets -> 'luxury house real estate', about "
        "time -> 'luxury watch'). Concrete, never abstract.\n"
        "- description: one engaging sentence ending with 'Follow for daily money wisdom!'.\n"
        "- About half the time, add ONE fitting emoji at the very END of the description (e.g. 💰, 📈, 💡, 🏦). "
        "Emoji ONLY in the description text, NEVER inside any segment 'text' (spoken captions).\n"
        "- hashtags: 6-8 relevant tags including #money #wealthmindset #shorts #fyp.\n"
        "- VARY THE TITLE FORMAT: do NOT start more than one in five titles with a number "
        "(avoid the repetitive 'N things' pattern). Mix a bold claim, a question, a "
        "'why/how' angle and a curiosity gap so titles never look the same.\n"
        "- ACCURACY IS CRITICAL: use ONLY widely-documented, verifiable facts. NEVER invent or "
        "guess numbers, percentages, dates, amounts or statistics. If a specific figure is not "
        "universally established, say it generally instead of making one up. Wrong facts kill the "
        "channel's credibility, so double-check every claim.\n"
        "- BE SPECIFIC: name the ACTUAL subject of the video (the exact place, case, event, person "
        "or thing) so it is never vague. Viewers complain when the location or subject is not named.\n"
        f"- Do NOT reuse any of these existing titles: {existing_titles}\n"
        "- Do NOT repeat the same SUBJECT, fact or concept as any existing title above, even reworded, "
        "renumbered or from a different angle. Every topic must be a genuinely DIFFERENT idea.\n"
        + trend_block +
        "STORYBOARD (visual directing, IMPORTANT): to EVERY segment ADD a field 'visual' = an object choosing HOW to visualize exactly what that line SAYS (never generic): {\"type\":\"kenburns\",\"prompt\":\"LITERAL ENGLISH image prompt naming ONE concrete, instantly recognizable subject/scene that depicts exactly what the line says (a real thing a camera could photograph; NEVER abstract, NEVER metaphors)\"} for normal lines; {\"type\":\"counter\",\"target\":1000,\"suffix\":\"x\",\"label\":\"3-4 WORD CAPTION\"} when the line contains a big number; {\"type\":\"compare\",\"small_prompt\":\"...\",\"big_prompt\":\"...\",\"small_label\":\"X\",\"big_label\":\"Y\",\"stat\":\"300x\"} for size/amount comparisons; {\"type\":\"callouts\",\"prompt\":\"subject image\",\"labels\":[\"SHORT LABEL\"]} to point at parts of a subject; {\"type\":\"lineup\",\"items\":[{\"name\":\"A\",\"prompt\":\"...\"}]} for listing 3-5 things; {\"type\":\"arrow\",\"from_prompt\":\"...\",\"to_prompt\":\"...\",\"label\":\"WHAT MOVES\"} for movement/flow. First segment gets {\"type\":\"hook\",\"prompt\":\"dramatic scene image\",\"big\":\"SHORT PUNCHY QUESTION OR CLAIM (max 5 words)\"}; last segment {\"type\":\"cta\",\"prompt\":\"iconic subject of the video\"}. Labels MUST describe what the narration says at that moment - never invent unrelated text. Image prompts must describe 3D RENDERED CGI assets in a modern 3D-explainer style - NEVER photographs, NEVER photorealistic people; if a person is needed, describe a cute stylized 3D cartoon character instead; prefer objects, anatomy, environments, close-up details; the subject must FILL the frame and be well lit. Return ONLY the JSON array."
    )


def call_model(user_text):
    r = requests.post(
        BASE.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "temperature": 0.95,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_text},
            ],
        },
        timeout=180,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Models API {r.status_code}: {r.text[:500]}")
    return r.json()["choices"][0]["message"]["content"]


def extract_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    a, b = s.find("["), s.rfind("]")
    if a != -1 and b != -1:
        s = s[a:b + 1]
    return json.loads(s)


def valid(t):
    if not isinstance(t, dict):
        return False
    if "title" not in t or "segments" not in t:
        return False
    if not isinstance(t["segments"], list) or len(t["segments"]) < 4:
        return False
    for seg in t["segments"]:
        if "text" not in seg or "keywords" not in seg:
            return False
    t.setdefault("description", t["title"] + " Follow for daily money wisdom!")
    t.setdefault("hashtags", ["#money", "#wealthmindset", "#shorts", "#fyp"])
    return True


_STOP = {"why", "your", "the", "is", "a", "of", "you", "that", "are", "and", "to", "in",
         "on", "how", "this", "for", "with", "it", "its", "can", "cant", "not", "be", "do",
         "than", "them", "their", "own", "what", "when", "was", "were", "has", "have", "from",
         "more", "most", "just", "every", "an", "as", "or", "but", "so", "hidden", "secret",
         "surprising", "truth", "facts", "fact", "these", "there", "they"}


def _sig(title):
    return set(w for w in re.findall(r"[a-z]+", str(title).lower()) if len(w) > 2 and w not in _STOP)


def _too_similar(sig, existing_sigs):
    if not sig:
        return False
    for es in existing_sigs:
        if not es:
            continue
        inter = len(sig & es)
        if inter >= 3:
            return True
        if inter >= 2 and inter / (len(sig | es) or 1) >= 0.5:
            return True
    return False


def main():
    if not TOKEN:
        print("CHYBA: chyba MODELS_TOKEN/GITHUB_TOKEN")
        sys.exit(1)
    bank = json.load(open(BANK, encoding="utf-8"))
    used = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else []
    titles = {t["title"] for t in bank}
    unused = [t for t in bank if t["title"] not in used]
    need = TARGET - len(unused)
    if need <= 0:
        print(f"Banka OK: {len(unused)} nepouzitych tem (>= {TARGET}), netreba dopnat.")
        return
    print(f"Nepouzitych {len(unused)} < {TARGET} -> generujem ~{need} novych tem cez {MODEL}...")
    trending = []
    if trends is not None:
        try:
            trending, meta = trends.gather(TREND_SUBREDDITS, TREND_YT_QUERIES, top=18, return_meta=True)
            if trending:
                print(f"Trendy: {len(trending)} titulkov (Reddit={meta['reddit']}, YouTube={meta['youtube']}) "
                      "-> temy z realneho dopytu.")
            else:
                print(f"Trendy: zdroj nedostupny (Reddit={meta['reddit']}, YouTube={meta['youtube']}) "
                      "-> generujem klasicky.")
        except Exception as e:
            print("Trendy preskocene:", str(e)[:120])
    raw = call_model(build_prompt(need + 3, sorted(titles), trending))
    items = extract_json(raw)
    added = 0
    existing_sigs = [_sig(x) for x in titles]
    for t in items:
        if not valid(t) or t["title"] in titles:
            continue
        _s = _sig(t["title"])
        if _too_similar(_s, existing_sigs):   # ta ista TEMA (iny nazov) -> preskoc (ziadne opakovanie)
            print("  preskocene (podobna tema):", t["title"]); continue
        if t.get("segments"):
            t["segments"][-1]["text"] = random.choice(CTAS)  # CTAS_ROTATE: nie vzdy rovnaka veta
        bank.append(t)
        titles.add(t["title"])
        existing_sigs.append(_s)
        added += 1
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Pridanych {added} novych tem. Banka ma teraz {len(bank)} tem.")


if __name__ == "__main__":
    main()
