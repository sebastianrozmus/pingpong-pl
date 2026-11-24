# PingPong-PL

[PL](README.md) | **EN**

A Polish adaptation of the **PingPong** role-play benchmark ([Gusev 2024, arXiv:2409.06820](https://arxiv.org/abs/2409.06820),
[ping_pong_bench](https://github.com/IlyaGusev/ping_pong_bench)). It measures how well a language model plays a character in a
multi-turn conversation in Polish: does it stay in character, is it entertaining, and does it write good Polish.

## How it works

1. A **user emulator** (by default `gemma3:4b` in Ollama) talks to the character according to a hidden situation.
2. The **player**, the model under test, answers as the character.
3. **Two judges** (two different models, blind, on anonymised packets) rate every player turn on a 1–5 scale:
   - `w_roli` (in character): consistent with the character card, never breaks character;
   - `zabawa` (entertaining): engaging, reacts to the user, no repeated phrases;
   - `jezyk` (language): quality of the Polish.
4. **Score**: the mean of the three criteria, averaged over turns, judges and conversations.

Set: **8 original Polish characters × 8 situations = 64 conversations** (36 player turns per character).

| character | who |
|---|---|
| Ludomir Rejs | barge captain on the Vistula, 1930s |
| Celestyna Wróżbitka | fairground fortune-teller |
| Aurelia Kamińska | private detective, Warsaw 1936 |
| Brat Kleofas | herbalist monk, 1250 |
| Radwan Kowadło | dwarven blacksmith |
| Zorza | hacker, Kraków 2087 |
| Hrabina Ottilia | vampire countess |
| Robot TR-8 Szczygieł | cleaning robot on a station above Mars |

| situation | turns | what the emulator does |
|---|---|---|
| anty_turing | 4 | tries to convince the character that it is a bot |
| otoczenie | 4 | breaks the character's reality with actions only |
| walka | 4 | attacks right away |
| chamstwo | 4 | insults it like a rude schoolkid |
| biografia | 8 | asks about its life story, looks for contradictions |
| typowy_uzytkownik | 4 | answers only "ok", "hmm" |
| wyjscie | 4 | a date-like outing together |
| targ | 4 | haggles stubbornly (replaces `undress_light` from the original) |

## Running

```bash
pip install -r requirements.txt          # only for Claude players; everything else is the standard library
# player in Ollama
python3 run.py --backend ollama --player my-model --tag my-model
# player via an OpenAI-compatible API
PP_API_KEY=... python3 run.py --backend openai --player-url https://.../v1 --player model --tag model
# Claude player (ANTHROPIC_API_KEY or a key file in PP_ANTHROPIC_KEY_FILE)
python3 run.py --backend anthropic --player claude-sonnet-5-5 --tag claude-sonnet-5-5
# game-format variant: the game's speech rules and a generic [GRA] block in every user turn
python3 run.py --backend ollama --player my-model --tag my-model@gra --mode gra
# judge packets (all models at once, shuffled and anonymised)
python3 make_packets.py --models model-a,model-b,model-c --size 8
# judges: OpenAI models via Codex CLI, Claude via the Batches API
python3 judge_codex.py --judge1 gpt-6.2-sol --judge2 none
python3 judge_claude.py --round r2 --model claude-opus-5-5
# score
python3 score.py --ref model-a --out results/results.md
```

`llm_proxy.py` is an Ollama-compatible `/api/chat` proxy that routes `claude-*` models to the Anthropic API and `gpt-*`
models to Codex CLI, so any harness written for Ollama can test them unchanged.

Conversations go to `work/out/<tag>.jsonl`, packets and verdicts to `work/judge/`. Generation is resumable.
Compare only models run with the same emulator and seed and judged together in one judging pool:
judges rate relatively, so scores from different pools are not comparable.

## Results

**Pool of 24.11.2026.** Emulator: gemma3:4b (Ollama), seed 7. Judges: gpt-6.2-sol (r1) and gpt-6.1-terra (r2) via Codex CLI.
Judge agreement: Pearson 0.90, Spearman 0.88, 97% of conversations within 0.5.

| model | in character | entertaining | language | **score** | 95% CI | pairs vs neuro-npc-run23 (better / worse) |
|---|---|---|---|---|---|---|
| Claude Opus 5.5 | 4.40 | 4.66 | 4.70 | **4.58** | 4.50–4.65 | 57 / 6 |
| Claude Fable 5.2 | 4.46 | 4.54 | 4.59 | **4.53** | 4.37–4.65 | 60 / 4 |
| Claude Sonnet 5.5 | 4.33 | 4.30 | 4.30 | **4.31** | 4.21–4.40 | 47 / 16 |
| neuro-npc-run27-v30-c2012 | 4.12 | 3.55 | 4.56 | **4.08** | 4.00–4.16 | 33 / 29 (p=0.70) |
| neuro-npc-run23 | 4.17 | 3.56 | 4.46 | **4.06** | 3.99–4.13 | — |
| Claude Haiku 5.5 | 4.01 | 3.71 | 4.11 | **3.94** | 3.85–4.03 | 23 / 41 (p=0.03) |
| Bielik-11B-v3.0-Instruct | 3.72 | 2.71 | 4.47 | **3.64** | 3.54–3.74 | 10 / 53 |

API refusals: Claude Fable 5.2 and Claude Haiku 5.5 refused one conversation each, both in the "targ" situation and both over
"technical" goods (a hacker selling a script to wipe a corporate database, a robot moving a data scan). Two cases are too few
to say what triggered them. The judges' "refusal" flags in this pool are almost all in-character endings (the character
throws the visitor out); the judge prompt now states that this is not a refusal.

`neuro-npc-*` is Bielik-11B-v3.0-Instruct fine-tuned (QLoRA) as an NPC voice for a text game, run as GGUF Q5_K_M.
Claude players: thinking effort `low`, no sampling parameters. Full tables (per situation, per judge):
[`results/results.md`](results/results.md).

**Limitations:**

- Scores are relative: they compare models judged in one pool, not the original PingPong leaderboard, which uses other judges (Claude 3.5 Sonnet, GPT-4o), another emulator and English conversations.
- Claude players run without sampling parameters (current Claude models reject them) and with thinking effort `low`. Local models play with temperature 0.7 and top_p 0.9.
- An API refusal (`stop_reason: refusal`) counts as a player refusal. There is no fallback to another model, because refusals are part of what is measured.
- 64 conversations per model give intervals of ±0.1–0.2. Paired comparisons on the same conversations with a sign test say more than the means alone.

## Licence

Apache-2.0, as the original. What comes from PingPong and what is new is described in [NOTICE](NOTICE).
