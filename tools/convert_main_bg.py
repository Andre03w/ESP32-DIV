#!/usr/bin/env python3
"""Convert an input image to 1-bit 211x280 main-menu background and patch skull_bg.h.
Usage:
  python tools/convert_main_bg.py input_image.png [--threshold 145] [--invert]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from PIL import Image, ImageOps
except Exception as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: pip install pillow") from exc

WIDTH = 211
HEIGHT = 280


def image_to_bytes(path: Path, threshold: int, invert: bool) -> list[int]:
    img = Image.open(path).convert("L")
    img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    if invert:
        img = ImageOps.invert(img)
    bw = img.point(lambda p: 255 if p >= threshold else 0, mode="1")

    px = bw.load()
    data: list[int] = []
    # XBM-style row packing used by TFT drawBitmap (left-to-right, 8 pixels per byte)
    row_bytes = (WIDTH + 7) // 8
    for y in range(HEIGHT):
        for bx in range(row_bytes):
            b = 0
            x0 = bx * 8
            for i in range(8):
                x = x0 + i
                if x < WIDTH and px[x, y] == 0:
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


def patch_skull_bg(skull_bg_h: Path, data: list[int]) -> None:
    text = skull_bg_h.read_text()
    pattern = re.compile(
        r"(#define SKULL_BG_WIDTH\s+211\s*\n#define SKULL_BG_HEIGHT\s+280\s*\n\s*const unsigned char skull_bg_bitmap\[\]\s*PROGMEM\s*=\s*\{)(.*?)(\n\};)",
        re.S,
    )
    body = "\n" + format_array(data)
    new_text, count = pattern.subn(r"\1" + body + r"\3", text)
    if count != 1:
        raise SystemExit("Could not find skull_bg_bitmap[] in skull_bg.h")
    skull_bg_h.write_text(new_text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--threshold", type=int, default=145)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--skull-bg", type=Path, default=Path("skull_bg.h"))
    parser.add_argument("--preview", type=Path, default=Path("tools/main_bg_preview_bw.png"))
    args = parser.parse_args()

    data = image_to_bytes(args.image, args.threshold, args.invert)
    patch_skull_bg(args.skull_bg, data)

    img = Image.open(args.image).convert("L")
    img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    if args.invert:
        img = ImageOps.invert(img)
    bw = img.point(lambda p: 255 if p >= args.threshold else 0, mode="1")
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    bw.save(args.preview)

    print(f"Updated {args.skull_bg} with {len(data)} bytes for skull_bg_bitmap")
    print(f"Preview written to {args.preview}")


if __name__ == "__main__":
    main()
