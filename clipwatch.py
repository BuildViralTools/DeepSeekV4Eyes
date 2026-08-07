#!/usr/bin/env python3
"""clipwatch.py — watch the Windows clipboard and auto-save images to screenshots/.

Pairs with eyes.py. When you copy or screenshot an image, it lands in
screenshots/ as clipboard-<timestamp>.png automatically, so eyes.py can
describe it even though pasting images into a chat does not save them.

Usage:
    python clipwatch.py          # watch until stopped (Ctrl+C)

Requires: pip install pillow
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageGrab

OUT_DIR = Path(__file__).resolve().parent / "screenshots"
POLL_SECONDS = 1.0


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    print(f"clipwatch: watching clipboard for images -> {OUT_DIR}  (Ctrl+C to stop)")
    last = None
    while True:
        try:
            clip = ImageGrab.grabclipboard()
        except Exception as exc:  # clipboard can be busy; don't crash the loop
            print(f"clipwatch: clipboard read failed: {exc}")
            time.sleep(POLL_SECONDS)
            continue
        if isinstance(clip, Image.Image):
            key = clip.tobytes()
            if key != last:
                last = key
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                path = OUT_DIR / f"clipboard-{stamp}.png"
                clip.save(path)
                print(f"clipwatch: saved {path.name}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
