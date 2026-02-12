#!/usr/bin/env python3
"""Convert an input image to 1-bit 240x320 splash bitmap and patch icon.h.
Usage:
  python tools/convert_splash.py input_image.png [--threshold 145] [--invert]
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

try:
    from PIL import Image, ImageOps
except Exception as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: pip install pillow") from exc

WIDTH = 240
HEIGHT = 320


def image_to_bytes(path: Path, threshold: int, invert: bool) -> list[int]:
    img = Image.open(path).convert("L")
    img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    if invert:
        img = ImageOps.invert(img)
    bw = img.point(lambda p: 255 if p >= threshold else 0, mode="1")

    px = bw.load()
    data: list[int] = []
    for y in range(HEIGHT):
        for x0 in range(0, WIDTH, 8):
            b = 0
            for i in range(8):
                x = x0 + i
                # For drawBitmap: set bit=1 to draw foreground pixel
                if px[x, y] == 0:
                    b |= 1 << (7 - i)
            data.append(b)
    return data


def format_array(data: list[int]) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        line = "  " + ", ".join(f"0x{b:02X}" for b in chunk)
        if i + 16 < len(data):
            line += ","
        lines.append(line)
    return "\n".join(lines)


def patch_icon_h(icon_h: Path, data: list[int]) -> None:
    text = icon_h.read_text()
    pattern = re.compile(
        r"(#define HALEHOUND_SPLASH_WIDTH\s+240\s*\n#define HALEHOUND_SPLASH_HEIGHT\s+320\s*\nconst unsigned char bitmap_halehound_splash\[\]\s*PROGMEM\s*=\s*\{)(.*?)(\n\};)",
        re.S,
    )
    body = "\n" + format_array(data)
    new_text, count = pattern.subn(r"\1" + body + r"\3", text)
    if count != 1:
        raise SystemExit("Could not find bitmap_halehound_splash[] in icon.h")
    icon_h.write_text(new_text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--threshold", type=int, default=145)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--icon-h", type=Path, default=Path("icon.h"))
    parser.add_argument("--preview", type=Path, default=Path("tools/splash_preview_bw.png"))
    args = parser.parse_args()

    data = image_to_bytes(args.image, args.threshold, args.invert)
    patch_icon_h(args.icon_h, data)

    # Save preview for quick visual check
    img = Image.open(args.image).convert("L")
    img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    if args.invert:
        img = ImageOps.invert(img)
    bw = img.point(lambda p: 255 if p >= args.threshold else 0, mode="1")
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    bw.save(args.preview)

    print(f"Updated {args.icon_h} with {len(data)} bytes for bitmap_halehound_splash")
    print(f"Preview written to {args.preview}")


if __name__ == "__main__":
    main()
