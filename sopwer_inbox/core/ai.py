# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Provider-agnostic AI draft generation for agent-assist ("Sarankan balasan").

The agent is ALWAYS in the loop: this module only produces a *draft* string for
the composer. It never sends anything to the customer.

Three providers, all over plain HTTP (no SDK dependency):
  - ``Ollama``  — local server, no API key.
  - ``Claude``  — Anthropic Messages API, prompt-cached system block.
  - ``OpenAI``  — Chat Completions API.

Entry points:
  - ``generate_draft(transcript, config) -> str``  — draft the next agent reply.
  - ``ping(config) -> None``                       — provider reachability check.
"""

import requests

TIMEOUT = 45
MAX_TOKENS = 600
DEFAULT_SYSTEM = (
	"You are a helpful customer-service agent replying on a messaging channel. "
	"Write a concise, friendly reply in the SAME language as the customer's last "
	"message. Reply with the message text only — no preamble, no quotes."
)

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_OPENAI_DEFAULT = "https://api.openai.com"


class AIError(Exception):
	"""Any failure while producing a draft — surfaced as a clean error to the UI."""


# --------------------------------------------------------------------------- #
# Config / transcript helpers
# --------------------------------------------------------------------------- #

def _norm_provider(config: dict) -> str:
	provider = (config.get("provider") or "").strip().lower()
	if provider not in ("ollama", "claude", "openai"):
		raise AIError(f"Unknown AI provider: {config.get('provider')!r}")
	return provider


def _require(config: dict, key: str, label: str) -> str:
	val = (config.get(key) or "").strip()
	if not val:
		raise AIError(f"AI config missing: {label}")
	return val


def _chat_messages(transcript: list[dict]) -> list[dict]:
	"""Map the inbox transcript onto chat-API messages.

	``transcript`` items are ``{"role": "customer"|"agent", "content": str}``.
	Customer turns become ``user``; agent turns become ``assistant``. Empty
	contents are dropped. The model is asked (via the system prompt) to draft the
	NEXT agent reply, so the last meaningful turn is normally the customer's."""
	out = []
	for m in transcript or []:
		content = (m.get("content") or "").strip()
		if not content:
			continue
		role = "assistant" if m.get("role") == "agent" else "user"
		out.append({"role": role, "content": content})
	if not out:
		raise AIError("No conversation history to draft a reply from.")
	return out


def _system_prompt(config: dict) -> str:
	extra = (config.get("system_prompt") or "").strip()
	return f"{DEFAULT_SYSTEM}\n\n{extra}" if extra else DEFAULT_SYSTEM


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def generate_draft(transcript: list[dict], config: dict) -> str:
	"""Return a draft reply string for the next agent turn. Raises AIError."""
	provider = _norm_provider(config)
	messages = _chat_messages(transcript)
	system = _system_prompt(config)
	if provider == "ollama":
		return _ollama(messages, system, config)
	if provider == "claude":
		return _claude(messages, system, config)
	return _openai(messages, system, config)


def ping(config: dict) -> None:
	"""Lightweight reachability/credential check. Raises AIError on failure."""
	probe = [{"role": "customer", "content": "ping"}]
	draft = generate_draft(probe, config)
	if not draft:
		raise AIError("Provider returned an empty response.")


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #

def _post(url: str, *, headers=None, json=None) -> dict:
	try:
		resp = requests.post(url, headers=headers or {}, json=json, timeout=TIMEOUT)
	except requests.RequestException as e:
		raise AIError(f"Could not reach AI provider: {e}") from e
	if resp.status_code >= 400:
		raise AIError(f"AI provider error {resp.status_code}: {resp.text[:300]}")
	try:
		return resp.json()
	except ValueError as e:
		raise AIError("AI provider returned a non-JSON response.") from e


def _ollama(messages: list[dict], system: str, config: dict) -> str:
	endpoint = (config.get("endpoint") or "http://localhost:11434").rstrip("/")
	model = _require(config, "model", "Model")
	body = {
		"model": model,
		"messages": [{"role": "system", "content": system}, *messages],
		"stream": False,
	}
	data = _post(f"{endpoint}/api/chat", json=body)
	content = ((data.get("message") or {}).get("content") or "").strip()
	if not content:
		raise AIError("Ollama returned an empty draft.")
	return content


def _claude(messages: list[dict], system: str, config: dict) -> str:
	api_key = _require(config, "api_key", "API Key")
	model = _require(config, "model", "Model")
	headers = {
		"x-api-key": api_key,
		"anthropic-version": _ANTHROPIC_VERSION,
		"content-type": "application/json",
	}
	body = {
		"model": model,
		"max_tokens": MAX_TOKENS,
		# Cache the (stable) system block so repeated suggests on the same site
		# reuse it — cuts latency and cost on the input side.
		"system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
		"messages": messages,
	}
	data = _post(_ANTHROPIC_URL, headers=headers, json=body)
	blocks = data.get("content") or []
	text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
	if not text:
		raise AIError("Claude returned an empty draft.")
	return text


def _openai(messages: list[dict], system: str, config: dict) -> str:
	api_key = _require(config, "api_key", "API Key")
	model = _require(config, "model", "Model")
	base = (config.get("endpoint") or _OPENAI_DEFAULT).rstrip("/")
	headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
	body = {
		"model": model,
		"messages": [{"role": "system", "content": system}, *messages],
		"max_tokens": MAX_TOKENS,
	}
	data = _post(f"{base}/v1/chat/completions", headers=headers, json=body)
	choices = data.get("choices") or []
	if not choices:
		raise AIError("OpenAI returned no choices.")
	content = ((choices[0].get("message") or {}).get("content") or "").strip()
	if not content:
		raise AIError("OpenAI returned an empty draft.")
	return content
