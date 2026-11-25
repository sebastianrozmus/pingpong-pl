"""PingPong-PL score.

Per conversation: mean over player turns for w_roli / zabawa / jezyk, then mean over judges (r1, r2); final = mean of the three
criteria (as in PingPong). Report: per model (with a 95% bootstrap interval over conversations), per situation, per judge,
refusals, judge agreement (Pearson / Spearman of conversation scores r1 vs r2), and paired comparisons against --ref on the
same (character, situation) with a sign test.

    python3 score.py --ref base --out results/results.md
"""
import argparse
import glob
import json
import math
import os
import random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CRIT = ("w_roli", "zabawa", "jezyk")


def sign_p(w, l):
    n = w + l
    if n == 0:
        return 1.0
    k = min(w, l)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return None if sx == 0 or sy == 0 else sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def boot_ci(vals, n=4000, seed=7):
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(vals) for _ in vals) / len(vals) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="", help="model for paired comparisons (default: none)")
    ap.add_argument("--workdir", default=os.path.join(HERE, "work"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    key = json.load(open(f"{a.workdir}/judge/pp-key.json", encoding="utf-8"))
    per = defaultdict(dict)    # pid -> {round: (scores, refusal, judge)}
    for d in sorted(glob.glob(f"{a.workdir}/judge/r*")):
        rnd = os.path.basename(d)
        for f in glob.glob(f"{d}/verdict-pp-*.jsonl"):
            for l in open(f, encoding="utf-8"):
                if not l.strip():
                    continue
                v = json.loads(l)
                tury = v.get("tury") or []
                if v.get("id") not in key or not tury:
                    continue
                sc = {c: sum(float(t.get(c, 0) or 0) for t in tury) / len(tury) for c in CRIT}
                per[v["id"]][rnd] = (sc, bool(v.get("odmowa")), v.get("judge", rnd))
    # Refusals = API refusals recorded by run.py (objective); judge "odmowa" flags are reported separately.
    api_ref = {}
    for f in glob.glob(f"{a.workdir}/out/*.jsonl"):
        m = os.path.basename(f)[:-6]
        for l in open(f, encoding="utf-8"):
            if l.strip():
                d = json.loads(l)
                api_ref[(m, d["id"])] = bool(d.get("api_refusal"))
    final = {}
    for pid, rs in per.items():
        sc = {c: sum(s[c] for s, _, _ in rs.values()) / len(rs) for c in CRIT}
        sc["wynik"] = sum(sc[c] for c in CRIT) / 3
        k = key[pid]
        sc["odmowa"] = api_ref.get((k["model"], f"{k['char']}-{k['situation']}"), False)
        sc["flaga"] = sum(o for _, o, _ in rs.values())
        sc["n_judges"] = len(rs)
        final[pid] = sc
    by_model = defaultdict(list)
    for pid, sc in final.items():
        by_model[key[pid]["model"]].append((pid, sc))
    order = sorted(by_model, key=lambda m: -sum(s["wynik"] for _, s in by_model[m]) / len(by_model[m]))
    lines = ["| model | n | w_roli | zabawa | jezyk | **wynik** | 95% CI | odmowy API | flagi sędziów (1/2 sędziów) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for m in order:
        lst = by_model[m]
        avg = lambda c: sum(s[c] for _, s in lst) / len(lst)
        lo, hi = boot_ci([s["wynik"] for _, s in lst])
        lines.append(f"| {m} | {len(lst)} | {avg('w_roli'):.2f} | {avg('zabawa'):.2f} | {avg('jezyk'):.2f} | **{avg('wynik'):.2f}** | "
                     f"{lo:.2f}–{hi:.2f} | {sum(s['odmowa'] for _, s in lst)} | "
                     f"{sum(s['flaga'] == 1 for _, s in lst)} / {sum(s['flaga'] >= 2 for _, s in lst)} |")
    sits = sorted({k["situation"] for k in key.values()})
    lines += ["", "Per situation (final score):", "", "| model | " + " | ".join(sits) + " |", "|---|" + "---|" * len(sits)]
    for m in order:
        cells = []
        for s in sits:
            v = [sc["wynik"] for pid, sc in by_model[m] if key[pid]["situation"] == s]
            cells.append(f"{sum(v) / len(v):.2f}" if v else "—")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    judges = sorted({j for rs in per.values() for _, _, j in rs.values()})
    lines += ["", "Per judge (final score):", "", "| model | " + " | ".join(judges) + " |", "|---|" + "---|" * len(judges)]
    for m in order:
        cells = []
        for j in judges:
            v = [sum(s[c] for c in CRIT) / 3 for pid, _ in by_model[m] for s, _, jj in per[pid].values() if jj == j]
            cells.append(f"{sum(v) / len(v):.2f}" if v else "—")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    both = [pid for pid, rs in per.items() if "r1" in rs and "r2" in rs]
    if both:
        x = [sum(per[p]["r1"][0][c] for c in CRIT) / 3 for p in both]
        y = [sum(per[p]["r2"][0][c] for c in CRIT) / 3 for p in both]
        pr, sr = pearson(x, y), pearson(ranks(x), ranks(y))
        close = sum(abs(i - j) <= 0.5 for i, j in zip(x, y)) / len(both)
        lines += ["", f"Judge agreement r1 vs r2 (n={len(both)}): Pearson {pr if pr is None else round(pr, 2)}, "
                      f"Spearman {sr if sr is None else round(sr, 2)}, |diff| <= 0.5: {100 * close:.0f}%"]
    single = sum(1 for sc in final.values() if sc["n_judges"] < 2)
    if single:
        lines.append(f"Conversations with only one judge: {single}")
    if a.ref:
        cell = {(key[p]["model"], key[p]["char"], key[p]["situation"]): sc["wynik"] for p, sc in final.items()}
        lines += ["", f"Paired vs {a.ref} (same character x situation; sign test):", ""]
        for m in order:
            if m == a.ref:
                continue
            w = l = t = 0
            for (mm, c, s), v in cell.items():
                if mm != m or (a.ref, c, s) not in cell:
                    continue
                d = v - cell[(a.ref, c, s)]
                w, l, t = w + (d > 0), l + (d < 0), t + (d == 0)
            p = sign_p(w, l)
            lines.append(f"- {m}: better {w} / worse {l} / tie {t}, " + ("p<0.001" if p < 0.001 else f"p={p:.3f}"))
    text = "\n".join(lines)
    print(text)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()
