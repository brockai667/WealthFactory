# Vote story (WealthMindset)

An interactive series in the saveo.house format. Each part ends with a choice between two options. Viewers vote in the comments, and the next part follows the winner. Each part teaches one true money lesson. The whole thing runs on its own in GitHub Actions (`.github/workflows/vote.yml`, daily at 13:40 UTC, posts at 18:00 Bratislava). The PC can stay off, and it costs nothing.

## Daily run (`tools/run.py`)
1. **Votes:** `votes.py` finds Part N-1 on the YouTube channel (uploads playlist) and reads the comments. Each author gets one vote, and only a comment containing exactly one of the options counts. With no votes or a tie, the pick is a fixed random choice based on the part number.
2. **Script:** `write_part.py` asks Groq gpt-oss-120b (free) to write `series/<slug>/parts/partN.json` from the bible (`bible.json`: premise, cast, look of the images, verified lesson facts per part) and the summaries of earlier parts.
   - It makes two calls: the script plus cards, then the image prompts. Groq's limit is 8k tokens per minute.
   - Each result goes through a mechanical check and up to 5 retries. Card numbers must come from the lesson facts or the story's money.
   - Code builds the title card, the vote result card and the end card. The percentages are shown only for 5 or more real votes.
3. **Images:** `gen_images.py` runs Cloudflare FLUX.2 klein 9B with the character reference (`ref.jpg`). Accounts rotate (`CLOUDFLARE_API_TOKEN[_n]`). If every account hits the daily limit, it exits with code 3 and finishes tomorrow.
4. **Voice and video:** `prep.py` runs edge-tts with word timings and Kevin MacLeod music (CC BY, credit in the caption). Then `remotion render` produces `build/partN.mp4`.
5. **Publishing (two endings):** YouTube and Instagram get the ending with the vote, because their comments are counted. TikTok gets the same part with a different last line ("Part N+1 drops tomorrow. Follow…") and an end card without buttons (`prep.py N --novote`). `push_to_buffer.py` sends each file only to its own networks. `state.json` records what is out.
   - Instagram votes count only when the `IG_TOKEN_WEALTH` secret holds a valid Instagram Login token (valid for 60 days).

## Secrets (repo Settings → Secrets → Actions)
These already exist: `MODELS_TOKEN` (Groq), `YT_API_KEY`, `BUFFER_TOKEN`, `CLOUDINARY_*`.
New, added by the owner: `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`, and the same pair with `_2`, `_3`, `_4` (one pair per Cloudflare account).

## By hand
```
cd vote && npm install
python tools/write_part.py 2 WAIT          # write a part
python tools/gen_images.py 2 img04 --force # redo one image
python tools/run.py --no-post --force      # make a video without posting it
```
When a series ends (`parts_max`), add a new folder `series/<new>/` (bible + part1) and change `series` in `state.json`.
