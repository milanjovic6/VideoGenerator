from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True  # izbegava pad kod oštećenih slika

# === PUTEVI =================================================================
SRC_DIR = Path(r"C:\Users\milan\Desktop\Anime World\Slike")
CSV_PATH = Path(r"C:\Users\milan\Desktop\Anime World\captions.csv")
OUT_DIR = Path(r"C:\Users\milan\Desktop\Anime World\Out")
OUT_DIR.mkdir(exist_ok=True, parents=True)

# === KONFIGURACIJA ==========================================================
TARGET_W, TARGET_H = 1080, 1920
PAD_H = 660  # visina donjeg crnog pojasa

# === FONTOVI ================================================================
default_font = ImageFont.load_default()
FONTS = {
    "title":    ImageFont.load_default(),
    "subtitle": ImageFont.load_default(),
    "body":     ImageFont.load_default(),
}


def process_image(src_path: Path, title: str, subtitle: str, body: str, dst_path: Path):
    # Automatska konverzija webp u jpg
    if src_path.suffix.lower() == ".webp":
        try:
            temp_img = Image.open(str(src_path)).convert("RGB")
            src_jpg = src_path.with_suffix(".jpg")
            temp_img.save(str(src_jpg), quality=95)
            print(f"[webp→jpg] {src_path.name} konvertovan u {src_jpg.name}")
            src_path = src_jpg  # zameni putanju za nastavak obrade
        except Exception as e:
            print(f"[ERROR webp] {src_path.name}: {e}")
            return

    try:
        img = Image.open(str(src_path)).convert("RGB")
    except Exception as e:
        print(f"[ERROR] {src_path.name}: {e}")
        return

    content_h = TARGET_H - PAD_H
    ratio = min(TARGET_W / img.width, content_h / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img_rs = img.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGB", (TARGET_W, TARGET_H), "black")
    x_off = (TARGET_W - new_size[0]) // 2
    y_off = (content_h - new_size[1]) // 2
    canvas.paste(img_rs, (x_off, y_off))

    draw = ImageDraw.Draw(canvas)
    cur_y = content_h + 20

    for txt, key, gap in [
        (title, "title", 18),
        (subtitle, "subtitle", 10),
        (body, "body", 6),
    ]:
        if not txt:
            continue
        for line in str(txt).splitlines():
            w, h = draw.textbbox((0, 0), line, font=FONTS[key])[2:]
            draw.text(((TARGET_W - w) // 2, cur_y), line,
                      font=FONTS[key], fill="white")
            cur_y += h + gap

    canvas.save(str(dst_path), quality=95)
    print(f"[OK] {src_path.name} → {dst_path.name}")


if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip().str.lower()

    if 'filename' not in df.columns:
        raise ValueError("CSV mora da sadrži kolonu 'filename'")

    for _, row in df.iterrows():
        src = SRC_DIR / row['filename']
        dst = OUT_DIR / src.with_suffix(".jpg").name
        process_image(
            src_path=src,
            title=row.get("title", ""),
            subtitle=row.get("subtitle", ""),
            body=row.get("body", ""),
            dst_path=dst
        )

    print(f"\n✓ Završeno: {len(df)} slika obrađeno.\nOutput: {OUT_DIR}")
