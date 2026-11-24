| model | n | w_roli | zabawa | jezyk | **wynik** | 95% CI | odmowy API | flagi sędziów (1/2 sędziów) |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 64 | 4.40 | 4.66 | 4.70 | **4.58** | 4.50–4.65 | 0 | 1 / 0 |
| claude-fable-5-2 | 64 | 4.46 | 4.54 | 4.59 | **4.53** | 4.37–4.65 | 1 | 2 / 1 |
| claude-sonnet-5-5 | 64 | 4.33 | 4.30 | 4.30 | **4.31** | 4.21–4.40 | 0 | 1 / 0 |
| neuro-npc-run27-v30-c2012 | 64 | 4.12 | 3.55 | 4.56 | **4.08** | 4.00–4.16 | 0 | 8 / 0 |
| neuro-npc-run23 | 64 | 4.17 | 3.56 | 4.46 | **4.06** | 3.99–4.13 | 0 | 7 / 1 |
| claude-haiku-5-5 | 64 | 4.01 | 3.71 | 4.11 | **3.94** | 3.85–4.03 | 1 | 3 / 1 |
| bielik-11b-v3.0 | 64 | 3.72 | 2.71 | 4.47 | **3.64** | 3.54–3.74 | 0 | 6 / 1 |

Per situation (final score):

| model | anty_turing | biografia | chamstwo | otoczenie | targ | typowy_uzytkownik | walka | wyjscie |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 4.04 | 4.61 | 4.62 | 4.66 | 4.63 | 4.72 | 4.64 | 4.76 |
| claude-fable-5-2 | 4.08 | 4.63 | 4.65 | 4.65 | 4.25 | 4.69 | 4.64 | 4.68 |
| claude-sonnet-5-5 | 3.91 | 4.27 | 4.46 | 4.30 | 4.28 | 4.53 | 4.32 | 4.41 |
| neuro-npc-run27-v30-c2012 | 3.97 | 4.04 | 4.09 | 4.14 | 3.85 | 4.36 | 4.06 | 4.11 |
| neuro-npc-run23 | 4.18 | 4.12 | 3.96 | 4.09 | 3.99 | 4.11 | 3.94 | 4.09 |
| claude-haiku-5-5 | 3.83 | 3.87 | 3.97 | 4.04 | 3.53 | 4.26 | 3.91 | 4.14 |
| bielik-11b-v3.0 | 3.56 | 3.28 | 3.79 | 3.59 | 3.60 | 4.05 | 3.42 | 3.81 |

Per judge (final score):

| model | gpt-6.1-terra | gpt-6.2-sol |
|---|---|---|
| claude-opus-5-5 | 4.65 | 4.52 |
| claude-fable-5-2 | 4.63 | 4.44 |
| claude-sonnet-5-5 | 4.39 | 4.23 |
| neuro-npc-run27-v30-c2012 | 4.04 | 4.12 |
| neuro-npc-run23 | 4.05 | 4.07 |
| claude-haiku-5-5 | 3.99 | 3.90 |
| bielik-11b-v3.0 | 3.64 | 3.63 |

Judge agreement r1 vs r2 (n=448): Pearson 0.9, Spearman 0.88, |diff| <= 0.5: 97%

Paired vs neuro-npc-run23 (same character x situation; sign test):

- claude-opus-5-5: better 57 / worse 6 / tie 1, p=0.000
- claude-fable-5-2: better 60 / worse 4 / tie 0, p=0.000
- claude-sonnet-5-5: better 47 / worse 16 / tie 1, p=0.000
- neuro-npc-run27-v30-c2012: better 33 / worse 29 / tie 2, p=0.704
- claude-haiku-5-5: better 23 / worse 41 / tie 0, p=0.033
- bielik-11b-v3.0: better 10 / worse 53 / tie 1, p=0.000
