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

ROOT = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(ROOT, "topics_bank.json")
STATE = os.path.join(ROOT, "used_topics.json")

TARGET = int(os.environ.get("TOPICS_TARGET", "15"))   # min. pocet nepouzitych tem
MODEL = os.environ.get("MODELS_MODEL", "openai/gpt-4o-mini")
BASE = os.environ.get("MODELS_BASE_URL", "https://models.github.ai/inference")
TOKEN = os.environ.get("MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN")

SYSTEM = ("You are a viral short-form video scriptwriter for a money & wealth-mindset brand. "
          "You teach timeless money psychology and habits in plain language. You ONLY use "
          "widely-accepted principles (no invented numbers, no specific stock/crypto picks, "
          "no promises of returns). You output strict JSON, nothing else. THE HOOK (the very first line / segment 1) is the single most important thing in the whole video: it MUST stop the scroll within 2 seconds. Make it concrete and specific (a number, a name, a vivid image, or a sharp contradiction) and open a curiosity gap that can ONLY be closed by watching to the end. Lead with the most shocking part FIRST, never a slow setup. Forbidden hook openers: 'Did you know', 'Have you ever', 'Imagine', 'Here are', 'In this video', 'Let me tell you'.")

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


def build_prompt(n, existing_titles):
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
        f"- Do NOT reuse any of these existing titles: {existing_titles}\n"
        "Return ONLY the JSON array."
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
    raw = call_model(build_prompt(need + 3, sorted(titles)))
    items = extract_json(raw)
    added = 0
    for t in items:
        if not valid(t) or t["title"] in titles:
            continue
        bank.append(t)
        titles.add(t["title"])
        added += 1
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Pridanych {added} novych tem. Banka ma teraz {len(bank)} tem.")


if __name__ == "__main__":
    main()
