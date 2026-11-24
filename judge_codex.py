"""Judge PingPong-PL packets with OpenAI models through Codex CLI (`codex exec`, no tools, read-only sandbox).

Round r1 is judged by --judge1, round r2 by --judge2 (two different judge models, as in PingPong v2).
Each verdict is validated: every conversation id of the packet present once, one score triple per player turn, scores 1-5.
Invalid output is retried (--retries). Resumable: valid verdict files are kept.

    python3 judge_codex.py --judge1 gpt-6.2-sol --judge2 gpt-6.1-terra --workers 4
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CODEX = os.environ.get("CODEX_BIN", os.path.expanduser("~/.local/bin/codex"))
CRIT = ("w_roli", "zabawa", "jezyk")


def expected(packet_text):
    """id -> number of player turns in the packet."""
    exp, cur = {}, None
    for line in packet_text.splitlines():
        m = re.match(r"=== (pp-\d+)", line)
        if m:
            cur = m.group(1)
            exp[cur] = 0
        elif cur and line.startswith("  gracz:"):
            exp[cur] += 1
    return exp


def parse(text, exp):
    got = {}
    for line in text.splitlines():
        line = line.strip().strip("`")
        if not line.startswith("{"):
            continue
        try:
            v = json.loads(line)
        except ValueError:
            continue
        pid = v.get("id")
        if pid not in exp or pid in got:
            continue
        tury = v.get("tury") or []
        ok = len(tury) == exp[pid] and all(
            isinstance(t.get(c), (int, float)) and 1 <= t[c] <= 5 for t in tury for c in CRIT)
        if ok:
            got[pid] = v
    missing = [p for p in exp if p not in got]
    return [got[p] for p in exp if p in got], missing


def judge_one(packet, model, effort, retries):
    out = packet.replace("blind-pp-", "verdict-pp-").replace(".txt", ".jsonl")
    text = open(packet, encoding="utf-8").read()
    exp = expected(text)
    if os.path.exists(out):
        _, missing = parse(open(out, encoding="utf-8").read(), exp)
        if not missing:
            return out, "kept"
    prompt = open(f"{HERE}/prompts/judge-pl.md", encoding="utf-8").read() + "\n\n===== ROZMOWY DO OCENY =====\n\n" + text
    last = ""
    for attempt in range(retries + 1):
        with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as tf:
            res_path = tf.name
        cmd = [CODEX, "exec", "-m", model, "-c", f"model_reasoning_effort={effort}", "-c", "features.code_mode_host=false",
               "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "--color", "never", "-o", res_path, "-"]
        p = subprocess.run(cmd, input=prompt, text=True, capture_output=True, timeout=1800)
        res = open(res_path, encoding="utf-8").read() if os.path.exists(res_path) else ""
        os.unlink(res_path)
        verdicts, missing = parse(res, exp)
        if not missing:
            with open(out, "w", encoding="utf-8") as fh:
                for v in verdicts:
                    v["judge"] = model
                    fh.write(json.dumps(v, ensure_ascii=False) + "\n")
            return out, f"ok (attempt {attempt + 1})"
        last = f"exit {p.returncode}, missing {len(missing)}/{len(exp)}: {p.stderr[-300:]}"
    return out, "FAILED " + last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge1", required=True, help="judge model for round r1")
    ap.add_argument("--judge2", required=True, help="judge model for round r2")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--workdir", default=os.path.join(HERE, "work"))
    a = ap.parse_args()
    jobs = [(p, a.judge1) for p in sorted(glob.glob(f"{a.workdir}/judge/r1/blind-pp-*.txt"))]
    if a.judge2 != "none":   # "none": round r2 is judged elsewhere (e.g. judge_claude.py)
        jobs += [(p, a.judge2) for p in sorted(glob.glob(f"{a.workdir}/judge/r2/blind-pp-*.txt"))]
    bad = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(judge_one, p, m, a.effort, a.retries): p for p, m in jobs}
        for f in cf.as_completed(futs):
            out, status = f.result()
            bad += status.startswith("FAILED")
            print(os.path.relpath(out, a.workdir), status, flush=True)
    print(f"done: {len(jobs)} packets, failed {bad}")


if __name__ == "__main__":
    main()
