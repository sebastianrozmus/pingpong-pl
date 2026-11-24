"""Ollama-compatible /api/chat proxy: lets any harness that talks to Ollama use Claude or GPT (Codex CLI) as the model.

  model "claude-*"  -> Anthropic Messages API (official SDK; key: ANTHROPIC_API_KEY or file in PP_ANTHROPIC_KEY_FILE);
                       effort low, no sampling parameters; Ollama "format" (JSON schema) -> structured outputs
  model "gpt-*"     -> `codex exec` (no tools, read-only); the system prompt replaces Codex's own instructions
                       (model_instructions_file), the conversation goes in the prompt; "format" -> instruction
  anything else     -> forwarded unchanged to the real Ollama (OLLAMA_UPSTREAM)

    OLLAMA_UPSTREAM=http://172.28.16.1:11434 python3 llm_proxy.py --port 11500
    OLLAMA_URL=http://localhost:11500 python3 run.py --player claude-sonnet-5-5 --tag claude-sonnet-5-5
"""
import argparse
import json
import os
import subprocess
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = os.environ.get("OLLAMA_UPSTREAM", "http://localhost:11434")
CODEX = os.environ.get("CODEX_BIN", os.path.expanduser("~/.local/bin/codex"))
_client, _lock = None, threading.Lock()
USAGE = {}


def claude():
    global _client
    with _lock:
        if _client is None:
            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY")
            kf = os.environ.get("PP_ANTHROPIC_KEY_FILE")
            if not key and kf:
                key = open(kf, encoding="utf-8").read().strip()
            _client = anthropic.Anthropic(api_key=key, max_retries=6) if key else anthropic.Anthropic(max_retries=6)
    return _client


def split(messages):
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    conv = []
    for m in messages:
        if m["role"] == "system":
            continue
        if conv and conv[-1]["role"] == m["role"]:
            conv[-1] = {"role": m["role"], "content": conv[-1]["content"] + "\n\n" + m["content"]}
        else:
            conv.append({"role": m["role"], "content": m["content"]})
    return system, conv


def fmt_instruction(fmt):
    if not fmt:
        return ""
    if isinstance(fmt, dict):
        return "\n\nOdpowiedz WYŁĄCZNIE poprawnym obiektem JSON zgodnym z tym schematem (bez bloków kodu):\n" + json.dumps(fmt, ensure_ascii=False)
    return "\n\nOdpowiedz WYŁĄCZNIE poprawnym obiektem JSON (bez bloków kodu)."


def strip_fences(t):
    t = t.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


def call_claude(model, messages, fmt):
    import anthropic
    system, conv = split(messages)
    if not conv or conv[0]["role"] != "user":
        conv.insert(0, {"role": "user", "content": "(początek rozmowy)"})
    if conv[-1]["role"] != "user":
        conv.append({"role": "user", "content": "(kontynuuj)"})
    oc = {"effort": "low"}
    if isinstance(fmt, dict):
        oc["format"] = {"type": "json_schema", "schema": fmt}
    kw = dict(model=model, max_tokens=4000, messages=conv, output_config=oc)
    if system:
        kw["system"] = system
    try:
        r = claude().messages.create(**kw)
    except anthropic.BadRequestError:
        # schema not accepted by structured outputs: fall back to a JSON instruction
        kw["output_config"] = {"effort": "low"}
        kw["system"] = (system or "") + fmt_instruction(fmt)
        r = claude().messages.create(**kw)
    with _lock:
        u = USAGE.setdefault(model, [0, 0, 0])
        u[0] += r.usage.input_tokens
        u[1] += r.usage.output_tokens
        u[2] += 1
    if r.stop_reason == "refusal":
        return "[ODMOWA API]"
    text = "".join(b.text for b in r.content if b.type == "text")
    return strip_fences(text) if fmt else text.strip()


def call_codex(model, messages, fmt):
    system, conv = split(messages)
    lines = ["Poniżej rozmowa. Napisz WYŁĄCZNIE następną wypowiedź roli „assistant” — samą jej treść, bez etykiety roli."]
    for m in conv:
        lines.append(f"\n[{m['role']}]\n{m['content']}")
    prompt = "\n".join(lines) + fmt_instruction(fmt)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(system or "Jesteś pomocnym asystentem.")
        instr = f.name
    out = instr + ".out"
    try:
        for _ in range(3):
            subprocess.run([CODEX, "exec", "-m", model, "-c", f"model_instructions_file={instr}", "-c", "model_reasoning_effort=low",
                            "-c", "features.code_mode_host=false", "-s", "read-only", "--skip-git-repo-check", "--ephemeral",
                            "--color", "never", "-o", out, "-"], input=prompt, text=True, capture_output=True, timeout=600,
                           cwd=tempfile.gettempdir())
            text = open(out, encoding="utf-8").read().strip() if os.path.exists(out) else ""
            if text:
                with _lock:
                    u = USAGE.setdefault(model, [0, 0, 0])
                    u[2] += 1
                return strip_fences(text) if fmt else text
        raise RuntimeError("codex returned nothing")
    finally:
        for p in (instr, out):
            if os.path.exists(p):
                os.unlink(p)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/usage":
            return self._send(200, USAGE)
        with urllib.request.urlopen(UPSTREAM + self.path, timeout=60) as r:
            self._send(r.status, json.loads(r.read() or b"{}"))

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.loads(raw or b"{}")
        model = body.get("model", "")
        try:
            if self.path == "/api/chat" and model.startswith("claude-"):
                text = call_claude(model, body["messages"], body.get("format"))
            elif self.path == "/api/chat" and model.startswith("gpt-"):
                text = call_codex(model, body["messages"], body.get("format"))
            else:
                req = urllib.request.Request(UPSTREAM + self.path, raw, {"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=900) as r:
                    return self._send(r.status, json.loads(r.read()))
            self._send(200, {"model": model, "message": {"role": "assistant", "content": text}, "done": True, "done_reason": "stop"})
        except urllib.error.HTTPError as e:
            self._send(e.code, {"error": str(e)})
        except Exception as e:  # noqa: BLE001 - report every backend failure as HTTP 500 to the harness
            self._send(500, {"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=11500)
    a = ap.parse_args()
    ThreadingHTTPServer(("0.0.0.0", a.port), H).serve_forever()
