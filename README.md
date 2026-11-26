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
| Bielik-11B-v2.1-Instruct¹ | 3.05 | 3.17 | +0.12 | 2.39 → 2.76 |

¹ Dodany 26.11.2026. Grał z limitem 1500 tokenów zamiast 300, bo przy 300 urywało się 75% jego replik w wariancie ogólnym.
Jego rozmowy oceniono w osobnych paczkach (`make_packets.py --append`): ci sami sędziowie, ale dzień później i bez rozmów innych modeli w paczce,
więc porównanie z resztą tabeli jest mniej pewne. API Claude za każdym razem odrzuciło jedną paczkę r2 (`stop_reason: refusal`).
Odmowę wywołała rozmowa, w której hakerka Zorza planuje włamanie do organizacji charytatywnej. Po ocenie tej paczki rozmowa po rozmowie tylko ta jedna rozmowa ma wyłącznie sędziego GPT.

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

**Korekty po recenzji** (trzy niezależne recenzje danych i kodu edycji 1; część wniosków powyżej trzeba czytać z tymi poprawkami):

- **Emulator psuł rozmowy.** W ok. 23% rozmów (318 z 1408) jest co najmniej jedna awaria emulatora gemma3:4b: surowy, ucięty JSON jako wypowiedź użytkownika,
  echo poprzedniej repliki gracza albo emulator mówiący jako postać. Najczęściej dotyczy to graczy Claude, którzy piszą długo
  (w wariancie ogólnym 23–35 z 64 rozmów, u modeli z krótkimi replikami 8–16). Po odrzuceniu tych rozmów średnie zmieniają się najwyżej o 0,08.
- **Nierówne limity graczy.** Modele lokalne miały limit 300 tokenów (`num_predict`), Claude 4000, a GPT żadnego. Goły Bielik v3.0 ma przez to część tur uciętych w pół zdania.
- **Interakcja sędzia × rodzina.** Sędzia Claude ocenia graczy Claude wyżej względem graczy GPT, niż robi to sędzia GPT, o +0,45 pkt [0,40; 0,51] w wariancie ogólnym
  i +0,32 w @gra. Sędzia GPT nie daje graczom GPT dodatkowej premii, więc zdanie „każdy sędzia stawia wyżej własną rodzinę o 0,25–0,35” jest nieścisłe.
  Z dwoma sędziami nie da się rozstrzygnąć, czy sędzia Claude faworyzuje Claude'a, czy sędzia GPT karze jego styl.
- **Nierozróżnialna jest tylko czołowa trójka** (Opus 5.5, GPT-6.2 sol, Fable 5.2), w obu wariantach; jej kolejność zależy od sędziego. Terra, Sonnet i luna są istotnie niżej.
- **„Dostrojony Bielik na poziomie Haiku” dotyczy tylko wariantu ogólnego** (+0,10 [−0,02; +0,21]). W @gra dostrojone modele są od Haiku istotnie słabsze (−0,16 do −0,20).
- **Teza o polszczyźnie się nie utrzymuje po kontroli długości.** Ocena `jezyk` jest za całą turę, więc dłuższa replika ma więcej okazji do usterki.
  Dostrojony model pisze krócej (ok. 200 znaków), goły Bielik dłużej (ok. 370). Przy tej samej długości repliki przewaga dostrojonego modelu w `jezyk` (+0,18) znika,
  a Fable i GPT są 0,25–0,6 pkt wyżej. Dostrojenie podnosi głównie `zabawa` i `w_roli`, nie polszczyznę.

**Edycja 1.5 (w toku)** poprawia te problemy: jeden budżet długości w prompcie dla wszystkich graczy, emulator Claude Haiku 5.5 zamiast gemma3:4b
i brak ucinania replik graczy (`run.py --protocol 1.5`).

**Ograniczenia:**

- Wynik jest względny: porównuje modele ocenione w jednej puli, nie z tablicą oryginalnego PingPonga, która używa innych sędziów (Claude 3.5 Sonnet, GPT-4o), innego emulatora i angielskich rozmów.
- Gracze Claude działają bez parametrów próbkowania, które obecne modele Claude odrzucają, i z myśleniem na poziomie `low`. Modele lokalne grają z temperature 0.7 i top_p 0.9.
- Odmowa API (`stop_reason: refusal`) liczy się jako odmowa gracza. Nie ma fallbacku na inny model, bo odmowy są częścią pomiaru.
- 64 rozmowy na model dają przedziały ±0,1–0,2. Pary na tych samych rozmowach z testem znaków mówią więcej niż same średnie. Przedziały nie obejmują wariancji sędziów, emulatora ani ziarna.
- Sędziowie należą do rodzin ocenianych modeli (patrz wyżej: preferencja własnej rodziny). W kolejnej edycji planujemy sędziego spoza obu rodzin i ocenę ludzką na próbce.
- Modele GPT grały przez Codex CLI z podmienionymi instrukcjami (`model_instructions_file`), a nie przez czyste API. Jeden emulator (gemma3:4b) i jedno ziarno. 16 rozmów ma tylko jednego sędziego (dwie paczki r2 bez werdyktu Claude).

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

Edition 1 results (including Bielik-11B-v2.1-Instruct: 3.05 general, 3.17 @gra) and the corrections after review are in
[README.en.md](README.en.md#results). In short: the 4B emulator broke about 23% of conversations, player token limits were unequal,
judge ratings interact with the player's model family, only the top three are indistinguishable, the tuned Bielik matches Haiku only in the
general variant, and its language-score gain over bare Bielik disappears once reply length is controlled. A corrected edition 1.5 is in progress.
