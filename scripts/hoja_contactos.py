"""Une los PNG de render_expresiones.py en una hoja de contactos con el nombre de cada expresión.

    python scripts/hoja_contactos.py carpeta_pngs hoja.png [--cols 8]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    p = argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--cols", type=int, default=8)
    a = p.parse_args()
    files = sorted(a.folder.glob("*.png"), key=lambda f: (not f.stem.startswith("00_"), f.stem.lower()))
    files = [f for f in files if f.resolve() != a.out.resolve()]
    first = Image.open(files[0])
    w, h = first.size
    label = 22
    rows = (len(files) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * w, rows * (h + label)), (24, 28, 34))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for i, f in enumerate(files):
        x, y = (i % a.cols) * w, (i // a.cols) * (h + label)
        sheet.paste(Image.open(f).convert("RGB"), (x, y + label))
        draw.text((x + 6, y + 3), f.stem.replace("00_", ""), fill=(230, 237, 243), font=font)
    sheet.save(a.out)
    print(f"{a.out}  ({len(files)} expresiones, {sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    main()
