"""Obrazok cez Cloudflare Workers AI (FLUX.2 klein) - zadarmo v dennom limite.
Pouzitie: python tools/cf_image.py "prompt alebo @subor.txt" out.jpg [ref1.jpg ref2.jpg ...]
Kluce z prostredia alebo z FactoryAnim/.env (nikdy sa nevypisuju):
  CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID          - ucet 1
  CLOUDFLARE_API_TOKEN_2, CLOUDFLARE_ACCOUNT_ID_2 ...  - dalsie ucty (ked je denny limit minuty, ide sa na dalsi)
Ak ACCOUNT_ID chyba, zisti sa cez API z tokenu."""
import base64, json, os, sys, time, urllib.request, uuid
from pathlib import Path

MODEL = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")
API = "https://api.cloudflare.com/client/v4"


class LimitReached(Exception):
    pass


def _vals():
    vals = {}
    for p in (Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    vals.setdefault(k.strip(), v.strip().strip('"'))
    return lambda k: os.environ.get(k) or vals.get(k, "")


def _account_id(tok):
    req = urllib.request.Request(f"{API}/accounts", headers={"Authorization": f"Bearer {tok}"})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=30).read()).get("result") or []
    except urllib.error.HTTPError:
        res = []
    return res[0]["id"] if res else ""


def accounts():
    get = _vals()
    out = []
    for suf in [""] + [f"_{i}" for i in range(2, 10)]:
        tok = get("CLOUDFLARE_API_TOKEN" + suf)
        if not tok:
            continue
        acc = get("CLOUDFLARE_ACCOUNT_ID" + suf) or _account_id(tok)
        if acc:
            out.append((suf or "_1", acc, tok))
        else:
            print(f"ucet{suf}: chyba CLOUDFLARE_ACCOUNT_ID{suf} (token nema pravo citat ucet)", file=sys.stderr)
    if not out:
        sys.exit("Chyba CLOUDFLARE_API_TOKEN (+ CLOUDFLARE_ACCOUNT_ID) v .env / prostredi")
    return out


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, path in files.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{Path(path).name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
        out += Path(path).read_bytes() + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def _run(acc, tok, body, ctype):
    req = urllib.request.Request(f"{API}/accounts/{acc}/ai/run/{MODEL}", data=body,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": ctype})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=180).read())
    except urllib.error.HTTPError as e:
        msg = e.read()[:400].decode(errors="replace")
        if e.code == 429 and "4006" in msg:
            raise LimitReached(msg)
        raise RuntimeError(f"HTTP {e.code}: {msg}")


_dead = set()


def generate(prompt, out, refs=(), width=576, height=1024, seed=42):
    body, ctype = multipart({"prompt": prompt, "width": width, "height": height, "seed": seed},
                            {f"input_image_{i}": r for i, r in enumerate(refs[:4])})
    for name, acc, tok in accounts():
        if name in _dead:
            continue
        try:
            try:
                data = _run(acc, tok, body, ctype)
            except RuntimeError as e:  # 5xx / docasna chyba -> 1x znova
                print(f"ucet{name}: {str(e)[:200]} -> opakujem", file=sys.stderr)
                time.sleep(8)
                data = _run(acc, tok, body, ctype)
        except LimitReached:
            _dead.add(name)
            print(f"ucet{name}: denny limit minuty, skusam dalsi", file=sys.stderr)
            continue
        img = (data.get("result") or {}).get("image")
        if not img:
            raise RuntimeError(f"Bez obrazka: {str(data)[:400]}")
        Path(out).write_bytes(base64.b64decode(img))
        return out
    raise LimitReached("Vsetky ucty maju dnes minuty denny limit (reset 00:00 UTC)")


if __name__ == "__main__":
    p = sys.argv[1]
    if p.startswith("@"):
        p = Path(p[1:]).read_text(encoding="utf-8").strip()
    print(generate(p, sys.argv[2], sys.argv[3:]))
