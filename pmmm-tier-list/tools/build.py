"""Render standardized 2:3 tier-list cards with a lower-third caption.

usage: python3 -I build.py <src_dir> <out_dir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest import ITEMS  # noqa: E402

W, H = 400, 600
SIDE = 20           # horizontal text padding
BOTTOM = 20         # space under the last title line
FONT_DIR = "/usr/share/fonts/opentype/inter"
TITLE_FONT = os.path.join(FONT_DIR, "Inter-ExtraBold.otf")
KICKER_FONT = os.path.join(FONT_DIR, "Inter-Bold.otf")
PINK = (255, 122, 178)


def crop_to_ratio(im, fx, fy):
    w, h = im.size
    target = W / H
    if w / h > target:
        cw, ch = round(h * target), h
    else:
        cw, ch = w, round(w / target)
    x = min(max(round(fx * w - cw / 2), 0), w - cw)
    y = min(max(round(fy * h - ch / 2), 0), h - ch)
    return im.crop((x, y, x + cw, y + ch))


def transparent_on_backdrop(im):
    """Cut-out character art: place it large and top-aligned on a soft pink gradient."""
    bg = Image.new("RGB", (W, H))
    top, bottom = (253, 236, 243), (226, 120, 160)
    px = bg.load()
    for y in range(H):
        t = y / (H - 1)
        c = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    scale = (H * 1.28) / im.height
    fig = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    shadow = Image.new("RGBA", fig.size, (90, 20, 50, 0))
    shadow.putalpha(fig.getchannel("A").point(lambda a: a * 0.35))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    x = (W - fig.width) // 2
    bg.paste(shadow, (x + 8, 22), shadow)
    bg.paste(fig, (x, 12), fig)
    return bg


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def balance(draw, text, font, max_w):
    """Two-line titles read better when both lines are similar in length."""
    words = text.split()
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        wa, wb = draw.textlength(a, font=font), draw.textlength(b, font=font)
        if max(wa, wb) <= max_w and (best is None or max(wa, wb) < best[0]):
            best = (max(wa, wb), [a, b])
    return best[1] if best else None


def fit_title(draw, text):
    max_w = W - 2 * SIDE
    if "\n" in text:  # manual break from the manifest
        lines = text.split("\n")
        for size in range(40, 21, -1):
            font = ImageFont.truetype(TITLE_FONT, size)
            if max(draw.textlength(l, font=font) for l in lines) <= max_w:
                return font, lines
    for size in range(42, 33, -1):
        font = ImageFont.truetype(TITLE_FONT, size)
        if draw.textlength(text, font=font) <= max_w:
            return font, [text]
    for size in range(38, 23, -1):
        font = ImageFont.truetype(TITLE_FONT, size)
        lines = balance(draw, text, font, max_w)
        if lines:
            return font, lines
    font = ImageFont.truetype(TITLE_FONT, 24)
    return font, wrap(draw, text, font, max_w)


def spaced_text(draw, xy_center, text, font, fill, tracking):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = xy_center[0] - total / 2
    for ch, cw in zip(text, widths):
        draw.text((x, xy_center[1]), ch, font=font, fill=fill)
        x += cw + tracking


def lower_third(card, kicker, title):
    card = card.convert("RGBA")
    probe = ImageDraw.Draw(card)
    font, lines = fit_title(probe, title)
    asc, desc = font.getmetrics()
    line_h = round((asc + desc) * 1.02)
    kfont = ImageFont.truetype(KICKER_FONT, 14)
    k_h = 14
    gap = 9
    block_h = k_h + gap + line_h * len(lines)
    top = H - BOTTOM - block_h

    # Scrim: transparent above the caption, ramping to a near-solid band behind the text.
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    ramp_start, solid_start = top - 95, top - 18
    for y in range(max(ramp_start, 0), H):
        if y < solid_start:
            t = (y - ramp_start) / (solid_start - ramp_start)
            a = round(222 * t ** 1.4)
        else:
            a = 222 + round(20 * (y - solid_start) / max(H - solid_start, 1))
        sd.line([(0, y), (W, y)], fill=(12, 6, 18, a))
    card = Image.alpha_composite(card, scrim)

    d = ImageDraw.Draw(card)
    bar_w = 34
    d.rounded_rectangle([(W - bar_w) / 2, top - 12, (W + bar_w) / 2, top - 9], radius=2, fill=PINK + (255,))
    spaced_text(d, (W / 2, top - 2), kicker, kfont, PINK + (255,), 2.6)
    y = top + k_h + gap
    for line in lines:
        lw = d.textlength(line, font=font)
        x = (W - lw) / 2
        d.text((x, y + 2), line, font=font, fill=(0, 0, 0, 150))
        d.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h
    return card.convert("RGB")


def build(src_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for n, (slug, kicker, title, src, focus, _credit) in enumerate(ITEMS, 1):
        im = Image.open(os.path.join(src_dir, src))
        if len(focus) == 4:
            im, (fx, fy) = im.crop(focus), (0.5, 0.5)
        else:
            fx, fy = focus
        if im.mode in ("RGBA", "LA", "P") and "A" in im.convert("RGBA").getbands() and \
                im.convert("RGBA").getchannel("A").getextrema()[0] < 250:
            card = transparent_on_backdrop(im.convert("RGBA"))
        else:
            card = crop_to_ratio(im.convert("RGB"), fx, fy).resize((W, H), Image.LANCZOS)
        card = lower_third(card, kicker, title)
        out = os.path.join(out_dir, f"{n:02d}-{slug}.jpg")
        card.save(out, quality=92, optimize=True, progressive=True)
        print(out)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
