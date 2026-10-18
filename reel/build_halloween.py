#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ハロウィン装飾 + 彩料理のリール (1080x1920 / 30fps / 約18秒)

使い方:
    SRC=/path/to/素材ディレクトリ python3 reel/build_halloween.py

    # 曲を乗せる場合 (MUSIC を渡すと音楽入りの版も出る)
    MUSIC=/path/to/曲.mp3 MUSIC_START=30 python3 reel/build_halloween.py

    # テロップもカットも触っていないときは映像を作り直さない
    python3 reel/build_halloween.py --audio-only

映像は 1 回だけエンコードして、音声違いを差し替えで書き出す。
中間ファイルは寿司版 (build_reel.py) とぶつからないよう接頭辞を分けてある。
ffmpeg 6.x 以降 + 日本語フォントが必要。
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

# 締めのカード
CARD_TITLE = os.environ.get("CARD_TITLE", "ススデパの ハロウィン")
CARD_LEAD = os.environ.get("CARD_LEAD", "開催中")
CARD_NOTE = os.environ.get("CARD_NOTE", "詳しくはプロフィールから")

# 音楽。空なら無音版だけ作る。
# MUSIC_START は曲のどこから使うか（秒）。レベルを1秒ごとに測ったところ
# 60秒に区切りがあり、61秒から次のセクション。そこから74秒へ向けて
# 曲がいちばん盛り上がるので、15秒だと「入って上がる」形になる。
# 一定の強さで通したいなら 155（150〜154のブレイク明け）。
MUSIC = os.environ.get("MUSIC", str(SRC / "5c40e34b-__________2.mp3"))
MUSIC_START = float(os.environ.get("MUSIC_START", "61"))

# 元クリップの音は、ビビンバのカットが -33 LUFS のほぼ無音、
# 生成動画のほうは AI がつけた音。どちらも曲と喧嘩するので混ぜない。
USE_CLIP_AUDIO = False

W, H, FPS = 1080, 1920, 30

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_FALLBACK = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"

SOURCES = {
    # 跳ねるジャックオランタン。AI 生成、480x640 と小さいので寄らずに使う
    "jump_v":   SRC / "85b27fc0-_users_50725571-75b6-4773-9a3d-c3ac9768d6f1_generated_c594a094-b375-47f9-86fe-16d5215b0a7e_generated_video.mp4",
    "bibim_v":  SRC / "71769e20-IMG_1922.mov",   # 石焼ビビンバを運ぶ 8.6s
    "jack1_p":  SRC / "ed3cae41-image.jpg",      # ジャックオランタン（縫い口）
    "jack2_p":  SRC / "bd35f927-image.jpg",      # ジャックオランタン（笑顔）
    "roll_p":   SRC / "8b355bc3-image.jpg",      # 巻き寿司の盛り
    "aburi_p":  SRC / "1353e30f-image.jpg",      # 炙りの一皿
    "chef_p":   SRC / "0a9bcf1d-image.jpg",      # 職人 + サーモントラウト（笑顔）
    "sting_v":  SRC / "977d2986-DopVl3SCneao9y70kOk0dgISllqQ9S1lyIWkKfA8vKg.mp4",  # ロゴ 2s
}

INK = "white"
CHIP = "0x101010@0.60"        # キャプションの下地
GOLD = "0xF0C071"             # アクセント

# ---------------------------------------------------------------- 構成
# kind:   "video" / "photo" / "card"（ぼかし背景に文字だけ）/ "black"
# zoom:   静止画は (開始倍率, 終了倍率)、動画は固定倍率。1.0 = 等倍
# focus:  どこに寄るか 0.0=左/上 0.5=中央 1.0=右/下
# lift:   暗いカットを持ち上げるガンマ
# plain:  True なら色調整もテロップも入れない（ロゴなど完成済みの素材用）
# lines:  [(文字列, フォントサイズ, 色), ...] 下寄せで積む

SEGMENTS = [
    # 跳ねるかぼちゃで掴む。480x640 なので寄らず、余白は同じ絵のぼかしで埋める
    dict(key="jump_v", kind="video", start=0.00, dur=1.80, fit="blur", lift=1.25,
         lines=[("ハロウィン、やってます。", 62, INK)]),

    dict(key="jack1_p", kind="photo", dur=1.60, zoom=(1.06, 1.16), focus=(0.50, 0.45),
         lift=1.10,
         lines=[("愉快な仲間たちが お出迎え。", 56, INK)]),

    dict(key="roll_p", kind="photo", dur=1.90, zoom=(1.02, 1.12), focus=(0.50, 0.50),
         lift=1.05,
         lines=[("彩り、揃ってます。", 64, INK)]),

    dict(key="aburi_p", kind="photo", dur=1.90, zoom=(1.04, 1.14), focus=(0.45, 0.50),
         lift=1.25,
         lines=[("炙りも、ひと皿。", 64, INK)]),

    dict(key="bibim_v", kind="video", start=3.60, dur=2.40, zoom=1.10, focus=(0.50, 0.45),
         lift=1.18,
         lines=[("できたては、お席まで。", 62, INK)]),

    # 間に挟む一拍。文字は乗せない
    dict(key="jack2_p", kind="photo", dur=1.40, zoom=(1.08, 1.18), focus=(0.48, 0.42),
         lift=1.22, lines=[]),

    dict(key="chef_p", kind="photo", dur=2.20, zoom=(1.02, 1.10), focus=(0.50, 0.40),
         lift=1.40,
         lines=[("ススデパで お待ちしてます。", 58, INK)]),

    # 告知カード（かぼちゃをぼかして地に使う）
    dict(key="jack2_p", kind="card", dur=2.40, lift=1.25,
         lines=[(CARD_TITLE, 54, INK), (CARD_LEAD, 84, GOLD), (CARD_NOTE, 44, INK)]),

    dict(key="sting_v", kind="video", start=0.00, dur=2.00, plain=True, lines=[]),

    dict(key=None, kind="black", dur=0.50, lines=[]),
]

TOTAL = sum(s["dur"] for s in SEGMENTS)

# ---------------------------------------------------------------- 見た目

CAPTION_BOTTOM = 1410      # キャプション下端 (Instagram の UI を避ける)
LINE_STEP = 118            # 行送り
TEXT_IN = 0.15             # キャプション表示開始 (秒)

CARD_LINE_STEP = 146       # 告知カードは少し広めに積む

TARGET_LUFS = -16.0
TARGET_TP = -1.5
PEAK_CEILING = 0.84        # -1.5dBFS。リミッターの頭打ち

MUSIC_LUFS = -18.0         # 音楽版のバランス
CLIP_LUFS = -22.0

FADE_IN = 0.0              # 1フレーム目から見せたいのでフェードなし
FADE_OUT = 0.20            # ロゴ側にもフェードがあるので短め
AUDIO_TAIL = 3.50          # 告知カードから引きはじめて、最後の黒で鳴り終わる
AUDIO_CURVE = "tri"        # 15秒と短いので、直線のほうが引きはじめが分かる
                           # (長い動画なら qsin のほうが終わり際が自然)


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

    lift は暗いカットを持ち上げるガンマ。ガンマだけ上げると平坦になるので、
    少しコントラストを足し戻している。
    """
    base = "eq=contrast=1.05:saturation=1.16:gamma=1.06"
    extra = f",eq=gamma={lift:.2f}:contrast=1.03" if lift > 1.0 else ""
    return f"{base}{extra},unsharp=5:5:0.45:5:5:0.0"


def kenburns(z0, z1, dur, fx, fy):
    """静止画にゆっくりズームをかける。

    2 倍解像度の 9:16 台紙に載せてから zoompan で寄る。等倍のまま寄ると
    座標の丸めでカクつく。
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


def blur_fit_video(dur):
    """小さい動画を切らずに全部見せる。余白は同じ絵のぼかしで埋める。

    480x640 を 9:16 に切ると横が 25% 落ちるうえ 3 倍に伸ばすことになる。
    幅を合わせるだけなら 2.25 倍で済み、跳ねるかぼちゃも切れない。
    """
    return (
        f"split=2[bgsrc][fgsrc];"
        f"[bgsrc]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"gblur=sigma=44,eq=brightness=-0.10:saturation=0.60,fps={FPS}[bg];"
        f"[fgsrc]scale={W}:-2:flags=lanczos,fps={FPS}[fg];"
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


def captions(seg, idx, fontfile, step=None, bottom=None):
    lines = [(t, s, c) for (t, s, c) in seg["lines"] if t]
    if not lines:
        return ""
    step = step or LINE_STEP
    bottom = bottom or CAPTION_BOTTOM
    parts = []
    first_y = bottom - step * len(lines)
    for i, (txt, size, color) in enumerate(lines):
        tf = TEXTDIR / f"hw{idx:02d}_{i}.txt"
        tf.write_text(txt, encoding="utf-8")
        parts.append(
            f"drawtext=fontfile='{fontfile}':textfile='{tf}':"
            f"fontsize={size}:fontcolor={color}:"
            f"box=1:boxcolor={CHIP}:boxborderw=24:"
            f"shadowcolor=black@0.5:shadowx=0:shadowy=3:"
            f"x='(w-text_w)/2':y={first_y + step * i}:enable='gte(t,{TEXT_IN})'"
        )
    return "," + ",".join(parts)


def _loudnorm_json(cmd, what):
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        sys.exit(f"ffmpeg が失敗しました (音量測定 {what})")
    start = proc.stderr.rfind("{")
    return json.loads(proc.stderr[start:proc.stderr.rfind("}") + 1])


def measure_lufs(inputs, chains, label, what):
    """フィルタグラフ途中のラベルの統合ラウドネスを測る。

    loudnorm は測定にだけ使い、書き出しには通さない。書き出しに挟むと
    動的モードで音が暴れるうえ、先読み 3 秒ぶん末尾が落ちることがある。
    """
    graph = ";\n".join(chains + [f"[{label}]loudnorm=print_format=json[probe]"])
    script = OUT / f"filtergraph_halloween_measure_{what}.txt"
    script.write_text(graph, encoding="utf-8")
    data = _loudnorm_json(
        ["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs +
        ["-filter_complex_script", str(script), "-map", "[probe]", "-vn",
         "-t", f"{TOTAL:.3f}", "-f", "null", "-"],
        what,
    )
    return float(data["input_i"])


def measure_music_lufs():
    data = _loudnorm_json(
        ["ffmpeg", "-hide_banner", "-nostats", "-y",
         "-ss", f"{MUSIC_START}", "-t", f"{TOTAL:.3f}", "-i", MUSIC,
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        "music",
    )
    return float(data["input_i"])


def run(cmd, what):
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        sys.exit(f"ffmpeg が失敗しました ({what})")


# ---------------------------------------------------------------- 映像

def render_video():
    fontfile = font()
    TEXTDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    inputs, chains, labels = [], [], []
    for i, seg in enumerate(SEGMENTS):
        dur = seg["dur"]
        path = SOURCES.get(seg["key"]) if seg["key"] else None
        if path is not None and not path.exists():
            sys.exit(f"素材が見つかりません: {path}")
        lift = seg.get("lift", 1.0)

        if seg["kind"] == "black":
            inputs += ["-f", "lavfi", "-t", f"{dur}",
                       "-i", f"color=c=black:s={W}x{H}:r={FPS}"]
            chains.append(
                f"[{i}:v]trim=duration={dur},setpts=PTS-STARTPTS,"
                f"setsar=1,format=yuv420p[v{i}]"
            )
        elif seg["kind"] == "card":
            # 写真を大きくぼかして暗く落とし、文字だけ載せる。
            # ロゴが黒地なので、カードも暗くしておくとつながりがいい
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur}", "-i", str(path)]
            chains.append(
                f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"gblur=sigma=56,eq=brightness=-0.26:saturation=0.40:gamma={lift:.2f},"
                f"fps={FPS},setsar=1,format=yuv420p"
                f"{captions(seg, i, fontfile, step=CARD_LINE_STEP)}[v{i}]"
            )
        elif seg["kind"] == "photo":
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur}", "-i", str(path)]
            # iPhone の JPEG は EXIF の回転を ffmpeg が自動で当てるので触らない
            chains.append(
                f"[{i}:v]{kenburns(*seg['zoom'], dur, *seg['focus'])},"
                f"{grade(lift)},fps={FPS},setsar=1,format=yuv420p"
                f"{captions(seg, i, fontfile)}[v{i}]"
            )
        else:
            inputs += ["-ss", f"{seg['start']}", "-t", f"{dur}", "-i", str(path)]
            # .mov は回転メタデータ付き。ffmpeg が自動で縦に起こす
            if seg.get("plain"):
                look = f"scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p"
                caption = ""
            elif seg.get("fit") == "blur":
                look = (f"{blur_fit_video(dur)},{grade(lift)},"
                        f"setsar=1,format=yuv420p")
                caption = captions(seg, i, fontfile)
            else:
                zoom = seg.get("zoom", 1.0)
                fx, fy = seg.get("focus", (0.5, 0.5))
                look = (
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H}{punch_in(zoom, fx, fy)},"
                    f"{grade(lift)},setsar=1,format=yuv420p"
                )
                caption = captions(seg, i, fontfile)
            chains.append(
                f"[{i}:v]fps={FPS},{look},"
                f"trim=duration={dur},setpts=PTS-STARTPTS{caption}[v{i}]"
            )
        labels.append(f"[v{i}]")

    chains.append("".join(labels) + f"concat=n={len(SEGMENTS)}:v=1:a=0[vcat]")
    fade_in = f"fade=t=in:st=0:d={FADE_IN}," if FADE_IN > 0 else ""
    chains.append(
        f"[vcat]{fade_in}fade=t=out:st={TOTAL - FADE_OUT:.3f}:d={FADE_OUT}[vout]"
    )

    script = OUT / "filtergraph_halloween_video.txt"
    script.write_text(";\n".join(chains), encoding="utf-8")
    dest = OUT / "_video_halloween.mp4"

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
    kind = "music" if with_music else "ambient"
    print(f"→ 音声 ({kind}) を書き出し中…")

    inputs, chains, labels = [], [], []
    for i, seg in enumerate(SEGMENTS):
        dur = seg["dur"]
        path = SOURCES.get(seg["key"]) if seg["key"] else None
        if seg["kind"] == "video" and path is not None and has_audio(path):
            inputs += ["-ss", f"{seg['start']}", "-t", f"{dur}", "-i", str(path)]
            chains.append(
                f"[{i}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                f"atrim=duration={dur},asetpts=PTS-STARTPTS,"
                f"afade=t=in:st=0:d=0.08,afade=t=out:st={dur - 0.08:.3f}:d=0.08[a{i}]"
            )
        else:
            inputs += ["-f", "lavfi", "-t", f"{dur}",
                       "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
            chains.append(f"[{i}:a]atrim=duration={dur},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[a{i}]")

    n = len(SEGMENTS)
    chains.append("".join(labels) + f"concat=n={n}:v=0:a=1[acat]")

    if with_music:
        music_i = measure_music_lufs()
        inputs += ["-ss", f"{MUSIC_START}", "-t", f"{TOTAL}", "-i", MUSIC]
        chains.append(
            f"[{n}:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"atrim=duration={TOTAL},asetpts=PTS-STARTPTS,"
            f"volume={MUSIC_LUFS - music_i:+.2f}dB[musicout]"
        )
        if USE_CLIP_AUDIO:
            # 混ぜる前に各系統を測って揃える。まとめてから正規化すると、
            # ずっと鳴っている曲に引っぱられて現場の音が埋もれる
            clips_i = measure_lufs(inputs[:-6], chains[:-1], "acat", f"{kind}_clips")
            print(f"   クリップ {clips_i:.1f} → {CLIP_LUFS} LUFS / "
                  f"音楽 {music_i:.1f} → {MUSIC_LUFS} LUFS")
            chains.append(f"[acat]volume={CLIP_LUFS - clips_i:+.2f}dB[clips]")
            chains.append(
                "[clips][musicout]amix=inputs=2:duration=first:normalize=0[mix]")
        else:
            print(f"   音楽 {music_i:.1f} → {MUSIC_LUFS} LUFS（曲のみ）")
            chains.append("[acat]anullsink")
            chains.append("[musicout]anull[mix]")
    else:
        chains.append("[acat]anull[mix]")

    mix_i = measure_lufs(inputs, chains, "mix", kind)
    gain = TARGET_LUFS - mix_i
    print(f"   全体 {mix_i:.1f} LUFS → {gain:+.1f}dB")

    chains.append(
        f"[mix]volume={gain:+.2f}dB,"
        f"alimiter=limit={PEAK_CEILING:.3f}:level=disabled:attack=5:release=60,"
        f"afade=t=in:st=0:d=0.20,"
        f"afade=t=out:st={TOTAL - AUDIO_TAIL:.3f}:d={AUDIO_TAIL}:curve={AUDIO_CURVE}[aout]"
    )

    script = OUT / f"filtergraph_halloween_audio_{kind}.txt"
    script.write_text(";\n".join(chains), encoding="utf-8")
    dest = OUT / f"_audio_halloween_{kind}.m4a"
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
    cached = OUT / "_video_halloween.mp4"
    if "--audio-only" in sys.argv and cached.exists():
        print(f"→ 映像は既存のものを使う: {cached.name}")
        video = cached
    else:
        video = render_video()

    mux(video, None, "halloween_reel_muted.mp4")
    if MUSIC and Path(MUSIC).exists():
        mux(video, render_audio(with_music=True), "halloween_reel.mp4")
    else:
        # 元クリップの音は使えないので、音源がなければ無音がそのまま本番
        print("   （MUSIC が未指定。アプリ側で曲を乗せるか MUSIC=... を渡す）")
        mux(video, None, "halloween_reel.mp4")
