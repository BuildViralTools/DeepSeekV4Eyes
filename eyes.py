#!/usr/bin/env python3
"""eyes.py — real vision for your AI.

Coding assistants (Claude Code, Copilot, Cursor, ...) can describe images only
when the model behind them supports vision. When it doesn't (a third-party
gateway, a text-only model, a local model) images arrive as a
"[Unsupported Image]" placeholder and nothing can describe them.

eyes.py bridges that gap: it sends the image straight to a real vision-capable
model API and prints the description as plain text, which the assistant can read.

Works with ANY of these, auto-detected from your API key:
    Claude (Anthropic)   sk-ant-api-...          default: claude-sonnet-5
    GPT / OpenAI         sk-proj-... / sk-svc-.. default: gpt-4o
    Grok (xAI)           xai-...                 default: grok-2-vision-1212
    Gemini (Google)      AIza...                 default: gemini-2.5-flash

Only one dependency: `pip install anthropic` (used for the Claude path). The
other providers talk plain HTTP via the standard library.

Usage:
    python eyes.py <image> [prompt]
    python eyes.py <image> --model claude-opus-5
    python eyes.py <image> --provider openai
    python eyes.py <image> --api-key sk-proj-... --provider openai
    python eyes.py --create "a logo: an eye with a lightning bolt" --provider openai
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:  # friendly error instead of a raw traceback
    sys.exit(
        "ERROR: missing dependency 'anthropic'. Install it first:\n"
        "    pip install anthropic"
    )

# Windows consoles default to cp1252, which cannot print characters like "ă".
# Force UTF-8 so Romanian / non-ASCII descriptions survive stdout.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:  # pragma: no cover — older Pythons
    pass

ENV_FILE = Path(__file__).resolve().parent / ".env"
OUT_DIR = Path(__file__).resolve().parent / "generated"

DEFAULT_PROMPT = (
    "Describe this image in detail: structure, layout, colors, any visible "
    "text (transcribe it exactly), visual elements, and its likely purpose."
)

# Model / endpoint defaults per provider.
PROVIDER_DEFAULTS = {
    "anthropic": {"model": "claude-sonnet-5", "base_url": "https://api.anthropic.com"},
    "openai": {"model": "gpt-4o", "base_url": "https://api.openai.com/v1"},
    "grok": {"model": "grok-2-vision-1212", "base_url": "https://api.x.ai/v1"},
    "gemini": {
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    },
}

# ─────────────────────────────────────────────────────────────────
# ⚙️  IMAGE GENERATION — EDIT YOUR MODELS HERE. Make it yours.
#     These are used by `python eyes.py --create "<prompt>"`.
#     Model IDs change over time — check each provider's current list
#     and edit freely. You can also add more providers below.
#
#     Note: Anthropic (Claude) has NO image-generation API.
# ─────────────────────────────────────────────────────────────────
IMAGE_MODELS = {
    "openai": "gpt-5.6",                        # OpenAI (e.g. gpt-image-1 / dall-e-3 — edit to current ID)
    "grok": "grok-image-1.5",                   # xAI Grok Image
    "gemini": "imagen-3.0-generate-002",        # Google Imagen
}

# Which env-var names hold the key for each provider (.env preferred, then env).
PROVIDER_ENV_KEYS = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "grok": ["XAI_API_KEY", "GROK_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
}

# Key prefixes used to auto-detect the provider.
PREFIX_TO_PROVIDER = [
    ("anthropic", ("sk-ant-api",)),
    ("gemini", ("AIza",)),
    ("grok", ("xai-",)),
    ("openai", ("sk-proj-", "sk-svc-")),
]

DEFAULTS_STR = ", ".join(
    "{}={}".format(k, v["model"]) for k, v in PROVIDER_DEFAULTS.items()
)

# Scan order for auto-detection (Claude preferred when several keys exist).
ALL_ENV_NAMES = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
]


def parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a .env file into {NAME: value} (no external deps)."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def detect_provider(key: str) -> str | None:
    """Guess the provider from an API key prefix, or None if unknown."""
    for provider, prefixes in PREFIX_TO_PROVIDER:
        if key.startswith(prefixes):
            return provider
    return None


def collect_keys(cli_key: str | None, dotenv: dict[str, str]) -> list[tuple[str, str]]:
    """Return [(source, key)] in priority order."""
    keys: list[tuple[str, str]] = []
    if cli_key:
        keys.append(("--api-key", cli_key))
    for name in ALL_ENV_NAMES:
        if name in dotenv:
            keys.append((f".env:{name}", dotenv[name]))
        elif name in os.environ:
            keys.append((f"env:{name}", os.environ[name]))
    return keys


def resolve(cli_key: str | None, dotenv: dict[str, str],
            provider: str) -> tuple[str, str]:
    """Return (provider, api_key). Resolves key source for the provider."""
    keys = collect_keys(cli_key, dotenv)

    if provider == "auto":
        # First key with a recognizable prefix wins (scan order above).
        for _, key in keys:
            detected = detect_provider(key)
            if detected:
                return detected, key
        if keys:
            sys.exit(
                "ERROR: could not auto-detect the provider from your key. "
                "Pass --provider {anthropic|openai|grok|gemini}."
            )
        sys.exit(
            "ERROR: no API key found. Set one in .env (e.g. ANTHROPIC_API_KEY=sk-ant-...), "
            "an env var, or pass --api-key."
        )

    # Explicit provider: look for its env vars first, then any available key.
    if cli_key:
        return provider, cli_key
    for name in PROVIDER_ENV_KEYS[provider]:
        if name in dotenv:
            return provider, dotenv[name]
        if name in os.environ:
            return provider, os.environ[name]
    if keys:
        return provider, keys[0][1]
    sys.exit(
        f"ERROR: no key found for provider '{provider}' "
        f"({', '.join(PROVIDER_ENV_KEYS[provider])})."
    )


def resolve_media_type(filename: str, forced: str | None) -> str:
    """Map a file to its image MIME type; supports an explicit override."""
    if forced:
        return forced
    mime, _ = mimetypes.guess_type(filename)
    if not mime or not mime.startswith("image/"):
        raise ValueError(
            f"unsupported or unknown image type for {filename!r} "
            f"(got {mime or 'nothing'}). Pass --media-type to force it."
        )
    return mime


def http_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    """POST JSON, return parsed JSON. Stdlib only."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from None


def call_anthropic(base_url: str, api_key: str, model: str, prompt: str,
                   mime: str, image_b64: str, max_tokens: int) -> str:
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str,
                           mime: str, image_b64: str, max_tokens: int) -> str:
    """Chat Completions API — works for OpenAI, Grok, and any compatible host."""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                    },
                ],
            }
        ],
    }
    data = http_json(url, headers, payload)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"unexpected response shape: {json.dumps(data)[:500]}"
        ) from None


def call_gemini(base_url: str, api_key: str, model: str, prompt: str,
                mime: str, image_b64: str, max_tokens: int) -> str:
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime, "data": image_b64}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    data = http_json(url, {}, payload)
    if "error" in data:
        raise RuntimeError(f"Gemini error: {json.dumps(data['error'])}")
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"unexpected response shape: {json.dumps(data)[:500]}"
        ) from None


# ── Image generation (used with --create) ─────────────────────────

def fetch_bytes(url: str) -> bytes:
    """Download a URL into bytes."""
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()


def generate_openai_compatible(base_url: str, api_key: str, model: str,
                               prompt: str, size: str | None) -> bytes:
    """POST /images/generations — works for OpenAI and Grok (both OpenAI-compatible).

    `size` is only sent when provided: Grok rejects it ("Argument not supported").
    """
    url = base_url.rstrip("/") + "/images/generations"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "response_format": "b64_json",
    }
    if size:
        payload["size"] = size
    data = http_json(url, headers, payload)
    try:
        item = data["data"][0]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"unexpected response shape: {json.dumps(data)[:500]}"
        ) from None
    if "b64_json" in item:
        return base64.b64decode(item["b64_json"])
    if "url" in item:
        return fetch_bytes(item["url"])
    raise RuntimeError(f"no image in response: {json.dumps(item)[:300]}")


def generate_gemini(base_url: str, api_key: str, model: str, prompt: str) -> bytes:
    """Google Imagen via the :predict endpoint."""
    url = f"{base_url.rstrip('/')}/models/{model}:predict?key={api_key}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1},
    }
    data = http_json(url, {}, payload)
    if "error" in data:
        raise RuntimeError(f"Gemini error: {json.dumps(data['error'])}")
    try:
        b64 = data["predictions"][0]["bytesBase64Encoded"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"unexpected response shape: {json.dumps(data)[:500]}"
        ) from None
    return base64.b64decode(b64)


def run_create(prompt: str, provider: str, api_key: str, base_url: str,
               model: str | None, size: str, out_path: str | None,
               verbose: bool) -> None:
    """Generate an image from a prompt and save it to disk."""
    if provider == "anthropic":
        sys.exit(
            "ERROR: Claude can't generate images. Use --provider openai, grok, or "
            "gemini (and a matching API key)."
        )
    if provider not in IMAGE_MODELS:
        sys.exit(
            f"ERROR: no image-generation model configured for '{provider}'. "
            f"Edit IMAGE_MODELS at the top of eyes.py."
        )
    gen_model = model or IMAGE_MODELS[provider]
    if verbose:
        print(f"[eyes] create provider={provider} model={gen_model} base_url={base_url}",
              file=sys.stderr)

    if provider == "openai":
        image_bytes = generate_openai_compatible(base_url, api_key, gen_model, prompt, size)
    elif provider == "grok":
        # Grok's API rejects the `size` argument.
        image_bytes = generate_openai_compatible(base_url, api_key, gen_model, prompt, None)
    else:  # gemini
        image_bytes = generate_gemini(base_url, api_key, gen_model, prompt)

    if out_path:
        out = Path(out_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = OUT_DIR / f"{provider}-{stamp}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image_bytes)
    print(out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze an image with a vision-capable model "
                    "(Claude, GPT, Grok, Gemini) — real vision for Claude Code.",
        epilog="examples:\n"
               "  python eyes.py screenshot.png\n"
               "  python eyes.py screenshot.png \"transcribe all text\"\n"
               "  python eyes.py ui.png --model claude-opus-5\n"
               "  python eyes.py ui.png --api-key sk-proj-... --provider openai\n"
               "  python eyes.py ui.png --verbose",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "image",
        nargs="?",
        default=None,
        help="Path to the image file to describe (png/jpg/jpeg/gif/webp/bmp)",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="What to look for. Defaults to a generic detailed description.",
    )
    parser.add_argument(
        "--create",
        metavar="PROMPT",
        default=None,
        help="Generate an image from a prompt instead of describing one. "
             "Needs a key that supports generation (openai / grok / gemini).",
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="Image size for --create (default: 1024x1024)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for --create (default: generated/...)",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", *PROVIDER_DEFAULTS],
        default="auto",
        help="Model provider (default: auto-detect from the key prefix).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use. Defaults per provider: " + DEFAULTS_STR + ".",
    )
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key (overrides .env and env vars)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override the provider endpoint (advanced).",
    )
    parser.add_argument(
        "--media-type",
        default=None,
        help="Force the image MIME type, e.g. image/png",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print resolved provider/model/endpoint to stderr",
    )
    args = parser.parse_args()

    if args.create and args.image:
        parser.error("provide EITHER an image to describe OR --create — not both.")
    if not args.create and not args.image:
        parser.error("provide an image to describe, or --create <prompt> to generate one.")

    dotenv = parse_dotenv(ENV_FILE)
    provider, api_key = resolve(args.api_key, dotenv, args.provider)
    base_url = args.base_url or PROVIDER_DEFAULTS[provider]["base_url"]

    if args.create:
        try:
            run_create(args.create, provider, api_key, base_url, args.model,
                       args.size, args.out, args.verbose)
        except RuntimeError as exc:
            sys.exit(f"ERROR: {exc}")
        return

    image_path = Path(args.image)
    if not image_path.is_file():
        parser.error(f"image not found: {image_path}")
    model = args.model or PROVIDER_DEFAULTS[provider]["model"]

    if args.verbose:
        source = next(
            (s for s, _ in collect_keys(args.api_key, dotenv) if _ == api_key),
            "unknown",
        )
        print(
            f"[eyes] provider={provider} model={model} base_url={base_url} key={source}",
            file=sys.stderr,
        )

    mime = resolve_media_type(image_path.name, args.media_type)
    image_b64 = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    prompt = args.prompt or DEFAULT_PROMPT

    try:
        if provider == "anthropic":
            text = call_anthropic(base_url, api_key, model, prompt, mime, image_b64,
                                  args.max_tokens)
        elif provider == "gemini":
            text = call_gemini(base_url, api_key, model, prompt, mime, image_b64,
                               args.max_tokens)
        else:  # openai / grok — both speak Chat Completions
            text = call_openai_compatible(base_url, api_key, model, prompt, mime,
                                          image_b64, args.max_tokens)
    except anthropic.AuthenticationError:
        sys.exit("ERROR: API key rejected (401). Is it a valid Anthropic key?")
    except anthropic.NotFoundError as exc:
        sys.exit(f"ERROR: model {model!r} not found: {exc}")
    except anthropic.RateLimitError as exc:
        sys.exit(f"ERROR: rate limited: {exc}")
    except anthropic.APIStatusError as exc:
        sys.exit(f"ERROR: API error {exc.status_code}: {exc}")
    except RuntimeError as exc:
        sys.exit(f"ERROR: {exc}")

    print(text)


if __name__ == "__main__":
    main()
