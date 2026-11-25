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

**Pool of 24.11.2026:** 11 models × 2 variants = 1408 conversations. Emulator gemma3:4b (Ollama), seed 7.
Every conversation has two judges from different families: gpt-6.2-sol (via Codex CLI) and Claude Opus 5.5 (Batches API).
The **general** variant uses the PingPong prompt. The **@gra** variant uses a text-game character card (speech rules: at most 3
sentences, no asterisks, a mood tag) and a generic `[GRA]` block in every turn, with no concrete game-engine decisions.

| model | general | @gra | Δ | entertaining: general → @gra |
|---|---|---|---|---|
| Claude Opus 5.5 | **4.64** | 4.57 | −0.07 | 4.70 → 4.58 |
| GPT-6.2 sol | 4.57 | 4.54 | −0.03 | 4.22 → 4.31 |
| Claude Fable 5.2 | 4.56 | 4.55 | −0.01 | 4.57 → 4.48 |
| GPT-6.1 terra | 4.37 | 4.45 | +0.08 | 3.78 → 3.97 |
| Claude Sonnet 5.5 | 4.31 | 4.37 | +0.06 | 4.29 → 4.23 |
| GPT-6 luna | 4.21 | 4.35 | +0.14 | 3.68 → 4.01 |
| neuro-npc-run27-v31-c2012 | 3.97 | 3.85 | −0.12 | 3.41 → 3.19 |
| neuro-npc-run27-v30-c2012 | 3.96 | 3.84 | −0.12 | 3.48 → 3.19 |
| neuro-npc-run23 | 3.95 | 3.81 | −0.14 | 3.53 → 3.21 |
| Claude Haiku 5.5 | 3.87 | 4.01 | +0.14 | 3.68 → 3.72 |
| Bielik-11B-v3.0-Instruct | 3.40 | 3.57 | +0.17 | 2.61 → 2.87 |

`neuro-npc-*` is Bielik-11B-v3.0/v3.1-Instruct fine-tuned (QLoRA, ~10k conversations) as an NPC voice for a text game (GGUF Q5_K_M).
Full tables (criteria, intervals, situations, judges, pairs): [`results/results.md`](results/results.md).

**Takeaways:**

- **The top six are statistically indistinguishable.** Each judge rates its own family higher, by about 0.25–0.35.
  The Claude judge gives Opus 4.76 and GPT-6.2 sol 4.45; the GPT judge gives them 4.51 and 4.69. Do not read the top order literally.
- **Fine-tuning helps a lot: +0.56 over bare Bielik v3.0.** The tuned 11B model is on par with Claude Haiku 5.5 (slightly above it in the
  general variant). Its strongest side is Polish; its weakest is "entertaining".
- **The @gra variant separates length from quality.** Top models barely lose when their replies shrink from 750–1040 to about 260–320
  characters with no gestures, so their lead is not about length. The game rules help weaker and untuned models (Bielik +0.17,
  Haiku and luna +0.14). The game-tuned models lose on "entertaining": a generic `[GRA]` with no engine decision gives them little material.
- **API refusals:** Claude Fable 5.2 and Claude Haiku 5.5 refused one conversation each, both in the "targ" situation and both over
  "technical" goods (a script to wipe a corporate database, moving a data scan). Two cases are too few to say what triggered them.

**Limitations:**

- Scores are relative: they compare models judged in one pool, not the original PingPong leaderboard, which uses other judges (Claude 3.5 Sonnet, GPT-4o), another emulator and English conversations.
- Claude players run without sampling parameters (current Claude models reject them) and with thinking effort `low`. Local models play with temperature 0.7 and top_p 0.9.
- An API refusal (`stop_reason: refusal`) counts as a player refusal. There is no fallback to another model, because refusals are part of what is measured.
- 64 conversations per model give intervals of ±0.1–0.2. Paired comparisons on the same conversations with a sign test say more than the means alone. The intervals do not include judge, emulator or seed variance.
- The judges belong to the families of the models they rate (see the own-family preference above). The next edition will add a judge from outside both families and a human rating on a sample.
- GPT models played through Codex CLI with replaced instructions (`model_instructions_file`), not through a plain API. One emulator (gemma3:4b) and one seed. 8 conversations have only one judge.

## Licence

Apache-2.0, as the original. What comes from PingPong and what is new is described in [NOTICE](NOTICE).
