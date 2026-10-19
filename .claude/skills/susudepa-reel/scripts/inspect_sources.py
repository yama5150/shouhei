#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材の下見。中身・明るさ・音を一度に出して、コンタクトシートを作る。

    python3 inspect_sources.py /path/to/素材 [--out 出力先]

リールを組む前にこれを流すと、どのクリップのどこが使えるか、どの写真が
沈んでいるか、音が入っているかが一度で分かる。コンタクトシートは画像
なので、出てきた jpg を実際に見ること。秒数つきで並ぶので、その数字を
そのまま構成ファイルの start に書ける。
"""

import json
import subprocess
import sys
from pathlib import Path

VIDEO_EXT = {".mov", ".mp4", ".m4v", ".avi", ".webm"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac"}

LABEL_FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"


def probe(path, entries):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entries,
         "-of", "json", str(path)], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def duration(path):
    d = probe(path, "format=duration").get("format", {})
    return float(d.get("duration", 0) or 0)


def brightness(path, still=False):
    """平均輝度を 0-255 で返す。10bit 素材は 0-1023 で出るので直す。

    静止画に fps フィルタを噛ませるとフレームが落ちて何も測れない
    （1 フレームしかなく尺も無いため）。静止画では外す。
    """
    stats = Path("/tmp/_inspect_stats.txt")
    stats.unlink(missing_ok=True)
    vf = "signalstats,metadata=print:file={}".format(stats) if still \
        else "fps=1,signalstats,metadata=print:file={}".format(stats)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf,
         "-frames:v", "1" if still else "60", "-f", "null", "-"],
        capture_output=True, text=True)
    if not stats.exists():
        return None
    vals = [float(l.split("=")[1]) for l in stats.read_text().splitlines()
            if "YAVG=" in l]
    stats.unlink(missing_ok=True)
    if not vals:
        return None
    m = sum(vals) / len(vals)
    return m / 4 if m > 300 else m


def loudness(path):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True)
    for i, line in enumerate(r.stderr.splitlines()):
        if "Integrated loudness" in line:
            nxt = r.stderr.splitlines()[i + 1]
            try:
                return float(nxt.split()[1])
            except Exception:
                return None
    return None


def contact_sheet(path, dest, dur):
    """秒数つきのコンタクトシート。数字をそのまま start に使える。"""
    step = max(dur / 12, 0.5)
    cols = 6
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path),
         "-vf", (f"fps=1/{step:.3f},scale=180:-1,"
                 f"drawtext=fontfile={LABEL_FONT}:"
                 f"text='%{{eif\\:n*{step:.2f}+{step/2:.2f}\\:d\\:2}}s':"
                 f"fontsize=22:fontcolor=yellow:box=1:boxcolor=black:x=3:y=3,"
                 f"tile={cols}x2:padding=3:color=magenta"),
         "-frames:v", "1", str(dest)], capture_output=True)
    return dest.exists()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0]).resolve()
    out = Path(sys.argv[sys.argv.index("--out") + 1]).resolve() \
        if "--out" in sys.argv else src.parent / "inspect"
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.iterdir() if p.is_file())
    if not files:
        sys.exit(f"素材がありません: {src}")

    print(f"素材: {src}\nコンタクトシート: {out}\n")
    for p in files:
        ext = p.suffix.lower()
        if ext in VIDEO_EXT:
            st = probe(p, "stream=codec_type,width,height,r_frame_rate")
            v = next((s for s in st.get("streams", [])
                      if s.get("codec_type") == "video"), {})
            rot = probe(p, "stream_side_data=rotation")
            has_rot = "rotation" in json.dumps(rot)
            dur = duration(p)
            y = brightness(p)
            lu = loudness(p)
            sheet = out / f"{p.stem[:24]}.jpg"
            ok = contact_sheet(p, sheet, dur) if dur else False
            print(f"[動画] {p.name}")
            print(f"       {v.get('width')}x{v.get('height')} / {dur:.1f}秒"
                  f"{' / 回転メタあり（ffmpeg が自動で起こす）' if has_rot else ''}")
            print(f"       輝度 {y:.0f}/255" if y else "       輝度 不明", end="")
            if lu is None:
                print(" / 音なし")
            elif lu < -30:
                print(f" / 音 {lu:.1f} LUFS … ほぼ無音。混ぜても意味がない")
            else:
                print(f" / 音 {lu:.1f} LUFS")
            if ok:
                print(f"       → {sheet}  （これを見てから start を決める）")
        elif ext in PHOTO_EXT:
            st = probe(p, "stream=width,height").get("streams", [{}])[0]
            y = brightness(p, still=True)
            print(f"[写真] {p.name}")
            size = f"{st.get('width')}x{st.get('height')}"
            if y is None:
                print(f"       {size}")
            else:
                if y < 100:
                    note = "  ← 沈んでいる。lift 1.3〜1.45 くらい"
                elif y < 118:
                    note = "  ← やや暗い。lift 1.15〜1.25"
                else:
                    note = ""
                print(f"       {size} / 輝度 {y:.0f}/255{note}")
        elif ext in AUDIO_EXT:
            print(f"[音源] {p.name}  {duration(p):.0f}秒"
                  f"  → pick_music.py で使いどころを出す")
        else:
            print(f"[その他] {p.name}")
        print()

    print("目安: 画面の平均輝度は 110〜160 に揃えると見やすい。")
    print("      lift はガンマなので、出来上がりを測って詰める。")


if __name__ == "__main__":
    main()
