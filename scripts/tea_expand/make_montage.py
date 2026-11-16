from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from download_images import UPLOAD_DIR, safe_filename
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from __init__ import ALL_TEAS

FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
CELL_W, CELL_H = 240, 190
COLS, ROWS = 6, 10
PER_SHEET = COLS * ROWS

names = [t["name"] for t in ALL_TEAS]
sheets = [names[i:i + PER_SHEET] for i in range(0, len(names), PER_SHEET)]

out_dir = Path(__file__).resolve().parent / "montage"
out_dir.mkdir(exist_ok=True)

for idx, chunk in enumerate(sheets, 1):
    canvas = Image.new("RGB", (CELL_W * COLS, CELL_H * ROWS), (250, 250, 250))
    draw = ImageDraw.Draw(canvas)
    for i, name in enumerate(chunk):
        r, c = divmod(i, COLS)
        x, y = c * CELL_W, r * CELL_H
        path = UPLOAD_DIR / f"{safe_filename(name)}.jpg"
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((CELL_W - 8, CELL_H - 26))
            canvas.paste(img, (x + (CELL_W - img.width) // 2, y + 4))
        except Exception:
            draw.rectangle([x + 4, y + 4, x + CELL_W - 4, y + CELL_H - 26], fill=(220, 200, 200))
        draw.text((x + 4, y + CELL_H - 22), name, fill=(20, 20, 20), font=FONT)
    out = out_dir / f"sheet{idx}.jpg"
    canvas.save(out, "JPEG", quality=82)
    print(out, len(chunk))
