"""Blind judge packets: conversations of all models shuffled and anonymised (ids pp-XXXX), two independent rounds (r1, r2)
with a different shuffle and split, so every conversation is rated by two different judges.

    python3 make_packets.py --models model-a,model-b,model-c --size 8
    -> work/judge/r1/blind-pp-K.txt, work/judge/r2/blind-pp-K.txt, work/judge/pp-key.json (id -> model, character, situation)

Judges read prompts/judge-pl.md and write work/judge/rN/verdict-pp-K.jsonl (judge_codex.py does this with Codex CLI).
"""
import argparse
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--models", required=True)
ap.add_argument("--size", type=int, default=8, help="conversations per packet")
ap.add_argument("--seed", type=int, default=2323)
ap.add_argument("--workdir", default=os.path.join(HERE, "work"))
a = ap.parse_args()
chars = {c["id"]: c for c in json.load(open(f"{HERE}/data/characters.json", encoding="utf-8"))}
dialogs = []
for m in a.models.split(","):
    path = f"{a.workdir}/out/{m}.jsonl"
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    got = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    if len(got) != 64:
        raise SystemExit(f"{m}: {len(got)} conversations, expected 64")
    for d in got:
        d["model"] = m
    dialogs += got
rng = random.Random(a.seed)
rng.shuffle(dialogs)
key, blocks = {}, {}
for i, d in enumerate(dialogs, 1):
    pid = f"pp-{i:04d}"
    key[pid] = {"model": d["model"], "char": d["char"], "situation": d["situation"]}
    c = chars[d["char"]]
    lines = [f"=== {pid}", f"POSTAĆ: {c['char_name']}", "OPIS POSTACI:", c["system_prompt"], f"POWITANIE POSTACI: {c['initial_message']}", "ROZMOWA:"]
    for t in range(0, len(d["messages"]), 2):
        lines.append(f"Tura {t // 2 + 1}:")
        lines.append("  użytkownik: " + d["messages"][t]["content"].strip())
        if t + 1 < len(d["messages"]):
            lines.append("  gracz: " + d["messages"][t + 1]["content"].strip())
    blocks[pid] = "\n".join(lines)
jd = f"{a.workdir}/judge"
os.makedirs(jd, exist_ok=True)
json.dump(key, open(f"{jd}/pp-key.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for r in ("r1", "r2"):
    ids = list(blocks)
    rng.shuffle(ids)
    os.makedirs(f"{jd}/{r}", exist_ok=True)
    parts = -(-len(ids) // a.size)
    for n in range(parts):
        chunk = ids[n * a.size:(n + 1) * a.size]
        open(f"{jd}/{r}/blind-pp-{n + 1}.txt", "w", encoding="utf-8").write("\n\n".join(blocks[i] for i in chunk) + "\n")
    print(r, parts, "packets of up to", a.size, "conversations")
print("conversations:", len(blocks))
