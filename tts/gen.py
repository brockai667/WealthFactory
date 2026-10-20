# Orpheus hlas pre ukazku: nazvy suborov = kluc cache z vote/tools/prep.py synth() -> lokalny render ich najde v tts_cache
import hashlib, json, os, time, requests
K, V = os.environ["MODELS_TOKEN"], "troy"
os.makedirs("out", exist_ok=True)
for b in json.load(open("tts/part.json", encoding="utf-8"))["beats"]:
    emo = b.get("emo", "")
    h = hashlib.md5((f"orpheus:{V}:{emo}:" + b["text"]).encode()).hexdigest()[:16]
    for a in range(5):
        r = requests.post("https://api.groq.com/openai/v1/audio/speech", headers={"Authorization": f"Bearer {K}"},
                          json={"model": "canopylabs/orpheus-v1-english", "voice": V, "response_format": "wav",
                                "input": (f"[{emo}] " if emo else "") + b["text"]}, timeout=90)
        print(h, emo, r.status_code, r.headers.get("x-ratelimit-remaining-requests"), "" if r.ok else r.text[:160])
        if r.ok:
            open(f"out/{h}.mp3", "wb").write(r.content); json.dump(None, open(f"out/{h}.json", "w")); break
        time.sleep(10 + 10 * a)
