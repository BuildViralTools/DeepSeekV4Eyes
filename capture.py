#!/usr/bin/env python3
"""capture.py — capture the screen into the screenshots/ folder.

Pairs with eyes.py: whatever is on your screen right now becomes an image file
that eyes.py can describe. (Pasting an image into a chat does NOT save it to
disk, so this is the reliable way to "show" eyes.py something.)

Usage:
    python capture.py                          # → screenshots/capture-<timestamp>.png
    python capture.py --name github.png        # → screenshots/github.png
    python capture.py --send                   # capture + analyze via eyes.py in one go

Requires: pip install pillow  (already present on this machine)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import ImageGrab
except ImportError:  # friendly error instead of a raw traceback
    sys.exit(
        "ERROR: missing dependency 'pillow'. Install it first:\n"
        "    pip install pillow"
    )

OUT_DIR = Path(__file__).resolve().parent / "screenshots"


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the screen into screenshots/.")
    parser.add_argument(
        "--name", default=None, help="Filename (default: capture-<timestamp>.png)"
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Also analyze the capture with eyes.py in the same command",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if args.name:
        out = OUT_DIR / args.name
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = OUT_DIR / f"capture-{stamp}.png"

    ImageGrab.grab().save(out)
    print(out)

    if args.send:
        eyes = Path(__file__).resolve().parent / "eyes.py"
        subprocess.run([sys.executable, str(eyes), str(out)], check=False)


if __name__ == "__main__":
    main()
