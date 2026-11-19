"""Adaptéry poskytovatelů: stejné rozhraní `(prompt, model, env, konfig) -> text odpovědi`.
Jen standardní knihovna. Chyby sítě i procesu se převádějí na `AIChyba`."""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request

from . import AIChyba


def _post(url: str, hlavicky: dict, telo: dict, limit: int) -> dict:
    req = urllib.request.Request(url, json.dumps(telo).encode(), {"Content-Type": "application/json", **hlavicky})
    try:
        with urllib.request.urlopen(req, timeout=limit) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise AIChyba(f"volání API selhalo: {type(e).__name__}")  # bez těla odpovědi (mohlo by obsahovat tajné údaje)


def claude_cli(prompt, model, env, k):
    try:
        p = subprocess.run(["claude", "-p", "--model", model], input=prompt, capture_output=True, text=True,
                           timeout=k.get("casovy_limit_s", 300), env=dict(env))
    except (OSError, subprocess.TimeoutExpired) as e:
        raise AIChyba(f"claude CLI: {type(e).__name__}")
    if p.returncode != 0:
        raise AIChyba(f"claude CLI skončilo kódem {p.returncode}")
    return p.stdout


def anthropic_api(prompt, model, env, k):
    d = _post("https://api.anthropic.com/v1/messages",
              {"x-api-key": env["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
              {"model": model, "max_tokens": 8192, "messages": [{"role": "user", "content": prompt}]},
              k.get("casovy_limit_s", 300))
    try:
        return "".join(b.get("text", "") for b in d["content"])
    except (KeyError, TypeError):
        raise AIChyba("neočekávaná odpověď Anthropic API")


def _openai_chat(url, klic, prompt, model, limit):
    d = _post(url.rstrip("/") + "/chat/completions", {"Authorization": f"Bearer {klic}"},
              {"model": model, "messages": [{"role": "user", "content": prompt}]}, limit)
    try:
        return d["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AIChyba("neočekávaná odpověď chat API")


def openai_api(prompt, model, env, k):
    return _openai_chat("https://api.openai.com/v1", env["OPENAI_API_KEY"], prompt, model, k.get("casovy_limit_s", 300))


def openai_compatible(prompt, model, env, k):
    return _openai_chat(env["OPENAI_COMPATIBLE_BASE_URL"], env["OPENAI_COMPATIBLE_API_KEY"], prompt, model,
                        k.get("casovy_limit_s", 300))


ADAPTERY = {"claude_cli": claude_cli, "anthropic_api": anthropic_api, "openai_api": openai_api,
            "openai_compatible": openai_compatible}
