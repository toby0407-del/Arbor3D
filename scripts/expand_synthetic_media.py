#!/usr/bin/env python3
"""Expand synthetic demo media from existing PNGs + Fengchia field assets.

Creates labelled DEMO variants under:
  app/public/scans/_shared/synthetic-tree-evidence/{masks,cross-sections,point-clouds}/

Does not invent field evidence — every file is derived from checked-in sources
and stamped DEMO / SIMULATED.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "app" / "public" / "scans" / "_shared" / "synthetic-tree-evidence"
FENGCHIA = REPO / "app" / "public" / "scans" / "20260818092855"
FIELD = REPO / "app" / "public" / "scans" / "_shared" / "fengchia-field"

KINDS = {
    "masks": ("mask", EVIDENCE / "masks", FENGCHIA / "masks"),
    "cross-sections": ("cross-section", EVIDENCE / "cross-sections", FENGCHIA / "dbh"),
    "point-clouds": ("point-cloud", EVIDENCE / "point-clouds", FENGCHIA / "previews"),
}


def load_sources(kind: str, dest: Path, real_dir: Path) -> list[Image.Image]:
    images: list[Image.Image] = []
    for path in sorted(dest.glob("*.png")):
        images.append(Image.open(path).convert("RGBA"))
    if real_dir.exists():
        for path in sorted(real_dir.glob("*.png"))[:8]:
            images.append(Image.open(path).convert("RGBA"))
    if kind == "point-clouds" and (FIELD / "field-photo.jpg").exists():
        images.append(Image.open(FIELD / "field-photo.jpg").convert("RGBA"))
    if not images:
        raise FileNotFoundError(f"No source images for {kind}")
    return images


def stamp_demo(img: Image.Image, label: str) -> Image.Image:
    canvas = img.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    banner = "DEMO / SIMULATED — NOT FIELD EVIDENCE"
    # Dark translucent bar
    bar_h = max(28, canvas.height // 14)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, canvas.width, bar_h), fill=(20, 40, 28, 170))
    od.rectangle(
        (0, canvas.height - bar_h, canvas.width, canvas.height),
        fill=(20, 40, 28, 170),
    )
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), banner, fill=(230, 245, 220, 255), font=font)
    draw.text((10, canvas.height - bar_h + 8), label, fill=(200, 230, 180, 255), font=font)
    return canvas


def variant(src: Image.Image, index: int, kind: str) -> Image.Image:
    work = src.copy()
    # Deterministic transforms from index
    rotate = (index * 7) % 15 - 7
    work = work.rotate(rotate, expand=False, fillcolor=(30, 30, 30, 255))
    # Color / contrast
    work_rgb = work.convert("RGB")
    work_rgb = ImageEnhance.Color(work_rgb).enhance(0.85 + (index % 5) * 0.08)
    work_rgb = ImageEnhance.Contrast(work_rgb).enhance(0.9 + (index % 4) * 0.08)
    work_rgb = ImageEnhance.Brightness(work_rgb).enhance(0.88 + (index % 6) * 0.05)
    if index % 3 == 0:
        work_rgb = work_rgb.filter(ImageFilter.SMOOTH_MORE)
    if index % 4 == 1:
        work_rgb = ImageOps.autocontrast(work_rgb, cutoff=2)
    # Mild crop+zoom for variety
    w, h = work_rgb.size
    inset = 4 + (index % 5) * 3
    work_rgb = work_rgb.crop((inset, inset, w - inset, h - inset)).resize((w, h), Image.Resampling.LANCZOS)
    # Kind-specific tint
    tint = {
        "masks": (40, 120, 60),
        "cross-sections": (90, 70, 40),
        "point-clouds": (50, 80, 110),
    }[kind]
    tint_layer = Image.new("RGB", work_rgb.size, tint)
    work_rgb = Image.blend(work_rgb, tint_layer, 0.08 + (index % 4) * 0.02)
    return stamp_demo(work_rgb.convert("RGBA"), f"{kind} variant {index:02d}")


def build(count: int = 12) -> dict[str, int]:
    summary: dict[str, int] = {}
    for kind, (prefix, dest, real_dir) in KINDS.items():
        dest.mkdir(parents=True, exist_ok=True)
        sources = load_sources(kind, dest, real_dir)
        written = 0
        for i in range(1, count + 1):
            src = sources[(i - 1) % len(sources)]
            out = dest / f"{prefix}-{i:02d}.png"
            variant(src, i, kind).convert("RGB").save(out, "PNG", optimize=True)
            written += 1
        summary[kind] = written
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=12, help="Variants per kind (default 12)")
    args = parser.parse_args()
    summary = build(args.count)
    for kind, n in summary.items():
        print(f"{kind}: {n} files")
    print("done")


if __name__ == "__main__":
    main()
