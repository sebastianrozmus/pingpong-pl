"""Judge PingPong-PL packets of one round with a Claude model through the Message Batches API (50% price).
Same prompt (prompts/judge-pl.md) and the same validation as judge_codex.py; packets that fail validation are retried
with plain requests. Resumable: valid verdict files are kept.

    PP_ANTHROPIC_KEY_FILE=~/.anthropic-key python3 judge_claude.py --round r2 --model claude-opus-5-5
"""
import argparse
import glob
import json
import os
import time

from judge_codex import expected, parse

HERE = os.path.dirname(os.path.abspath(__file__))


def client():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY")
    kf = os.environ.get("PP_ANTHROPIC_KEY_FILE")
    if not key and kf:
        key = open(kf, encoding="utf-8").read().strip()
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def params(model, effort, system, text):
    return {"model": model, "max_tokens": 16000, "system": system, "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": "===== ROZMOWY DO OCENY =====\n\n" + text}]}


def save(out, verdicts, model):
    with open(out, "w", encoding="utf-8") as fh:
        for v in verdicts:
            v["judge"] = model
            fh.write(json.dumps(v, ensure_ascii=False) + "\n")


def main():
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--workdir", default=os.path.join(HERE, "work"))
    a = ap.parse_args()
    system = open(f"{HERE}/prompts/judge-pl.md", encoding="utf-8").read()
    c = client()
    todo = {}
    for p in sorted(glob.glob(f"{a.workdir}/judge/{a.round}/blind-pp-*.txt")):
        out = p.replace("blind-pp-", "verdict-pp-").replace(".txt", ".jsonl")
        text = open(p, encoding="utf-8").read()
        exp = expected(text)
        if os.path.exists(out) and not parse(open(out, encoding="utf-8").read(), exp)[1]:
            continue
        todo[os.path.basename(p)[:-4]] = (out, text, exp)
    print(f"{a.round}: {len(todo)} packets to judge", flush=True)
    if not todo:
        return
    batch = c.messages.batches.create(requests=[
        Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**params(a.model, a.effort, system, text)))
        for cid, (_, text, _) in todo.items()])
    print("batch", batch.id, flush=True)
    while c.messages.batches.retrieve(batch.id).processing_status != "ended":
        time.sleep(60)
    failed = []
    for res in c.messages.batches.results(batch.id):
        out, text, exp = todo[res.custom_id]
        if res.result.type == "succeeded":
            msg = res.result.message
            verdicts, missing = parse("".join(b.text for b in msg.content if b.type == "text"), exp)
            if not missing:
                save(out, verdicts, a.model)
                continue
        failed.append(res.custom_id)
    for cid in failed:   # retry with plain requests
        out, text, exp = todo[cid]
        for _ in range(2):
            msg = c.messages.create(**params(a.model, a.effort, system, text))
            verdicts, missing = parse("".join(b.text for b in msg.content if b.type == "text"), exp)
            if not missing:
                save(out, verdicts, a.model)
                break
        else:
            print("FAILED", cid, flush=True)
    print(f"{a.round}: done, retried {len(failed)}", flush=True)


if __name__ == "__main__":
    main()
