# -*- coding: utf-8 -*-
"""Oprava naplanovaneho dielu v Buffri (20.10.: repost dostal edge hlas, IG zlyhal na prvom komentari).
    python vote/tools/buffer_fix.py N VIDEO_URL
YT prispevok dielu N: vymeni video za VIDEO_URL, cas necha. IG: ak diel nema naplanovany reel, vytvori ho
na rovnaky cas (bez prveho komentara). Nic nemaze."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import push_to_buffer as pb  # noqa: E402

n, url = int(sys.argv[1]), sys.argv[2]
tok = os.environ["BUFFER_TOKEN"]
want = {c["service"]: c["id"] for c in json.load(open("config.example.json"))["buffer_channels"]}
orgs = [o["id"] for o in pb.gql(tok, "query { account { organizations { id } } }")["account"]["organizations"]]
Q = """query($i: PostsInput!) { posts(first: 50, input: $i) { edges { node {
  id status dueAt text channelId assets { source }
  metadata { ... on YoutubePostMetadata { title } ... on InstagramPostMetadata { type firstComment } } } } } }"""
EDIT = """mutation($i: EditPostInput!) { editPost(input: $i) {
  ... on PostActionSuccess { post { id dueAt status assets { source } } } ... on MutationError { message } } }"""
CREATE = """mutation($i: CreatePostInput!) { createPost(input: $i) {
  ... on PostActionSuccess { post { id dueAt status } } ... on MutationError { message } } }"""


def posts(channel):
    out = []
    for o in orgs:
        res = pb.gql(tok, Q, {"i": {"organizationId": o, "filter": {"channelIds": [channel], "status": ["scheduled", "error"]}}})
        out += [e["node"] for e in res["posts"]["edges"] or []]
    return [p for p in out if f"Part {n}:" in p["text"] or f"Part {n}:" in json.dumps(p.get("metadata") or {})
            or any(f"part{n:02d}" in a["source"] for a in p["assets"])]


if url == "draft":   # user 20.10.: "zrus to, vyjde az ked to bude hotove" -> naspat do konceptov, nic sa nemaze
    for ch in ("youtube", "instagram"):
        for p in posts(want[ch]):
            if p["status"] == "scheduled":
                meta = ({"youtube": {"title": p["metadata"]["title"], "categoryId": pb.YT_CATEGORY, "privacy": "public"}}
                        if ch == "youtube" else {"instagram": {"type": "reel", "shouldShareToFeed": True}})
                print(ch, p["id"], pb.gql(tok, EDIT, {"i": {"id": p["id"], "saveToDraft": True, "text": p["text"],
                                                            "assets": [{"video": {"url": a["source"]}} for a in p["assets"]],
                                                            "metadata": meta}})["editPost"])
    sys.exit(0)

yt = posts(want["youtube"])
print("YT:", [(p["id"], p["status"], p["dueAt"], [a["source"][-60:] for a in p["assets"]]) for p in yt])
if len(yt) != 1:
    sys.exit("YT: cakal som presne 1 prispevok dielu - nic nemenim")
p = yt[0]
res = pb.gql(tok, EDIT, {"i": {"id": p["id"], "text": p["text"], "assets": [{"video": {"url": url}}],
                              "metadata": {"youtube": {"title": p["metadata"]["title"], "categoryId": pb.YT_CATEGORY,
                                                       "privacy": "public"}}}})["editPost"]
print("YT edit:", res)
if res.get("message"):
    sys.exit(1)

ig = posts(want["instagram"])
print("IG:", [(x["id"], x["status"], x["dueAt"]) for x in ig])
if not any(x["status"] == "scheduled" for x in ig):
    res = pb.gql(tok, CREATE, {"i": {"channelId": want["instagram"], "text": p["text"], "schedulingType": "automatic",
                                     "mode": "customScheduled", "dueAt": p["dueAt"], "assets": [{"video": {"url": url}}],
                                     "metadata": {"instagram": {"type": "reel", "shouldShareToFeed": True}}}})["createPost"]
    print("IG create:", res)
    if res.get("message"):
        sys.exit(1)
    d = json.load(open(pb.PUSHED, encoding="utf-8"))
    name = f"suddenly-rich-part{n:02d}.mp4"
    d[name] = sorted(set(d.get(name, [])) | {"instagram"})
    pb.save_pushed(d)
