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

**Pula z 24.11.2026:** 11 modeli × 2 warianty = 1408 rozmów. Emulator gemma3:4b (Ollama), ziarno 7.
Na każdą rozmowę jest dwóch sędziów z różnych rodzin: gpt-6.2-sol (przez Codex CLI) i Claude Opus 5.5 (Batches API).
Wariant **ogólny** to prompt PingPonga. Wariant **@gra** to karta postaci w formacie gry tekstowej (zasady mowy: najwyżej 3 zdania,
bez gwiazdek, znacznik nastroju) i ogólny blok `[GRA]` w każdej turze, bez konkretnych decyzji silnika gry.

| model | ogólny | @gra | Δ | zabawa: ogólny → @gra |
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

`neuro-npc-*` to Bielik-11B-v3.0/v3.1-Instruct dostrojony (QLoRA, ~10 tys. rozmów) do roli NPC w grze tekstowej (GGUF Q5_K_M).
Pełne tabele (kryteria, przedziały, sytuacje, sędziowie, pary): [`results/results.md`](results/results.md).

**Co z tego wynika:**

- **Pierwsza szóstka jest statystycznie nierozróżnialna.** Każdy sędzia stawia wyżej modele własnej rodziny, o około 0,25–0,35.
  Sędzia Claude daje Opusowi 4.76, a GPT-6.2 sol 4.45. Sędzia GPT daje im odpowiednio 4.51 i 4.69. Kolejności w czołówce nie należy czytać dosłownie.
- **Dostrojenie daje dużo: +0,56 nad gołym Bielikiem v3.0.** Dostrojony 11B jest na poziomie Claude Haiku 5.5 (w wariancie ogólnym nieco wyżej).
  Najmocniejszą stroną jest polszczyzna, najsłabszą „zabawa”.
- **Wariant @gra rozdziela długość od jakości.** Modele czołowe po skróceniu odpowiedzi z 750–1040 do około 260–320 znaków i bez gestów prawie nie tracą.
  Ich przewaga nie wynika więc z długości. Zasady gry pomagają modelom słabszym i niedostrojonym (Bielik +0.17, Haiku i luna +0.14).
  Dostrojonym modelom gry ogólny `[GRA]` bez decyzji silnika odbiera materiał, więc tracą na „zabawie”.
- **Odmowy API:** Claude Fable 5.2 i Claude Haiku 5.5 odmówiły po jednej rozmowie, obie w sytuacji „targ” i obie przy towarze „technicznym”
  (skrypt do czyszczenia bazy korporacji, przenoszenie skanu danych). Dwa przypadki to za mało na wniosek, co je wywołało.

**Ograniczenia:**

- Wynik jest względny: porównuje modele ocenione w jednej puli, nie z tablicą oryginalnego PingPonga, która używa innych sędziów (Claude 3.5 Sonnet, GPT-4o), innego emulatora i angielskich rozmów.
- Gracze Claude działają bez parametrów próbkowania, które obecne modele Claude odrzucają, i z myśleniem na poziomie `low`. Modele lokalne grają z temperature 0.7 i top_p 0.9.
- Odmowa API (`stop_reason: refusal`) liczy się jako odmowa gracza. Nie ma fallbacku na inny model, bo odmowy są częścią pomiaru.
- 64 rozmowy na model dają przedziały ±0,1–0,2. Pary na tych samych rozmowach z testem znaków mówią więcej niż same średnie. Przedziały nie obejmują wariancji sędziów, emulatora ani ziarna.
- Sędziowie należą do rodzin ocenianych modeli (patrz wyżej: preferencja własnej rodziny). W kolejnej edycji planujemy sędziego spoza obu rodzin i ocenę ludzką na próbce.
- Modele GPT grały przez Codex CLI z podmienionymi instrukcjami (`model_instructions_file`), a nie przez czyste API. Jeden emulator (gemma3:4b) i jedno ziarno. 8 rozmów ma tylko jednego sędziego.

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
