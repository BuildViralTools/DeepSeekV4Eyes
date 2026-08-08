# AGENTS.md

Instructions for AI coding assistants working in this repo.

This project gives you (an AI assistant) real eyes. Use these tools whenever the
user shows you an image, points at a screenshot, pastes a picture, or asks what
is in an image. The tools are plain Python, so you can also adapt or extend them
(see `README.md`).

## The tools

| Tool | What it does |
|---|---|
| `eyes.py` | Describes or creates images via a vision model (Claude / GPT / Grok / Gemini). Provider auto-detected from the API key. |
| `capture.py` | Captures the screen into `screenshots/`. |
| `clipwatch.py` | Watches the clipboard and auto-saves copied / screenshotted images into `screenshots/`. |

## Workflows

### 1. Describe an image file

```bash
python eyes.py <image> "what to look for"
```

Add `--provider`, `--model`, `--size`, or `--verbose` as needed.

### 2. The user pasted an image in chat and you see "[Unsupported Image]"

Pasted images do NOT reach the model and are not saved by the chat. Instead,
`clipwatch.py` saves anything the user copies to the clipboard into
`screenshots/clipboard-*.png`. Check for the newest one and describe it:

```bash
# newest captured image
NEWEST=$(ls -t screenshots/clipboard-*.png 2>/dev/null | head -1)
if [ -n "$NEWEST" ]; then
  python eyes.py "$NEWEST" "describe this image in detail, transcribing any text exactly"
fi
```

If `screenshots/` is empty, ask the user to copy/screenshot the image first
(or to bring it on screen so you can run `capture.py`).

### 3. Capture the screen and describe it in one step

```bash
python capture.py --send "what to look for"
```

### 4. Create an image

```bash
python eyes.py --create "a logo: an eye with a lightning bolt" --provider openai
```

Claude (Anthropic) has no image-generation API; `--create` needs an OpenAI,
Grok, or Gemini key.

## Notes

- `.env` holds the API key(s). Never commit, upload, or share it.
- Captured/copied images pile up in `screenshots/` — clean up old ones when they
  accumulate.
- If eyes.py reports a missing key, ask the user to create `.env` (one line:
  `ANTHROPIC_API_KEY=sk-ant-...`, or the matching `OPENAI_API_KEY` /
  `XAI_API_KEY` / `GEMINI_API_KEY`).
