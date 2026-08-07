# 👁️ eyes.py — real vision for your AI

A tiny tool that gives an AI coding assistant **real eyes**: it sends an image
to a vision-capable model and prints the description as plain text that the
assistant can read back.

**Provider-agnostic.** Works with **Claude, GPT, Grok, or Gemini** — the
provider is auto-detected from your API key. No key or model is hardcoded.

---

## The problem it solves

Coding assistants (Claude Code, Copilot, Cursor, and others) can describe
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

```bash
# 1. Install the dependencies
pip install anthropic pillow

# 2. Create a file named .env next to eyes.py and paste your key(s), e.g.:
#    ANTHROPIC_API_KEY=sk-ant-api03-...
#    (or OPENAI_API_KEY, XAI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY)
```

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

# See which provider/model/key was resolved
python eyes.py ui.png --verbose
```

### From inside your coding assistant (e.g. Claude Code)

Point the assistant at eyes.py, e.g. when reviewing a screenshot:

> "Run `python eyes.py screenshots/home.png "Check the navbar alignment and list every color used"` and use the result."

The assistant runs the command, reads the description as text, and reasons
about it — the image never has to reach the assistant's own model.

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
| `404 model ... not found` | Typo in `--model`, or model ID no longer exists | Check the provider's current model list |
| `429 rate limited` | Hit your rate limit | Wait, or use a smaller/cheaper model |
| Garbled / `cp1252` characters | Windows console | Run with the current version (UTF-8 forced automatically) |
| `no API key found` | `.env` missing or empty | Create a `.env` file with `ANTHROPIC_API_KEY=sk-ant-...` |

## License

MIT — do whatever you like. If it saves you time, say hi to whoever shared it
with you. 🚀

## Let's connect

Follow me on X: [@NBSCToken](https://x.com/NBSCToken)
