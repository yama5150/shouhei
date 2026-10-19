#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曲のどこを使うか決める。1 秒ごとにレベルを測って、区切りと候補を出す。

    python3 pick_music.py 曲.mp3 20          # 20 秒ぶん使う場合の候補

数分ある曲から十数秒を切り出すとき、適当な位置から始めると「途中から
ぶつっと入る」感じになる。静かなブレイク明け（＝セクションの頭）から
使うと、音が入ってくるところで始まるので収まりがいい。

出てくる候補は 2 種類:
  区切り明け … 直前に静かな箇所があり、セクションの頭らしいところ
  安定区間   … 平均が高く、ばらつきが小さいところ

迷ったら区切り明けを選ぶ。盛り上がりを使い切りたいなら安定区間。
"""

import array
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


def levels(path, win=1.0):
    """win 秒ごとの RMS を dB で返す。"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        tmp = Path(t.name)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path),
         "-ac", "1", "-ar", "8000", "-f", "wav", str(tmp)],
        capture_output=True)
    w = wave.open(str(tmp))
    sr = w.getframerate()
    d = array.array("h")
    d.frombytes(w.readframes(w.getnframes()))
    w.close()
    tmp.unlink(missing_ok=True)

    step = int(sr * win)
    out = []
    for i in range(0, len(d) - step, step):
        s = sum(x * x for x in d[i:i + step]) / step
        out.append(20 * math.log10(max(math.sqrt(s) / 32768, 1e-6)))
    return out, len(d) / sr


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    path = Path(args[0]).resolve()
    want = float(args[1]) if len(args) > 1 else 20.0
    if not path.exists():
        sys.exit(f"音源が見つかりません: {path}")

    db, total = levels(path)
    print(f"{path.name}  全長 {total:.0f}秒  （使う長さ {want:.1f}秒）\n")
    print("秒ごとのレベル(dB):")
    for i in range(0, len(db), 15):
        print(f"  {i:3d}s: " + " ".join(f"{v:5.1f}" for v in db[i:i + 15]))

    med = sorted(db)[len(db) // 2]
    W = int(round(want))

    # 区切り: 直前 2 秒が中央値より 3dB 以上落ちていて、そこから戻る位置
    breaks = []
    for i in range(2, len(db) - W):
        before = min(db[i - 2], db[i - 1])
        if before < med - 3 and db[i] > before + 2.5:
            seg = db[i:i + W]
            breaks.append((sum(seg) / W, i))
    breaks.sort(reverse=True)

    print(f"\n■ 区切り明けの候補（おすすめ）")
    if breaks:
        for mean, i in breaks[:4]:
            seg = db[i:i + W]
            print(f"  start={i:3d}  {i}〜{i+W}秒  平均{mean:5.1f}dB  "
                  f"幅{max(seg)-min(seg):4.1f}")
    else:
        print("  はっきりした区切りが見つからない。下の安定区間から選ぶ。")

    steady = sorted(
        ((sum(db[i:i + W]) / W - (max(db[i:i + W]) - min(db[i:i + W])) * 0.25, i)
         for i in range(len(db) - W)), reverse=True)
    seen, picks = set(), []
    for score, i in steady:
        if any(abs(i - j) < W // 2 for j in seen):
            continue
        seen.add(i)
        picks.append(i)
        if len(picks) >= 4:
            break

    print(f"\n■ 安定区間の候補")
    for i in picks:
        seg = db[i:i + W]
        print(f"  start={i:3d}  {i}〜{i+W}秒  平均{sum(seg)/W:5.1f}dB  "
              f"幅{max(seg)-min(seg):4.1f}")

    tail = [i for i in range(len(db)) if db[i] < med - 6]
    if tail and tail[-1] > len(db) - 15:
        fade = next((i for i in tail if i > len(db) - 25), None)
        if fade:
            print(f"\n注意: {fade}秒あたりから曲が終わりにかかる。"
                  f"start + 使う長さ がここを越えないように。")


if __name__ == "__main__":
    main()
