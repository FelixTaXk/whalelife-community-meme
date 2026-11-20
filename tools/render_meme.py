# -*- coding: utf-8 -*-
"""给一张图加字幕 / 气泡 / 描边，做成表情包。

来自鱼仔 tools/make_meme_*.py 的做法，改成脚本化：stdin 收 JSON，stdout 回 JSON。
用法：
    echo {"input":"...","output":"...","text":"就这？","style":"band"} | python render_meme.py
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def font(size):
    for path in FONTS:
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def measure(draw, text, f):
    box = draw.textbbox((0, 0), text, font=f)
    return box[2] - box[0], box[3] - box[1]


def wrap(draw, text, f, max_width):
    """按像素宽度折行；已经有 \n 的先按 \n 分段。"""
    paragraphs = [p for p in str(text).split("\n")]
    lines = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        cur = ""
        for ch in p:
            trial = cur + ch
            w, _ = measure(draw, trial, f)
            if w <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines or [str(text)]


def fit(draw, text, max_width, start=46, minimum=26):
    size = start
    while size > minimum:
        f = font(size)
        lines = wrap(draw, text, f, max_width)
        width = max(measure(draw, line, f)[0] for line in lines)
        if width <= max_width:
            return f, lines
        size -= 2
    return font(minimum), wrap(draw, text, font(minimum), max_width)


def resize_width(img, width):
    if img.width == width:
        return img.copy()
    height = max(1, round(img.height * width / img.width))
    return img.resize((width, height), Image.LANCZOS)


def render(req):
    src = req.get("input")
    out = req.get("output")
    text = str(req.get("text") or "").strip()
    style = str(req.get("style") or "band")
    width = int(req.get("width") or 512)
    if not src or not os.path.exists(src):
        raise SystemExit("input missing")
    if not text:
        raise SystemExit("text empty")
    if width < 256 or width > 1600:
        width = 512

    img = Image.open(src)
    img.seek(0)
    img = img.convert("RGBA")
    base = resize_width(img, width)
    W, H = base.size

    if style == "band" or style == "top":
        probe = ImageDraw.Draw(Image.new("RGB", (W, 64)))
        f, lines = fit(probe, text, W - 40, 44, 24)
        lh = int(f.size * 1.35)
        band = 24 + lh * len(lines)
        canvas = Image.new("RGB", (W, H + band), (255, 255, 255))
        if style == "band":
            canvas.paste(base.convert("RGB"), (0, 0))
            origin_y = H
        else:
            canvas.paste(base.convert("RGB"), (0, band))
            origin_y = 0
        d = ImageDraw.Draw(canvas)
        y = origin_y + 12
        for line in lines:
            w, _ = measure(d, line, f)
            d.text(((W - w) // 2, y), line, font=f, fill=(24, 24, 24))
            y += lh

    elif style == "bubble":
        probe = ImageDraw.Draw(Image.new("RGB", (W, 64)))
        f, lines = fit(probe, text, int(W * 0.78), 40, 22)
        lh = int(f.size * 1.35)
        pad_x, pad_y = 22, 16
        text_w = max(measure(probe, line, f)[0] for line in lines)
        box_w = min(W - 16, text_w + pad_x * 2)
        box_h = lh * len(lines) + pad_y * 2
        canvas = base.convert("RGBA")
        d = ImageDraw.Draw(canvas)
        left = (W - box_w) // 2
        top = H - box_h - 26
        d.rounded_rectangle(
            [left, top, left + box_w, top + box_h],
            radius=18,
            fill=(255, 255, 255, 255),
            outline=(20, 20, 20, 255),
            width=4,
        )
        # 尾巴画在气泡之后，顶边和气泡底边重合，不再多出一条横线
        cx = W // 2
        d.polygon(
            [(cx - 15, top + box_h + 1), (cx + 15, top + box_h + 1), (cx, top + box_h + 18)],
            fill=(255, 255, 255, 255),
            outline=(20, 20, 20, 255),
            width=4,
        )
        y = top + pad_y
        for line in lines:
            w, _ = measure(d, line, f)
            d.text(((W - w) // 2, y), line, font=f, fill=(18, 18, 18, 255))
            y += lh

    else:  # plain：只描边，不挡画面
        probe = ImageDraw.Draw(Image.new("RGB", (W, 64)))
        f, lines = fit(probe, text, W - 48, 52, 28)
        lh = int(f.size * 1.3)
        canvas = base.convert("RGBA")
        d = ImageDraw.Draw(canvas)
        y = H - lh * len(lines) - 18
        for line in lines:
            w, _ = measure(d, line, f)
            d.text(
                ((W - w) // 2, y), line, font=f, fill=(255, 255, 255, 255),
                stroke_width=max(4, f.size // 7), stroke_fill=(0, 0, 0, 255),
            )
            y += lh

    folder = os.path.dirname(out)
    if folder:
        os.makedirs(folder, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    return {
        "ok": True,
        "path": out,
        "width": canvas.width,
        "height": canvas.height,
        "bytes": os.path.getsize(out),
        "style": style,
    }


if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
        result = render(payload)
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
    except SystemExit as e:
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        sys.stdout.write(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
