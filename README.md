# 👁️ eyes.py — real vision for your AI

A tiny tool that gives an AI coding assistant **real eyes**: it sends an image
to a vision-capable model and prints the description as plain text that the
assistant can read back. It can also **create** images from a prompt with GPT,
Grok, or Gemini.

**Provider-agnostic.** Works with **Claude, GPT, Grok, or Gemini** — the
provider is auto-detected from your API key. No key or model is hardcoded.

---

## The problem it solves

Coding assistants (Claude Code, Copilot, Grok, and others) can describe
images **only when the model powering them supports vision** — and that's not
always the case:

- The assistant may be routed to a **non-vision model**: Claude Code pointed at
  a third-party Anthropic-compatible gateway, an editor running a text-only
  model, a local model without vision. The image never reaches a model that can
  actually see it — it comes back as a `[Unsupported Image]` placeholder or
  nothing at all.
- Even with a vision-capable model, different products are locked to different
  providers, so "can this assistant see my screenshot?" depends on which model
  it happens to be running.

No matter how you ask, a model that can't see can't help you look.

eyes.py fixes this the same way a human would: it takes the image, sends it
**straight to a vision-capable model API** — Claude, GPT, Grok, or Gemini — and
reads back the words, regardless of which model your assistant is running on.

```
┌─────────────────┐   path + prompt    ┌─────────┐   base64 image   ┌───────────────────┐
│  Your AI        │ ─────────────────▶ │ eyes.py │ ───────────────▶ │  a vision API     │
│  assistant      │                    │         │                  │  Claude / GPT /   │
│  (no vision)    │ ◀───────────────── │         │ ◀─────────────── │  Grok / Gemini    │
└─────────────────┘   plain text reply └─────────┘    description    └───────────────────┘
```

## Why eyes.py instead of a normal API call

| Problem | How eyes.py handles it |
|---|---|
| Your editor injects its own `ANTHROPIC_*` / other env vars for gateway routing | Reads keys from `.env` **before** the environment, so a gateway key never shadows yours |
| Which provider am I talking to? | Auto-detects from the key prefix (`sk-ant-api-…` → Claude, `sk-proj-…` → GPT, `xai-…` → Grok, `AIza…` → Gemini), or force it with `--provider` |
| Windows console can't print `ă`, `ş` etc. (cp1252) | Forces stdout/stderr to UTF-8 |
| No SDK knowledge needed | Two deps: `pip install anthropic pillow` (OpenAI / Grok / Gemini talk plain HTTP via the standard library) |

## Make it yours — this is just the idea

Both files are tiny, plain Python — a starting point, not a finished product.
Everything is meant to be edited:

- **Models**: `PROVIDER_DEFAULTS` (vision) and `IMAGE_MODELS` (generation) at
  the top of `eyes.py`. Model IDs change — check each provider and adjust.
- **Add a provider**: every provider is one small function; copy the pattern of
  `call_openai_compatible` or `call_gemini`.
- **Ask your AI**: because the whole thing is two small files, you can even just
  tell your AI assistant to adapt and configure `capture.py` and `eyes.py` for
  you. What's here is the seed of an idea — build on it.

## Requirements

- Python 3.9+
- `pip install anthropic pillow` (pillow is only used by the optional `capture.py`)
- An API key for at least one supported provider:

| Provider | Key prefix | Get one at |
|---|---|---|
| Claude (Anthropic) | `sk-ant-api03-…` | <https://platform.claude.com/settings/keys> |
| GPT (OpenAI) | `sk-proj-…` / `sk-svc-…` | <https://platform.openai.com/api-keys> |
| Grok (xAI) | `xai-…` | <https://console.x.ai> |
| Gemini (Google) | `AIza…` | <https://aistudio.google.com/apikey> |

## Setup (2 minutes)

**1. Install the dependencies:**

```bash
pip install anthropic pillow
```

**2. Create a `.env` file next to eyes.py — one line, nothing else:**

```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY" > .env
```

No quotes, no spaces around `=`, one line. (Or in VS Code: **New File** → name it
exactly `.env` → paste the line → **Save**.)

Use the matching line for your provider:

| Provider | Line to put in `.env` |
|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY=sk-ant-api03-...` |
| GPT (OpenAI) | `OPENAI_API_KEY=sk-proj-...` |
| Grok (xAI) | `XAI_API_KEY=xai-...` |
| Gemini (Google) | `GEMINI_API_KEY=AIza...` |

That's it. Keep `.env` local — never upload or share it.

## Usage

```bash
# Generic detailed description (provider auto-detected from your key)
python eyes.py screenshot.png

# Ask a specific question
python eyes.py screenshot.png "Where is the alignment broken? Transcribe all buttons."

# Force a provider / pick a model
python eyes.py ui.png --provider anthropic --model claude-opus-5
python eyes.py ui.png --provider openai --model gpt-4o
python eyes.py ui.png --provider grok
python eyes.py ui.png --provider gemini --model gemini-2.5-pro

# Explicit key / custom endpoint (overrides everything)
python eyes.py ui.png --api-key sk-proj-... --provider openai
python eyes.py ui.png --api-key sk-ant-api03-... --base-url https://api.anthropic.com

# Generate an image (needs an openai / grok / gemini key)
python eyes.py --create "a logo: an eye with a lightning bolt" --provider openai
python eyes.py --create "futuristic landing page, dark theme" --provider grok

# See which provider/model/key was resolved
python eyes.py ui.png --verbose
```

### From inside your coding assistant (e.g. Claude Code)

Point the assistant at eyes.py, e.g. when reviewing a screenshot:

> "Run `python eyes.py screenshots/home.png "Check the navbar alignment and list every color used"` and use the result."

The assistant runs the command, reads the description as text, and reasons
about it — the image never has to reach the assistant's own model.

## Create images too (`--create`)

eyes.py can also **generate** images, not just describe them:

```bash
python eyes.py --create "a logo: an eye with a lightning bolt" --provider openai
python eyes.py --create "futuristic landing page, dark theme" --provider grok
python eyes.py --create "minimalist poster" --provider gemini --size 1024x1024
```

The image is saved to `generated/` (or `--out <path>`).

**Which providers can generate?** Only the ones with an image-generation model:

| Provider | Default `--create` model | Notes |
|---|---|---|
| OpenAI | `gpt-5.6` | Edit in `IMAGE_MODELS` if your current ID differs |
| Grok (xAI) | `grok-image-1.5` | Grok rejects the `size` arg — handled automatically |
| Gemini | `imagen-3.0-generate-002` | |
| Claude | — | ⚠️ Anthropic has **no** image-generation API |

All models live in one editable place — `IMAGE_MODELS` at the top of
`eyes.py`. Check each provider's current model list and adjust freely.

## Bonus: capture.py — show eyes.py your screen

Don't have the image as a file, or just want to point at what's on your screen?
`capture.py` grabs the screen into `screenshots/` and pairs with eyes.py:

```bash
python capture.py                      # → screenshots/capture-<timestamp>.png
python capture.py --name github.png    # → screenshots/github.png
python capture.py --send               # capture + analyze via eyes.py in one go
```

Requires `pillow`. (Pasting an image into a chat usually does **not** save it
to disk anywhere, so `capture.py` is the reliable way to "show" eyes.py
something.)

## Bonus: clipwatch.py — auto-save images you copy

Copy or screenshot an image and it lands in `screenshots/` automatically,
ready for eyes.py. Each one is saved separately, no overwrites.

```bash
python clipwatch.py                    # watch the clipboard until stopped (Ctrl+C)
```

Then copy or screenshot as many images as you want — each becomes
`screenshots/clipboard-<timestamp>.png`. Tell eyes.py which one to look at.

Requires `pillow`. Handy when pasting an image into a chat does **not** save it
to disk: this catches it straight from the clipboard instead.

## Vision-capable models

| Provider | Default model | Other good options |
|---|---|---|
| Claude (Anthropic) | `claude-sonnet-5` | `claude-opus-5`, `claude-haiku-4-5` |
| GPT (OpenAI) | `gpt-4o` | `gpt-4o-mini`, `gpt-4.1` |
| Grok (xAI) | `grok-2-vision-1212` | pass your exact ID with `--model` |
| Gemini (Google) | `gemini-2.5-flash` | `gemini-2.5-pro` |

Supported image formats: PNG, JPEG, GIF, WebP, BMP (any type `mimetypes`
recognizes as `image/*`). If the MIME type can't be detected, force it with
`--media-type image/png`.

## How the provider and key are resolved

1. `--provider` forces a provider; otherwise it's **auto-detected** from the key prefix.
2. Key priority: `--api-key` → `.env` file → environment variables (per provider: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` / `GROK_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`).
3. When several keys exist and provider is `auto`, the scan order is: Anthropic → OpenAI → Grok → Gemini.

The `.env` file deliberately beats the environment: when running inside an
assistant that injects its own API-related variables for gateway routing, that
injected value must not shadow the key eyes.py uses for the real API.

## Go fully local (Ollama) — no cloud, no real keys

You can even go fully local: install a local vision model (via Ollama) and
point eyes.py at its endpoint. DeepSeek keeps coding, a model on your own
machine does the looking. No cloud, no API keys, fully offline.

```bash
# 1. Install Ollama and a local vision model
ollama pull llava        # or: gemma3, moondream, qwen2-vl, ...
ollama serve

# 2. Point eyes.py at the local endpoint (Ollama ignores the key,
#    so any placeholder works)
python eyes.py photo.png --provider openai --base-url http://localhost:11434/v1 --model llava --api-key local
```

Run DeepSeek locally too and the whole stack stays on your machine.

## Security notes

- **Never upload or share `.env`** — it holds your API keys and must stay
  local, next to eyes.py.
- If a key is ever pasted into a chat/log you don't control, **rotate it** at
  the provider's console and update `.env`.
- Images are sent to the provider's API over HTTPS. Don't use this tool on
  images that must never leave your machine.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 API key is invalid` | Wrong / revoked key, or key from a different provider | Use a key that matches `--provider`; check the `.env` entry |
| `could not auto-detect the provider` | Key prefix isn't recognized | Pass `--provider {anthropic|openai|grok|gemini}` |
| Model answers `[Unsupported Image]` | Request went to a non-vision gateway | `--provider` / `--base-url` are wrong; eyes.py should hit a real vision API |
| `--create` says "Claude can't generate" | Your key is Anthropic | Use an OpenAI / Grok / Gemini key with `--provider` |
| `404 model ... not found` | Typo in `--model`, or model ID no longer exists | Check the provider's current model list |
| `429 rate limited` | Hit your rate limit | Wait, or use a smaller/cheaper model |
| Garbled / `cp1252` characters | Windows console | Run with the current version (UTF-8 forced automatically) |
| `no API key found` | `.env` missing or empty | Create a `.env` file with `ANTHROPIC_API_KEY=sk-ant-...` |

## License

MIT — do whatever you like. If it saves you time, say hi to whoever shared it
with you. 🚀

## Let's connect

Follow me on X: [@NBSCToken](https://x.com/NBSCToken)
