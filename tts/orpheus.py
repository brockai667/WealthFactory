import os, requests
K = os.environ["MODELS_TOKEN"]
L = [("excited", "You just won a hundred million dollars!"), ("shocked", "But the check says... thirty-eight million."), ("suspicious", "So where did sixty-two million go?")]
m = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {K}"}, timeout=30).json()
print("tts models:", [x["id"] for x in m.get("data", []) if "orpheus" in x["id"] or "tts" in x["id"]])
os.makedirs("out", exist_ok=True)
for voice in ("troy", "daniel", "austin"):
    for i, (emo, txt) in enumerate(L):
        r = requests.post("https://api.groq.com/openai/v1/audio/speech", headers={"Authorization": f"Bearer {K}"},
                          json={"model": "canopylabs/orpheus-v1-english", "voice": voice, "input": f"[{emo}] {txt}", "response_format": "wav"}, timeout=60)
        print(voice, i, r.status_code, "" if r.ok else r.text[:200])
        if r.ok:
            open(f"out/{voice}_{i}.wav", "wb").write(r.content)
