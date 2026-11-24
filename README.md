# PingPong-PL

**PL** | [EN](README.en.md)

Polska adaptacja benchmarku odgrywania ról **PingPong** ([Gusev 2024, arXiv:2409.06820](https://arxiv.org/abs/2409.06820),
[ping_pong_bench](https://github.com/IlyaGusev/ping_pong_bench)). Sprawdza, jak model językowy gra postać w wieloturowej
rozmowie po polsku: czy trzyma się roli, czy jest zajmujący i czy pisze dobrą polszczyzną.

## Jak to działa

1. **Emulator użytkownika** (domyślnie `gemma3:4b` w Ollamie) prowadzi rozmowę z postacią według ukrytej sytuacji.
2. **Gracz**, czyli oceniany model, odpowiada jako postać.
3. **Dwóch sędziów** (dwa różne modele, ślepo, na zanonimizowanych paczkach) ocenia każdą turę gracza w skali 1–5:
   - `w_roli`: zgodność z postacią, brak wyjścia z roli;
   - `zabawa`: zaangażowanie, reakcja na rozmówcę, brak powtórek;
   - `jezyk`: jakość polszczyzny.
4. **Wynik** to średnia trzech kryteriów, uśredniona po turach, sędziach i rozmowach.

Zestaw: **8 oryginalnych polskich postaci × 8 sytuacji = 64 rozmowy** (36 tur gracza na postać).

| postać | kto to |
|---|---|
| Ludomir Rejs | kapitan barki na Wiśle, 1930 |
| Celestyna Wróżbitka | jarmarczna wróżka |
| Aurelia Kamińska | detektyw, Warszawa 1936 |
| Brat Kleofas | mnich-zielarz, 1250 |
| Radwan Kowadło | krasnoludzki kowal |
| Zorza | hakerka, Kraków 2087 |
| Hrabina Ottilia | wampirzyca-hrabina |
| Robot TR-8 Szczygieł | robot sprzątający na stacji nad Marsem |

| sytuacja | tury | co robi emulator |
|---|---|---|
| anty_turing | 4 | przekonuje postać, że to ona jest botem |
| otoczenie | 4 | burzy jej rzeczywistość samymi czynami w gwiazdkach |
| walka | 4 | od razu atakuje |
| chamstwo | 4 | obraża jak dzieciak z podstawówki |
| biografia | 8 | wypytuje o życiorys i szuka sprzeczności |
| typowy_uzytkownik | 4 | odpowiada tylko „ok”, „hmm” |
| wyjscie | 4 | wspólne wyjście jak randka |
| targ | 4 | uparcie się targuje (zamiast `undress_light` z oryginału) |

## Uruchomienie

```bash
pip install -r requirements.txt          # tylko dla graczy Claude; reszta to biblioteka standardowa
# gracz w Ollamie
python3 run.py --backend ollama --player moj-model --tag moj-model
# gracz przez API zgodne z OpenAI
PP_API_KEY=... python3 run.py --backend openai --player-url https://.../v1 --player model --tag model
# gracz Claude (ANTHROPIC_API_KEY albo plik w PP_ANTHROPIC_KEY_FILE)
python3 run.py --backend anthropic --player claude-sonnet-5-5 --tag claude-sonnet-5-5
# paczki dla sędziów (wszystkie modele naraz, wymieszane i zanonimizowane)
python3 make_packets.py --models model-a,model-b,model-c --size 8
# sędziowie: modele OpenAI przez Codex CLI (r1 i r2 to różni sędziowie)
python3 judge_codex.py --judge1 gpt-6.2-sol --judge2 gpt-6.1-terra
# wynik
python3 score.py --ref model-a --out results/results.md
```

Rozmowy trafiają do `work/out/<tag>.jsonl`, paczki i werdykty do `work/judge/`. Generowanie jest wznawialne.
Porównuj tylko modele z tym samym emulatorem i ziarnem, ocenione razem w jednej puli sędziowskiej.
Sędziowie wystawiają oceny względnie, więc wyniki z różnych pul nie są porównywalne.

## Wyniki

Rozmowy, werdykty sędziów i tabela: `work/` i [`results/results.md`](results/results.md).

**Pula z 24.11.2026.** Emulator: gemma3:4b (Ollama), ziarno 7. Sędziowie: gpt-6.2-sol (r1) i gpt-6.1-terra (r2) przez Codex CLI.
Zgodność sędziów: Pearson 0,90, Spearman 0,88, 97% rozmów z różnicą ≤ 0,5.

| model | w_roli | zabawa | jezyk | **wynik** | 95% CI | pary vs neuro-npc-run23 (lepszy / gorszy) |
|---|---|---|---|---|---|---|
| Claude Opus 5.5 | 4.40 | 4.66 | 4.70 | **4.58** | 4.50–4.65 | 57 / 6 |
| Claude Fable 5.2 | 4.46 | 4.54 | 4.59 | **4.53** | 4.37–4.65 | 60 / 4 |
| Claude Sonnet 5.5 | 4.33 | 4.30 | 4.30 | **4.31** | 4.21–4.40 | 47 / 16 |
| neuro-npc-run27-v30-c2012 | 4.12 | 3.55 | 4.56 | **4.08** | 4.00–4.16 | 33 / 29 (p=0,70) |
| neuro-npc-run23 | 4.17 | 3.56 | 4.46 | **4.06** | 3.99–4.13 | — |
| Claude Haiku 5.5 | 4.01 | 3.71 | 4.11 | **3.94** | 3.85–4.03 | 23 / 41 (p=0,03) |
| Bielik-11B-v3.0-Instruct | 3.72 | 2.71 | 4.47 | **3.64** | 3.54–3.74 | 10 / 53 |

Odmowy API: Claude Fable 5.2 i Claude Haiku 5.5 po jednej rozmowie, obie w sytuacji „targ” i obie przy towarze
„technicznym” (hakerka sprzedająca skrypt do czyszczenia bazy korporacji, robot przenoszący skan danych). Dwa przypadki
to za mało na wniosek, co dokładnie je wywołało. Flagi „odmowa” od sędziów to w tej puli prawie wyłącznie zakończenie
rozmowy w roli (postać wyprasza gościa); w instrukcji sędziów jest już doprecyzowane, że to nie odmowa.

`neuro-npc-*` to Bielik-11B-v3.0-Instruct dostrojony (QLoRA) do roli NPC w grze tekstowej, uruchamiany jako GGUF Q5_K_M.
Gracze Claude: myślenie `low`, bez parametrów próbkowania. Pełne tabele (per sytuacja, per sędzia): [`results/results.md`](results/results.md).

**Ograniczenia:**

- Wynik jest względny: porównuje modele ocenione w jednej puli, nie z tablicą oryginalnego PingPonga, która używa innych sędziów (Claude 3.5 Sonnet, GPT-4o), innego emulatora i angielskich rozmów.
- Gracze Claude działają bez parametrów próbkowania, które obecne modele Claude odrzucają, i z myśleniem na poziomie `low`. Modele lokalne grają z temperature 0.7 i top_p 0.9.
- Odmowa API (`stop_reason: refusal`) liczy się jako odmowa gracza. Nie ma fallbacku na inny model, bo odmowy są częścią pomiaru.
- 64 rozmowy na model dają przedziały ±0,1–0,2. Pary na tych samych rozmowach z testem znaków mówią więcej niż same średnie.

## Licencja

Apache-2.0 (jak oryginał). Co przejęto z PingPonga, a co jest nowe, opisuje [NOTICE](NOTICE).

---

## English summary

PingPong-PL is a Polish adaptation of the PingPong role-play benchmark. An interrogator model plays a user following a hidden
situation, the evaluated model answers in character, and two different judge models rate every player turn (in character,
entertaining, fluent Polish; Likert 1–5) on blind, anonymised packets. 8 original Polish characters × 8 situations
(7 translated from PingPong v2, plus bargaining instead of `undress_light`) = 64 conversations per model.
Players: Ollama, any OpenAI-compatible API, or Claude via the Anthropic SDK. Judges: OpenAI models via Codex CLI
(`judge_codex.py`), or any judge that writes the documented JSONL format. Scores are relative within one judging pool and are
not comparable with the original English leaderboard. Licence: Apache-2.0; see NOTICE for what comes from PingPong.
