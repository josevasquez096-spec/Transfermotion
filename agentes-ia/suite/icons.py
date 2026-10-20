"""Iconos de las apps, dibujados con Pillow (sin archivos binarios en el repositorio)."""

from PIL import Image, ImageDraw, ImageFont


def _font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def make_icon(text, accent, size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 16
    draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=size // 5, fill=accent)
    # pequeño destello de "IA" en la esquina
    r = size // 9
    cx, cy = size - pad - r - size // 14, pad + r + size // 14
    draw.polygon(
        [(cx, cy - r), (cx + r // 3, cy - r // 3), (cx + r, cy), (cx + r // 3, cy + r // 3),
         (cx, cy + r), (cx - r // 3, cy + r // 3), (cx - r, cy), (cx - r // 3, cy - r // 3)],
        fill="white",
    )
    font = _font(int(size * (0.42 if len(text) <= 2 else 0.32)))
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1] + size * 0.04), text, font=font, fill="white")
    return img


def save_ico(text, accent, path):
    make_icon(text, accent).save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
