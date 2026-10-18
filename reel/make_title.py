#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サムネ用のタイトルを透過 PNG に描く。

ffmpeg の drawtext はカラー絵文字（ビットマップフォント）を扱えず、
NotoColorEmoji を渡すと落ちる。Pillow なら embedded_color で描けるので、
文字と絵文字をまとめてここで作って、動画側には画像として重ねる。
縁取り・影・傾きもここで付けられる。

Pillow は /usr/bin/python3 (3.13) に入っている。実行もそれで。

    /usr/bin/python3 reel/make_title.py            -> reel/out/title.png
    TITLE_L1=... TITLE_L2=... TITLE_EMOJI=... で文言を差し替え
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

W = 1080                       # 動画と同じ幅で作る

# 丸ゴシック。おどけた見出し向き
FONT_MARU = "/usr/share/fonts/truetype/motoya-l-maruberi/MTLmr3m.ttf"
FONT_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
# NotoColorEmoji はビットマップで 109px にしか開けない。大きさは後で縮める
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJI_NATIVE = 109

ORANGE = (255, 140, 26, 255)
CREAM = (255, 248, 230, 255)
OUTLINE = (40, 16, 56, 255)     # 紫がかった黒。ハロウィンらしい縁取り

TITLE_L1 = os.environ.get("TITLE_L1", "ハロウィンコーデの")
TITLE_L2 = os.environ.get("TITLE_L2", "バイキング")
TITLE_EMOJI = os.environ.get("TITLE_EMOJI", "⁉🎃🧑‍🍳⁉")

# (文字列, フォント, 文字サイズ, 塗り, 縁の太さ, 傾き)
LINES = [
    (TITLE_L1, "maru", 82, CREAM, 11, -3.0),
    (TITLE_L2, "maru", 136, ORANGE, 15, 2.0),
    (TITLE_EMOJI, "emoji", 108, None, 0, -1.5),
]

GAP = 14                        # 行間
SHADOW = (0, 0, 0, 150)
SHADOW_OFFSET = (0, 9)


def font_path(kind):
    if kind == "emoji":
        return FONT_EMOJI
    if Path(FONT_MARU).exists():
        return FONT_MARU
    return FONT_CJK


def render_line(text, kind, size, fill, stroke, angle):
    """1 行を透過画像に描いて、傾けて返す。"""
    if kind == "emoji":
        # ビットマップなので原寸で描いてから縮める
        font = ImageFont.truetype(FONT_EMOJI, EMOJI_NATIVE)
        tmp = Image.new("RGBA", (EMOJI_NATIVE * (len(text) + 2), EMOJI_NATIVE * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((0, 0), text, font=font, embedded_color=True)
        layer = tmp.crop(tmp.getbbox() or (0, 0, 1, 1))
        scale = size / layer.height
        layer = layer.resize(
            (max(int(layer.width * scale), 1), max(int(layer.height * scale), 1)),
            Image.LANCZOS,
        )
    else:
        font = ImageFont.truetype(font_path(kind), size)
        pad = stroke * 2 + 24
        box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox(
            (0, 0), text, font=font, stroke_width=stroke)
        tmp = Image.new("RGBA", (box[2] - box[0] + pad * 2, box[3] - box[1] + pad * 2),
                        (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        at = (pad - box[0], pad - box[1])
        # 影 → 本体の順。縁取りは本体と一緒に描く
        d.text((at[0] + SHADOW_OFFSET[0], at[1] + SHADOW_OFFSET[1]), text, font=font,
               fill=SHADOW, stroke_width=stroke, stroke_fill=SHADOW)
        d.text(at, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=OUTLINE)
        layer = tmp.crop(tmp.getbbox() or (0, 0, 1, 1))

    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    return layer


def build(outfile="title.png"):
    OUT.mkdir(parents=True, exist_ok=True)
    layers = [render_line(t, k, s, f, st, a) for (t, k, s, f, st, a) in LINES if t]
    if not layers:
        sys.exit("文言が空")

    height = sum(l.height for l in layers) + GAP * (len(layers) - 1)
    canvas = Image.new("RGBA", (W, height), (0, 0, 0, 0))
    y = 0
    for l in layers:
        canvas.alpha_composite(l, ((W - l.width) // 2, y))
        y += l.height + GAP

    dest = OUT / outfile
    canvas.save(dest)
    print(f"   完成: {dest}  {canvas.width}x{canvas.height}")
    return dest


if __name__ == "__main__":
    build()
