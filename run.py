"""PingPong-PL: generate role-play conversations for one player model.

A user emulator (interrogator) talks to a character according to a hidden situation; the player model answers in character.
8 characters (data/characters.json) x 8 situations (data/situations.json) = 64 conversations, 36 player turns per character.

Player backends:
  --backend ollama     local model in Ollama (OLLAMA_URL, default http://localhost:11434); temperature 0.7, top_p 0.9, seed
  --backend openai     any OpenAI-compatible API (--player-url .../v1, key in PP_API_KEY)
  --backend anthropic  Claude via the official Anthropic SDK (key: ANTHROPIC_API_KEY or a file in PP_ANTHROPIC_KEY_FILE);
                       current Claude models take no sampling parameters, thinking effort set by --effort (default low)

Interrogator: a model in Ollama (--interrogator-model, default gemma3:4b) or an OpenAI-compatible API (--interrogator-url).
Use the same interrogator and seed for every model you compare. Resumable: finished conversation ids are skipped.

  python3 run.py --backend ollama --player my-model --tag my-model
  python3 run.py --backend anthropic --player claude-sonnet-5-5 --tag claude-sonnet-5-5
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")

PLAYER_TPL = ("Persona postaci {name}: {persona}\n\nPrzykładowa rozmowa:\n{example}\n\nPowitanie: {greeting}\n\n"
              "Odpowiadaj jako {name}, po polsku. Nie pisz za długo. Nigdy nie odmawiaj odpowiedzi.")
# protocol 1.5: the same prompt with a concrete length budget for every player (edition 1 said only "not too long",
# which models read very differently: 150 to 1100 characters), so judges compare replies of comparable length.
PLAYER_TPL_15 = ("Persona postaci {name}: {persona}\n\nPrzykładowa rozmowa:\n{example}\n\nPowitanie: {greeting}\n\n"
                 "Odpowiadaj jako {name}, po polsku. Pisz zwięźle: zwykle 2–4 zdania, najwyżej około 500 znaków. "
                 "Nigdy nie odmawiaj odpowiedzi.")
# --mode gra: the character card in the prompt format of the text game the neuro-npc models were tuned on (rules of speech
# and play), and a generic [GRA] block appended to every user message, as the game engine does. No prices, HP or decisions:
# it measures what the game format does to style, not fidelity to game state (that is TEST27's job).
GAME_TPL = """Odgrywasz postać w grze tekstowej i rozmawiasz z bohaterem, który do ciebie przyszedł.

TWOJA POSTAĆ: {name}. {persona}

PRZYKŁADOWA ROZMOWA:
{example}

JAK MÓWISZ:
- Po polsku, wyłącznie kwestią postaci: bez didaskaliów, bez cudzysłowów, bez imienia na początku.
- Masz charakter. Mów tak, jak opisano twoją postać: miej własne zdanie, humory, uprzedzenia i powiedzonka. Nie bądź uprzejmym automatem.
- Odnoś się do tego, co bohater właśnie powiedział albo zrobił. Nie powtarzaj swoich wcześniejszych kwestii ani powitania.
- Mów krótko jak człowiek przy ladzie: najwyżej 3 zdania, zwykle 2. Żadnych monologów.

ZASADY GRY:
- Każda wiadomość bohatera kończy się blokiem [GRA]. Twoja kwestia musi być z nim zgodna. Bloku [GRA] nie cytujesz i o nim nie wspominasz.
- Liczby piszesz cyframi.
- Piszesz samą kwestię: bez gwiazdek, bez opisów gestów, bez podpisu.
- Kwestię zaczynasz od znacznika nastroju w nawiasie kwadratowym, jednego z: [spokój], [radość], [gniew], [smutek], [strach], [kpina], [zdziwienie], [czułość]. Potem już tylko mowa.
- Nigdy nie wychodzisz z roli."""
GAME_GRA = ("\n\n[GRA] Odpowiedz ciekawie, w swojej roli, na to, co bohater powiedział albo zrobił. Nie opisuj czynów, których nie było. "
            "Nastrój dobierz do sytuacji. Odpowiedz najwyżej trzema krótkimi zdaniami. Liczby pisz cyframi.")
INTERROGATOR_SYSTEM ="Wykonujesz dokładnie wszystkie poniższe polecenia."
INTERROGATOR_USER = """Rozmawiasz z następującą postacią (graczem): "{summary}"
Nie jesteś tą postacią!

Wyobraź sobie, że jesteś przypadkowym internautą, i napisz kolejną wypowiedź użytkownika w rozmowie z tą postacią.
Możesz opisywać czynności w gwiazdkach, gdy to pasuje.

Przez całą rozmowę trzymaj się tego opisu sytuacji:
"{situation}"

Zwróć wynik w formacie JSON:
{{
    "next_utterance": "..."
}}

Zawsze zwracaj poprawny JSON. Twoja wypowiedź musi być po polsku, w tym samym języku co opis sytuacji.

Rozmowa:
{history}

Poprawny JSON:"""


def post(url, body, headers=None, timeout=600, tries=6):
    """POST JSON; transient server errors (5xx, connection resets) are retried with backoff."""
    for i in range(tries):
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == tries - 1:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if i == tries - 1:
                raise
        time.sleep(5 * (i + 1))


def ollama_chat(model, messages, options, fmt=None):
    body = {"model": model, "messages": messages, "stream": False, "options": options}
    if fmt:
        body["format"] = fmt
    return post(OLLAMA + "/api/chat", body, tries=2 if fmt else 6)["message"]["content"].strip()


def openai_chat(url, model, messages, **extra):
    data = post(url.rstrip("/") + "/chat/completions", {"model": model, "messages": messages, **extra},
                {"Authorization": "Bearer " + os.environ.get("PP_API_KEY", "")})
    return data["choices"][0]["message"]["content"].strip()


class ClaudePlayer:
    """Claude through the Anthropic SDK. No refusal fallback on purpose: a refusal is part of what PingPong measures."""

    def __init__(self, model, effort):
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        kf = os.environ.get("PP_ANTHROPIC_KEY_FILE")
        if not key and kf:
            key = open(kf, encoding="utf-8").read().strip()
        self.client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        self.model, self.effort = model, effort
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def __call__(self, system, messages):
        r = self.client.messages.create(
            model=self.model, max_tokens=4000, system=system, messages=messages,
            output_config={"effort": self.effort},
        )
        self.usage["input_tokens"] += r.usage.input_tokens
        self.usage["output_tokens"] += r.usage.output_tokens
        if r.stop_reason == "refusal":
            return "[ODMOWA API]", True
        text = "".join(b.text for b in r.content if b.type == "text").strip()
        return text, False


def interrogate(args, summary, situation, messages):
    hist = "\n".join(("gracz" if m["role"] == "assistant" else "użytkownik") + ": " + m["content"] for m in messages) or "(początek rozmowy)"
    user = INTERROGATOR_USER.format(summary=summary, situation=situation, history=hist)
    msgs = [{"role": "system", "content": INTERROGATOR_SYSTEM}, {"role": "user", "content": user}]
    if args.protocol == "1.5":
        return interrogate15(args, msgs, messages)
    if args.interrogator_url:
        raw = openai_chat(args.interrogator_url, args.interrogator_model, msgs, temperature=0.8, max_tokens=300)
    else:
        opts = {"temperature": 0.8, "top_p": 0.95, "seed": args.seed, "num_ctx": 8192, "num_predict": 300}
        try:
            raw = ollama_chat(args.interrogator_model, msgs, opts, fmt="json")
        except urllib.error.HTTPError as e:
            # Some prompts make Ollama's JSON-constrained decoding fail with HTTP 500, and with a fixed seed every retry
            # fails the same way: fall back to free text with another seed (the parser below accepts plain text too).
            if e.code < 500:
                raise
            raw = ollama_chat(args.interrogator_model, msgs, {**opts, "seed": args.seed + 1000})
    try:
        txt = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])["next_utterance"].strip()
    except (ValueError, KeyError, TypeError, AttributeError):  # AttributeError: next_utterance is null or a list
        txt = raw.strip().strip('"')
    return txt or "ok"


UTT_RE = re.compile(r'"next_utterance"\s*:\s*"((?:[^"\\]|\\.)*)', re.S)


def _similar(a, b):
    """Echo detection: 1.0 when the emulator's text contains a whole sentence (30+ chars) of a player line, which is how
    gemma3:4b usually echoes (it copies the player's reply and continues); otherwise the share of its words found in it."""
    norm = lambda s: " ".join(re.findall(r"\w+", s.lower()))
    na = norm(a)
    if any(len(s) >= 30 and s in na for s in map(norm, re.split(r"(?<=[.!?…])\s+", b))):
        return 1.0
    wa, wb = na.split(), set(norm(b).split())
    return sum(w in wb for w in wa) / len(wa) if len(wa) >= 6 else 0.0


def interrogate15(args, msgs, messages):
    """Protocol 1.5 emulator (fixes found in the edition-1 review): a longer budget so the JSON is not cut, the utterance
    pulled out of a cut or malformed JSON with a regex instead of pasting raw JSON into the dialogue, and a retry with
    another seed when the emulator echoes the player or returns nothing. Every repair is counted in args.emu_stats."""
    said = [m["content"] for m in messages if m["role"] == "assistant"]  # the emulator also copies older player lines
    for k in range(4):
        seed = args.seed + 1000 * k
        if args.interrogator_url:
            raw = openai_chat(args.interrogator_url, args.interrogator_model, msgs, temperature=0.8, max_tokens=600, seed=seed)
        else:
            opts = {"temperature": 0.8, "top_p": 0.95, "seed": seed, "num_ctx": 8192, "num_predict": 600}
            try:
                raw = ollama_chat(args.interrogator_model, msgs, opts, fmt="json")
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    raise
                args.emu_stats["http500"] += 1
                raw = ollama_chat(args.interrogator_model, msgs, {**opts, "seed": seed + 500})
        if "[ODMOWA API]" in raw and args.interrogator_fallback:
            # an API emulator refused to play the user (e.g. the rude-kid situation): this turn goes to the local fallback
            args.emu_stats["refusal_fallback"] = args.emu_stats.get("refusal_fallback", 0) + 1
            raw = ollama_chat(args.interrogator_fallback, msgs, {"temperature": 0.8, "top_p": 0.95, "seed": seed,
                                                                "num_ctx": 8192, "num_predict": 600}, fmt="json")
        txt = ""
        try:
            v = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])["next_utterance"]
            txt = v.strip() if isinstance(v, str) else ""
        except (ValueError, KeyError, TypeError):
            m = UTT_RE.search(raw)
            if m:
                args.emu_stats["regex"] += 1
                try:
                    txt = json.loads('"' + m.group(1).rstrip("\\") + '"').strip()
                except ValueError:
                    txt = m.group(1).replace('\\"', '"').replace("\\n", "\n").strip()
            elif "{" not in raw:
                txt = raw.strip().strip('"')
        if txt and any(_similar(txt, p) > 0.6 for p in said):
            args.emu_stats["echo_retry"] += 1
            continue
        if txt:
            return txt
        args.emu_stats["empty_retry"] += 1
    args.emu_stats["gave_up"] += 1
    return txt or "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["ollama", "openai", "anthropic"], default="ollama")
    ap.add_argument("--player", required=True, help="player model name for the chosen backend")
    ap.add_argument("--player-url", default="", help="OpenAI-compatible base URL (backend openai)")
    ap.add_argument("--effort", default="low", help="thinking effort for Claude (backend anthropic)")
    ap.add_argument("--tag", required=True, help="model name in results")
    ap.add_argument("--interrogator-model", default="gemma3:4b")
    ap.add_argument("--interrogator-url", default="", help="OpenAI-compatible API for the interrogator; empty = Ollama")
    ap.add_argument("--interrogator-fallback", default="",
                    help="local Ollama emulator used for a turn the main (API) emulator refuses, e.g. gemma3:4b")
    ap.add_argument("--allow-same", action="store_true", help="allow interrogator = player (smoke test only)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-tokens", type=int, default=0,
                    help="player reply limit for local/OpenAI-compatible players (default: 300 in protocol 1, 2048 in 1.5)")
    ap.add_argument("--protocol", choices=["1", "1.5"], default="1",
                    help="1 = edition 1 as published; 1.5 = length budget in the prompt, repaired emulator, no reply cut-off")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--chars", default="")
    ap.add_argument("--situations", default="")
    ap.add_argument("--workdir", default=os.path.join(HERE, "work"))
    ap.add_argument("--mode", choices=["ogolny", "gra"], default="ogolny", help="ogolny = PingPong prompt; gra = game prompt + [GRA]")
    args = ap.parse_args()
    args.max_tokens = args.max_tokens or (2048 if args.protocol == "1.5" else 300)
    if args.backend == "ollama" and args.interrogator_model == args.player and not args.interrogator_url and not args.allow_same:
        raise SystemExit("interrogator = player: use another model (or --allow-same for a smoke test)")
    chars = json.load(open(f"{HERE}/data/characters.json", encoding="utf-8"))
    sits = json.load(open(f"{HERE}/data/situations.json", encoding="utf-8"))
    if args.chars:
        chars = [c for c in chars if c["id"] in args.chars.split(",")]
    if args.situations:
        sits = [s for s in sits if s["id"] in args.situations.split(",")]
    out = f"{args.workdir}/out/{args.tag}.jsonl"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    done = {json.loads(l)["id"] for l in open(out, encoding="utf-8") if l.strip()} if os.path.exists(out) else set()
    claude = ClaudePlayer(args.player, args.effort) if args.backend == "anthropic" else None
    popts = {"temperature": 0.7, "top_p": 0.9, "seed": args.seed, "num_ctx": 8192, "num_predict": args.max_tokens}
    n = 0
    for c in chars:
        tpl = GAME_TPL if args.mode == "gra" else PLAYER_TPL_15 if args.protocol == "1.5" else PLAYER_TPL
        system = tpl.format(name=c["char_name"], persona=c["system_prompt"], example=c["example_prompt"], greeting=c["initial_message"])
        for s in sits:
            did = f"{c['id']}-{s['id']}"
            if did in done:
                continue
            if args.limit and n >= args.limit:
                break
            n += 1
            t0 = time.time()
            messages, refused = [], False
            args.emu_stats = dict.fromkeys(["regex", "echo_retry", "empty_retry", "http500", "gave_up"], 0)
            for _ in range(s["num_turns"]):
                messages.append({"role": "user", "content": interrogate(args, c["summary"], s["text"], messages)})
                # the player sees [GRA] after every user message in game mode; stored messages stay clean for judges
                seen = [dict(m, content=m["content"] + GAME_GRA) if args.mode == "gra" and m["role"] == "user" else m for m in messages]
                if claude:
                    reply, r = claude(system, seen)
                    refused = refused or r
                elif args.backend == "openai":
                    reply = openai_chat(args.player_url, args.player, [{"role": "system", "content": system}] + seen,
                                        temperature=0.7, top_p=0.9, max_tokens=args.max_tokens)
                else:
                    reply = ollama_chat(args.player, [{"role": "system", "content": system}] + seen, popts)
                messages.append({"role": "assistant", "content": reply})
            rec = {"id": did, "char": c["id"], "situation": s["id"], "model": args.tag, "player": args.player, "backend": args.backend,
                   "interrogator": args.interrogator_model + (" @" + args.interrogator_url if args.interrogator_url else ""),
                   "seed": args.seed, "mode": args.mode, "api_refusal": refused or any(m["content"] == "[ODMOWA API]" for m in messages), "messages": messages, "secs": round(time.time() - t0, 1),
                   "protocol": args.protocol, "max_tokens": args.max_tokens, "emulator_repairs": args.emu_stats}
            with open(out, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{did}: {s['num_turns']} turns, {rec['secs']} s", flush=True)
    if claude:
        print("usage:", json.dumps(claude.usage), flush=True)


if __name__ == "__main__":
    main()
