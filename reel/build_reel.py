#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
寿司・魚介リール動画ビルダー (1080x1920 / 30fps / 約27秒)

使い方:
    SRC=/path/to/素材ディレクトリ python3 reel/build_reel.py

映像は 1 回だけエンコードして、音声違いの 3 本を差し替えで書き出す。
ffmpeg 6.x 以降 + 日本語フォント (Noto Sans CJK JP) が必要。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 設定

ROOT = Path(__file__).resolve().parent
SRC = Path(os.environ.get("SRC", "/root/.claude/uploads/ebdc904f-5340-54cd-b0d4-2ab1002efa6a"))
OUT = ROOT / "out"
TEXTDIR = ROOT / "text"

CTA = os.environ.get("CTA", "貴方様を おまちしております")

# 秋祭りフェアの締めカード（企画書より）
FAIR_LEAD = os.environ.get("FAIR_LEAD", "熟成赤酢で喰らう")
FAIR_TITLE = os.environ.get("FAIR_TITLE", "蟹とお寿司の ススデパ秋祭り")
# 日程が固まるまでは「近日開催」で先に回す。決まったら
#   FAIR_DATES="9/1(火) 〜 10/31(土)" FAIR_NOTE="" python3 reel/build_reel.py
FAIR_DATES = os.environ.get("FAIR_DATES", "近日開催")
FAIR_NOTE = os.environ.get("FAIR_NOTE", "詳しくはプロフィールから")

# 音楽。MUSIC_START は曲のどこから使うか（秒）
MUSIC = Path(os.environ.get("MUSIC", str(SRC / "33e8d767-_shun.mp3")))
MUSIC_START = float(os.environ.get("MUSIC_START", "153"))

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
    "sting_v":  SRC / "60522e38-DopVl3SCneao9y70kOk0dgISllqQ9S1lyIWkKfA8vKg.mp4",  # ロゴ 2s
    "cover_p":  SRC / "4dcd4b9d-image.jpg",      # 握り3貫。カバー画像用
}

# 環境音のベッドに使うクリップ（静止画パートで無音にならないように敷く）
AMBIENT_BED = "tai_v"

# 文字色まわり
INK = "white"
CHIP = "0x101010@0.60"        # キャプションの下地
GOLD = "0xF0C071"             # CTA のアクセント

# ---------------------------------------------------------------- 構成
# kind:   "video" = 動画から切り出し / "photo" = 静止画 + ケンバーンズ
# zoom:   静止画は (開始倍率, 終了倍率)、動画は固定倍率。1.0 = 等倍
# focus:  どこに寄るか 0.0=左/上 0.5=中央 1.0=右/下
# fit:    "blur" で写真を切らずに全部見せる（余白は同じ写真のぼかし）
# plain:  True なら色調整もテロップも入れない（ロゴなど完成済みの素材用）
# lines:  [(文字列, フォントサイズ, 色), ...] 下寄せで積む

SEGMENTS = [
    # --- フック ---------------------------------------------------------
    dict(key="chef_p", kind="photo", dur=2.40, zoom=(1.32, 1.46), focus=(0.72, 0.16),
         lift=1.45,
         lines=[("今日、こんなん", 76, INK), ("入りました。", 76, INK)]),

    # --- 仕入れ ---------------------------------------------------------
    dict(key="fish3_p", kind="photo", dur=2.20, zoom=(1.00, 1.10), focus=(0.42, 0.45),
         lift=1.25,
         lines=[("魚は その日のぶんだけ。", 64, INK)]),

    dict(key="basket_v", kind="video", start=0.00, dur=2.00,
         lines=[("本日の地魚と、貝。", 64, INK)]),

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
         lift=1.15,
         lines=[("その日入荷した、", 66, INK), ("旬の魚介で。", 66, INK)]),

    dict(key="uni_p", kind="photo", dur=2.40, zoom=(1.08, 1.22), focus=(0.48, 0.46),
         lift=1.20,
         lines=[(CTA, 62, GOLD)]),

    # --- 締め: フェアの告知 ---------------------------------------------
    dict(key="chef_p", kind="photo", dur=3.60, zoom=(1.10, 1.00), focus=(0.50, 0.50),
         fit="blur", lift=1.40,
         lines=[(FAIR_LEAD, 46, INK), (FAIR_TITLE, 54, INK),
                (FAIR_DATES, 58, GOLD), (FAIR_NOTE, 42, INK)]),

    # 店のロゴテンプレ。素材のまま出す
    dict(key="sting_v", kind="video", start=0.00, dur=2.00, plain=True, lines=[]),
]

TOTAL = sum(s["dur"] for s in SEGMENTS)

# ---------------------------------------------------------------- 見た目

CAPTION_BOTTOM = 1410      # キャプション下端 (Instagram の UI を避ける)
LINE_STEP = 118            # 行送り
TEXT_IN = 0.18             # キャプション表示開始 (秒)

# 書き出しの音量。SNS 向けに -16 LUFS / 真ピーク -1.5dBFS
TARGET_LUFS = -16.0
TARGET_TP = -1.5
PEAK_CEILING = 0.84        # -1.5dBFS。リミッターの頭打ち

# 音楽版のバランス。曲を主役にして、包丁や貝の音を上に効かせる
MUSIC_LUFS = -18.0
CLIP_LUFS = -22.0

FADE_IN = 0.30
FADE_OUT = 0.20            # ロゴテンプレ側にもフェードがあるので短め
AUDIO_TAIL = 2.00          # ロゴが出ている間に音を引く


def font():
    for f in (FONT_BOLD, FONT_REG, FONT_FALLBACK):
        if Path(f).exists():
            return f
    sys.exit("日本語フォントが見つかりません (fonts-noto-cjk を入れてください)")


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return "audio" in out.stdout


def grade(lift=1.0):
    """食材が旨そうに見える程度の色調整。

    lift は暗いカットを持ち上げるためのガンマ。写真素材は厨房が暗いぶん
    沈むので、カットごとに指定して 110〜150 (0-255) あたりに揃える。
    ガンマだけ上げると平坦になるので、少しコントラストを足し戻す。
    """
    base = "eq=contrast=1.05:saturation=1.16:gamma=1.06"
    extra = f",eq=gamma={lift:.2f}:contrast=1.03" if lift > 1.0 else ""
    return f"{base}{extra},unsharp=5:5:0.45:5:5:0.0"


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

    手前の写真は固定、背景のぼかしだけをゆっくり動かす。
    """
    frames = max(int(round(dur * FPS)) - 1, 1)
    return (
        f"split=2[bgsrc][fgsrc];"
        f"[bgsrc]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
        f"crop={W * 2}:{H * 2},"
        f"zoompan=z='{z0}+({z1}-{z0})*on/{frames}':"
        f"x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS},"
        f"gblur=sigma=40,eq=brightness=-0.06:saturation=0.62[bg];"
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


def measure_gain(inputs, chains, kind):
    """一度流して測り、目標ラウドネスに合わせる静的ゲインを返す。

    loudnorm を書き出しにそのまま使うと、狙いどおりに寄らなかったときに
    動的モードへ落ちて音が暴れる。測った値からゲインを決めて、
    はみ出す瞬間だけリミッターで止めるほうが結果が読める。
    """
    graph = ";\n".join(chains + [
        f"[mix]loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json[aout]"
    ])
    script = OUT / f"filtergraph_measure_{kind}.txt"
    script.write_text(graph, encoding="utf-8")

    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs +
        ["-filter_complex_script", str(script), "-map", "[aout]", "-vn",
         "-t", f"{TOTAL:.3f}", "-f", "null", "-"],
        stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        sys.exit(f"ffmpeg が失敗しました (音量測定 {kind})")

    start = proc.stderr.rfind("{")
    data = json.loads(proc.stderr[start:proc.stderr.rfind("}") + 1])
    measured_i = float(data["input_i"])
    gain = TARGET_LUFS - measured_i
    print(f"   測定: {measured_i:.1f} LUFS / TP {float(data['input_tp']):.1f} dBFS"
          f" → {gain:+.1f}dB")
    return gain


# ---------------------------------------------------------------- カバー画像
# Instagram はプロフィールのグリッドでカバーの中央 1:1 を切り出す。
# 9:16 の 1080x1920 なら y=420〜1500 がその範囲なので、写真も文字もここに収める。
GRID_TOP, GRID_BOTTOM = 420, 1500

COVER_PHOTO_Y = 440        # 写真の上端
COVER_LINES = [            # (文字列, フォントサイズ, 色, 上端 y)
    (FAIR_LEAD, 44, INK, 350),
    (FAIR_TITLE, 54, INK, 1285),
    (FAIR_DATES, 60, GOLD, 1398),
]


def build_cover(outfile="cover.jpg"):
    """リールのカバー画像を作る。動画と同じ色調整・同じ文言で揃える。"""
    fontfile = font()
    TEXTDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    src = SOURCES["cover_p"]
    if not src.exists():
        sys.exit(f"素材が見つかりません: {src}")

    parts = []
    for i, (txt, size, color, y) in enumerate(COVER_LINES):
        if not txt:
            continue
        tf = TEXTDIR / f"cover_{i}.txt"
        tf.write_text(txt, encoding="utf-8")
        parts.append(
            f"drawtext=fontfile='{fontfile}':textfile='{tf}':"
            f"fontsize={size}:fontcolor={color}:"
            f"box=1:boxcolor={CHIP}:boxborderw=24:"
            f"shadowcolor=black@0.5:shadowx=0:shadowy=3:"
            f"x='(w-text_w)/2':y={y}"
        )

    graph = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"gblur=sigma=45,eq=brightness=-0.10:saturation=0.55[bgo];"
        f"[fg]scale={W}:-2,{grade(1.20)}[fgo];"
        f"[bgo][fgo]overlay=x=0:y={COVER_PHOTO_Y},"
        + ",".join(parts) + "[out]"
    )
    script = OUT / "filtergraph_cover.txt"
    script.write_text(graph, encoding="utf-8")

    dest = OUT / outfile
    print("→ カバー画像を書き出し中…")
    run(
        ["ffmpeg", "-hide_banner", "-y", "-i", str(src),
         "-filter_complex_script", str(script), "-map", "[out]",
         "-frames:v", "1", "-q:v", "2", str(dest)],
        "カバー画像",
    )
    print(f"   完成: {dest}  {dest.stat().st_size / 1e3:.0f}KB")
    return dest


def run(cmd, what):
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        sys.exit(f"ffmpeg が失敗しました ({what})")


# ---------------------------------------------------------------- 映像

def render_video():
    """映像だけを 1 回エンコードする。音声はあとから差し替える。"""
    fontfile = font()
    TEXTDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    inputs, chains, labels = [], [], []
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
                f"{grade(seg.get('lift', 1.0))},fps={FPS},setsar=1,format=yuv420p"
                f"{captions(seg, i, fontfile)}[v{i}]"
            )
        else:
            inputs += ["-ss", f"{seg['start']}", "-t", f"{dur}", "-i", str(path)]
            # .mov は回転メタデータ付き。ffmpeg が自動で起こすので縦のまま扱える
            if seg.get("plain"):
                # ロゴなど完成済みの素材。色もテロップも足さない
                look = f"scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p"
                caption = ""
            else:
                zoom = seg.get("zoom", 1.0)
                fx, fy = seg.get("focus", (0.5, 0.5))
                look = (
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H}{punch_in(zoom, fx, fy)},"
                    f"{grade(seg.get('lift', 1.0))},setsar=1,format=yuv420p"
                )
                caption = captions(seg, i, fontfile)
            chains.append(
                f"[{i}:v]fps={FPS},{look},"
                f"trim=duration={dur},setpts=PTS-STARTPTS{caption}[v{i}]"
            )
        labels.append(f"[v{i}]")

    chains.append("".join(labels) + f"concat=n={len(SEGMENTS)}:v=1:a=0[vcat]")
    chains.append(
        f"[vcat]fade=t=in:st=0:d={FADE_IN},"
        f"fade=t=out:st={TOTAL - FADE_OUT:.3f}:d={FADE_OUT}[vout]"
    )

    script = OUT / "filtergraph_video.txt"
    script.write_text(";\n".join(chains), encoding="utf-8")
    dest = OUT / "_video.mp4"

    print(f"→ 映像 ({TOTAL:.1f}秒) をエンコード中…")
    run(
        ["ffmpeg", "-hide_banner", "-y"] + inputs +
        ["-filter_complex_script", str(script), "-map", "[vout]", "-an",
         "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
         "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-g", str(FPS * 2), "-movflags", "+faststart",
         "-t", f"{TOTAL:.3f}", str(dest)],
        "映像",
    )
    return dest


# ---------------------------------------------------------------- 音声

def render_audio(with_music):
    """クリップの環境音（+ BGM）をつないで書き出す。"""
    inputs, chains, labels = [], [], []

    for i, seg in enumerate(SEGMENTS):
        path = SOURCES[seg["key"]]
        dur = seg["dur"]
        if seg["kind"] == "video" and has_audio(path):
            inputs += ["-ss", f"{seg['start']}", "-t", f"{dur}", "-i", str(path)]
            chains.append(
                f"[{i}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                f"atrim=duration={dur},asetpts=PTS-STARTPTS,"
                f"afade=t=in:st=0:d=0.08,afade=t=out:st={dur - 0.08:.3f}:d=0.08[a{i}]"
            )
        else:
            # 静止画とロゴには音がないので無音を挟む
            inputs += ["-f", "lavfi", "-t", f"{dur}",
                       "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
            chains.append(f"[{i}:a]atrim=duration={dur},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[a{i}]")

    n = len(SEGMENTS)
    chains.append("".join(labels) + f"concat=n={n}:v=0:a=1[acat]")

    if with_music:
        if not MUSIC.exists():
            sys.exit(f"音源が見つかりません: {MUSIC}")
        inputs += ["-ss", f"{MUSIC_START}", "-t", f"{TOTAL}", "-i", str(MUSIC)]
        # 各系統を先に測って揃えてから混ぜる。まとめてから正規化すると、
        # ずっと鳴っている曲に引っぱられて包丁や貝の音が埋もれる
        chains.append(f"[acat]loudnorm=I={CLIP_LUFS}:TP=-6:LRA=14[clips]")
        chains.append(
            f"[{n}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"atrim=duration={TOTAL},asetpts=PTS-STARTPTS,"
            f"loudnorm=I={MUSIC_LUFS}:TP=-3:LRA=8[musicout]"
        )
        chains.append("[clips][musicout]amix=inputs=2:duration=first:normalize=0[mix]")
    else:
        # 静止画パートで無音にならないよう、厨房の環境音を薄く敷く
        inputs += ["-stream_loop", "-1", "-t", f"{TOTAL}", "-i", str(SOURCES[AMBIENT_BED])]
        chains.append(
            f"[{n}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"atrim=duration={TOTAL},asetpts=PTS-STARTPTS,volume=0.10[bedout]"
        )
        chains.append(
            "[acat][bedout]amix=inputs=2:duration=first:normalize=0,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,"
            "alimiter=limit=0.89[mix]"
        )

    kind = "music" if with_music else "ambient"
    print(f"→ 音声 ({kind}) を書き出し中…")

    gain = measure_gain(inputs, chains, kind)
    chains.append(
        f"[mix]volume={gain:+.2f}dB,"
        f"alimiter=limit={PEAK_CEILING:.3f}:level=disabled:attack=5:release=60,"
        f"afade=t=in:st=0:d=0.25,"
        f"afade=t=out:st={TOTAL - AUDIO_TAIL:.3f}:d={AUDIO_TAIL}[aout]"
    )

    script = OUT / f"filtergraph_audio_{kind}.txt"
    script.write_text(";\n".join(chains), encoding="utf-8")
    dest = OUT / f"_audio_{kind}.m4a"

    run(
        ["ffmpeg", "-hide_banner", "-y"] + inputs +
        ["-filter_complex_script", str(script), "-map", "[aout]", "-vn",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-t", f"{TOTAL:.3f}", str(dest)],
        f"音声 {kind}",
    )
    return dest


def mux(video, audio, outfile):
    dest = OUT / outfile
    args = ["ffmpeg", "-hide_banner", "-y", "-i", str(video)]
    if audio:
        args += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy"]
    else:
        args += ["-map", "0:v:0", "-an", "-c", "copy"]
    run(args + ["-movflags", "+faststart", str(dest)], outfile)
    print(f"   完成: {dest}  {dest.stat().st_size / 1e6:.1f}MB")
    return dest


if __name__ == "__main__":
    if "--cover-only" in sys.argv:
        build_cover()
        sys.exit(0)

    cached = OUT / "_video.mp4"
    if "--audio-only" in sys.argv and cached.exists():
        print(f"→ 映像は既存のものを使う: {cached.name}")
        video = cached
    else:
        video = render_video()
    mux(video, render_audio(with_music=True), "sushi_reel.mp4")
    mux(video, render_audio(with_music=False), "sushi_reel_ambient.mp4")
    mux(video, None, "sushi_reel_muted.mp4")
    build_cover()
