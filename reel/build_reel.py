#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
寿司・魚介リール動画ビルダー (1080x1920 / 30fps / 約23秒)

使い方:
    SRC=/path/to/素材ディレクトリ python3 reel/build_reel.py

素材ファイル名は SOURCES で定義。SHOP に店名を入れるとラストにクレジットが入る。
ffmpeg 6.x 以降 + 日本語フォント (Noto Sans CJK JP) が必要。
"""

import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 設定

ROOT = Path(__file__).resolve().parent
SRC = Path(os.environ.get("SRC", "/root/.claude/uploads/ebdc904f-5340-54cd-b0d4-2ab1002efa6a"))
OUT = ROOT / "out"
TEXTDIR = ROOT / "text"

SHOP = os.environ.get("SHOP", "")          # 例: SHOP="鮨 ○○" で最後にクレジット表示
CTA = os.environ.get("CTA", "貴方様を おまちしております")

W, H, FPS = 1080, 1920, 30

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_FALLBACK = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"

SOURCES = {
    "basket_v": SRC / "0d7336f2-IMG_1744.mov",   # 盛り籠パン 4.67s
    "clam_v":   SRC / "477c6431-IMG_1747.mov",   # 貝を開ける 8.94s
    "tai_v":    SRC / "086b18c5-IMG_1749.mov",   # 真鯛の仕込み 20.43s
    "chef_p":   SRC / "01d4f250-image.jpg",      # 職人 + サーモントラウト (EXIF 回転あり)
    "basket_p": SRC / "adad3a16-image.jpg",      # 盛り籠 寄り (EXIF 回転あり)
    "fish3_p":  SRC / "d06c975f-image.jpg",      # ブリ + サクラマス 2本 (EXIF 回転あり)
    "don_p":    SRC / "6a30fbb1-image.jpg",      # 海鮮丼
    "uni_p":    SRC / "eccff8b3-image.jpg",      # うに軍艦
}

# 文字色まわり
INK = "white"
CHIP = "0x101010@0.60"        # キャプションの下地
GOLD = "0xF0C071"             # CTA のアクセント

# ---------------------------------------------------------------- 構成
# kind:   "video" = 動画から切り出し / "photo" = 静止画 + ケンバーンズ
# zoom:   静止画は (開始倍率, 終了倍率)、動画は固定倍率。1.0 = 等倍
# focus:  どこに寄るか 0.0=左/上 0.5=中央 1.0=右/下
# lines:  [(文字列, フォントサイズ, 色), ...] 下寄せで積む

SEGMENTS = [
    # --- フック ---------------------------------------------------------
    dict(key="chef_p", kind="photo", dur=2.40, zoom=(1.32, 1.46), focus=(0.72, 0.16),
         lines=[("今日、こんなん", 76, INK), ("入りました。", 76, INK)]),

    # --- 仕入れ ---------------------------------------------------------
    dict(key="fish3_p", kind="photo", dur=2.20, zoom=(1.00, 1.10), focus=(0.42, 0.45),
         lines=[("魚は その日のぶんだけ。", 64, INK)]),

    dict(key="basket_v", kind="video", start=0.00, dur=2.00,
         lines=[("貝も いいのが入ってます。", 62, INK)]),

    # --- 仕込み ---------------------------------------------------------
    dict(key="tai_v", kind="video", start=9.60, dur=2.60, zoom=1.18, focus=(0.42, 0.58),
         lines=[("真鯛は 一本もの。", 64, INK)]),

    dict(key="tai_v", kind="video", start=17.20, dur=2.00, zoom=1.45, focus=(0.05, 0.10),
         lines=[("一尾ずつ、手で。", 64, INK)]),

    dict(key="clam_v", kind="video", start=0.30, dur=2.20, zoom=1.10, focus=(0.50, 0.45),
         lines=[("貝は、目の前で開ける。", 64, INK)]),

    dict(key="clam_v", kind="video", start=6.60, dur=2.40, zoom=1.16, focus=(0.45, 0.62),
         lines=[("開けたてが、", 72, INK), ("いちばん旨い。", 72, INK)]),

    dict(key="basket_v", kind="video", start=2.70, dur=1.60,
         lines=[("ぜんぶ 今日のネタです。", 62, INK)]),

    # --- 出来上がり -----------------------------------------------------
    dict(key="don_p", kind="photo", dur=2.80, zoom=(1.00, 1.09), focus=(0.50, 0.48),
         lines=[("その日入荷した、", 66, INK), ("旬の魚介で。", 66, INK)]),

    dict(key="uni_p", kind="photo", dur=2.40, zoom=(1.08, 1.22), focus=(0.48, 0.46),
         lines=[("今日の一貫、どうぞ。", 64, INK)]),

    # --- 締め -----------------------------------------------------------
    dict(key="chef_p", kind="photo", dur=3.20, zoom=(1.10, 1.00), focus=(0.50, 0.50),
         fit="blur",
         lines=([(SHOP, 52, INK)] if SHOP else []) + [(CTA, 64, GOLD)]),
]

# ---------------------------------------------------------------- 組み立て

CAPTION_BOTTOM = 1410      # キャプション下端 (Instagram の UI を避ける)
LINE_STEP = 118            # 行送り
TEXT_IN = 0.18             # キャプション表示開始 (秒)


def font():
    for f in (FONT_BOLD, FONT_REG, FONT_FALLBACK):
        if Path(f).exists():
            return f
    sys.exit("日本語フォントが見つかりません (fonts-noto-cjk を入れてください)")


def grade():
    """食材が旨そうに見える程度の軽い色調整。"""
    return "eq=contrast=1.06:saturation=1.14:gamma=1.02,unsharp=5:5:0.45:5:5:0.0"


def kenburns(z0, z1, dur, fx, fy):
    """静止画にゆっくりズームをかける (ケンバーンズ)。

    2 倍解像度の 9:16 台紙に載せてから zoompan で寄る。等倍のまま寄ると
    座標の丸めでカクつくので、大きい台紙を作ってから縮小している。
    """
    base_w, base_h = W * 2, H * 2
    frames = max(int(round(dur * FPS)) - 1, 1)
    return (
        f"scale={base_w}:{base_h}:force_original_aspect_ratio=increase,"
        f"crop={base_w}:{base_h}:(iw-ow)*{fx:.3f}:(ih-oh)*{fy:.3f},"
        f"zoompan=z='{z0}+({z1}-{z0})*on/{frames}':"
        f"x='(iw-iw/zoom)*{fx:.3f}':y='(ih-ih/zoom)*{fy:.3f}':"
        f"d=1:s={W}x{H}:fps={FPS}"
    )


def kenburns_fit(z0, z1, dur):
    """写真を切らずに全部見せる。余白は同じ写真のぼかしで埋める。

    手前の写真は固定、背景のぼかしだけをゆっくり動かす。締めのカットなど
    「写真そのものを見せたい」ところで使う。
    """
    frames = max(int(round(dur * FPS)) - 1, 1)
    return (
        f"split=2[bgsrc][fgsrc];"
        f"[bgsrc]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
        f"crop={W * 2}:{H * 2},"
        f"zoompan=z='{z0}+({z1}-{z0})*on/{frames}':"
        f"x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS},"
        f"gblur=sigma=40,eq=brightness=-0.14:saturation=0.60[bg];"
        f"[fgsrc]scale={W}:-2,fps={FPS}[fg];"
        f"[bg][fg]overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2:shortest=1"
    )


def punch_in(zoom, fx, fy):
    """動画クリップを固定倍率で寄せる (構図の整理用)。"""
    if not zoom or zoom <= 1.0:
        return ""
    cw = f"floor({W}/{zoom}/2)*2"
    ch = f"floor({H}/{zoom}/2)*2"
    return (
        f",crop=w={cw}:h={ch}:x='(in_w-out_w)*{fx:.3f}':y='(in_h-out_h)*{fy:.3f}',"
        f"scale={W}:{H}"
    )


def captions(seg, idx, fontfile):
    lines = [(t, s, c) for (t, s, c) in seg["lines"] if t]
    if not lines:
        return ""
    parts = []
    first_y = CAPTION_BOTTOM - LINE_STEP * len(lines)
    for i, (txt, size, color) in enumerate(lines):
        tf = TEXTDIR / f"seg{idx:02d}_{i}.txt"
        tf.write_text(txt, encoding="utf-8")
        y = first_y + LINE_STEP * i
        parts.append(
            f"drawtext=fontfile='{fontfile}':textfile='{tf}':"
            f"fontsize={size}:fontcolor={color}:"
            f"box=1:boxcolor={CHIP}:boxborderw=24:"
            f"shadowcolor=black@0.5:shadowx=0:shadowy=3:"
            f"x='(w-text_w)/2':y={y}:enable='gte(t,{TEXT_IN})'"
        )
    return "," + ",".join(parts)


def build(with_audio=True, outfile="sushi_reel.mp4"):
    fontfile = font()
    TEXTDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    total = sum(s["dur"] for s in SEGMENTS)

    inputs, chains, vlabels, alabels = [], [], [], []

    for i, seg in enumerate(SEGMENTS):
        path = SOURCES[seg["key"]]
        if not path.exists():
            sys.exit(f"素材が見つかりません: {path}")
        dur = seg["dur"]

        if seg["kind"] == "photo":
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur}", "-i", str(path)]
            # iPhone の JPEG は EXIF Orientation=6。ffmpeg が自動で起こすので
            # ここで transpose をかけると二重回転になる
            if seg.get("fit") == "blur":
                shaper = kenburns_fit(*seg["zoom"], dur)
            else:
                shaper = kenburns(*seg["zoom"], dur, *seg["focus"])
            chains.append(
                f"[{i}:v]{shaper},"
                f"{grade()},fps={FPS},setsar=1,format=yuv420p"
                f"{captions(seg, i, fontfile)}[v{i}]"
            )
            if with_audio:
                chains.append(
                    f"anullsrc=channel_layout=stereo:sample_rate=48000,"
                    f"atrim=duration={dur},asetpts=PTS-STARTPTS[a{i}]"
                )
        else:
            start = seg["start"]
            inputs += ["-ss", f"{start}", "-t", f"{dur}", "-i", str(path)]
            # .mov は回転メタデータ付き。ffmpeg が自動で起こすので縦のまま扱える
            zoom = seg.get("zoom", 1.0)
            fx, fy = seg.get("focus", (0.5, 0.5))
            chains.append(
                f"[{i}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H}{punch_in(zoom, fx, fy)},"
                f"{grade()},setsar=1,format=yuv420p,"
                f"trim=duration={dur},setpts=PTS-STARTPTS"
                f"{captions(seg, i, fontfile)}[v{i}]"
            )
            if with_audio:
                chains.append(
                    f"[{i}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"atrim=duration={dur},asetpts=PTS-STARTPTS,"
                    f"afade=t=in:st=0:d=0.08,afade=t=out:st={dur - 0.08:.3f}:d=0.08[a{i}]"
                )

        vlabels.append(f"[v{i}]")
        alabels.append(f"[a{i}]")

    n = len(SEGMENTS)
    chains.append("".join(vlabels) + f"concat=n={n}:v=1:a=0[vcat]")
    if with_audio:
        chains.append("".join(alabels) + f"concat=n={n}:v=0:a=1[acat]")

    # 頭と尻をフェード（ループしても違和感が出ないように）
    chains.append(
        f"[vcat]fade=t=in:st=0:d=0.30,"
        f"fade=t=out:st={total - 0.45:.3f}:d=0.45[vout]"
    )

    if with_audio:
        # 静止画パートで無音にならないよう、厨房の環境音を薄く敷く
        bed_idx = n
        inputs += ["-stream_loop", "-1", "-t", f"{total}", "-i", str(SOURCES["tai_v"])]
        chains.append(
            f"[{bed_idx}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"atrim=duration={total},asetpts=PTS-STARTPTS,volume=0.10[bed]"
        )
        chains.append(
            "[acat][bed]amix=inputs=2:duration=first:normalize=0,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"afade=t=in:st=0:d=0.25,afade=t=out:st={total - 0.5:.3f}:d=0.5[aout]"
        )
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    else:
        amap = ["-an"]

    script = OUT / ("filtergraph_sound.txt" if with_audio else "filtergraph_silent.txt")
    script.write_text(";\n".join(chains), encoding="utf-8")

    dest = OUT / outfile
    cmd = (
        ["ffmpeg", "-hide_banner", "-y"] + inputs +
        ["-filter_complex_script", str(script), "-map", "[vout]"] + amap +
        [
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
            "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-g", str(FPS * 2), "-movflags", "+faststart",
            "-t", f"{total:.3f}", str(dest),
        ]
    )
    print(f"→ {dest.name} ({total:.1f}秒) をエンコード中…")
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        sys.exit(f"ffmpeg が失敗しました ({dest.name})")
    print(f"   完成: {dest}  {dest.stat().st_size / 1e6:.1f}MB")
    return dest


if __name__ == "__main__":
    build(with_audio=True, outfile="sushi_reel.mp4")
    build(with_audio=False, outfile="sushi_reel_muted.mp4")
