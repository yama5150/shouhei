"""トレーラー用の音声と、拍の表(plan.json)を作る。手順は同じフォルダの README.md。

    python make_audio.py 原曲.mp3 WORK                 # 2026-11 版と同じ切り方
    python make_audio.py 原曲.mp3 WORK --survey        # 曲の音量と拍を出すだけ(切り方を決める用)

切り方(既定値は Eruza: Cyber Rose Crimson Remastered・4:49 版で決めたもの):
    --start 174.96   入り。間奏で静かになる拍
    --drop  184.48   盛り上がりの頭(--start の5小節後)
    --bars  13       盛り上がりから何小節使うか
    --tail  284.05   曲の終わり方の頭。ここから最後までを最後につなぐ
すべて、そこに一番近い拍に寄せてから使う。
"""
import argparse, json, os, subprocess
import numpy as np
import librosa

ap = argparse.ArgumentParser()
ap.add_argument("song"); ap.add_argument("work")
ap.add_argument("--start", type=float, default=174.96)
ap.add_argument("--drop", type=float, default=184.48)
ap.add_argument("--bars", type=int, default=13)
ap.add_argument("--tail", type=float, default=284.05)
ap.add_argument("--survey", action="store_true")
a = ap.parse_args()
os.makedirs(a.work, exist_ok=True)

y, sr = librosa.load(a.song, sr=22050, mono=True)
dur = len(y) / sr
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
bt = librosa.frames_to_time(beats, sr=sr)
print(f"長さ {dur:.2f}s / テンポ {float(np.atleast_1d(tempo)[0]):.1f} BPM / 拍 {len(bt)}")

if a.survey:
    rms = librosa.feature.rms(y=y)[0]
    t = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    for s in range(0, int(dur), 4):
        m = rms[(t >= s) & (t < s + 4)].mean()
        print(f"{s:4d}s {'#' * int(m * 200)}")
    raise SystemExit

near = lambda x: int(np.argmin(abs(bt - x)))
i0, idrop, itail = near(a.start), near(a.drop), near(a.tail)
iend = idrop + 4 * a.bars
plan = {"a0": float(bt[i0]), "drop": float(bt[idrop]), "a1": float(bt[iend]),
        "b0": float(bt[itail]), "b1": dur}
body = [float(x - bt[i0]) for x in bt[i0:iend + 1]]
tail = [float(plan["a1"] - plan["a0"] + x - bt[itail]) for x in bt[itail:]]
plan["vbeats"] = body + tail[1:]
plan["total"] = plan["a1"] - plan["a0"] + plan["b1"] - plan["b0"]
print("入り→盛り上がり:", idrop - i0, "拍 / 本体の終わり(映像の秒):", round(body[-1], 2), "/ 全体:", round(plan["total"], 2))
json.dump(plan, open(os.path.join(a.work, "plan.json"), "w"))

# 本体(入り〜指定小節)と、曲の終わり方を 0.12秒で重ねてつなぐ。音量は配信向けに -14 LUFS
f = (f"[0:a]atrim={plan['a0']}:{plan['a1']},asetpts=PTS-STARTPTS,afade=t=in:d=0.6[x];"
     f"[0:a]atrim={plan['b0']}:{plan['b1']},asetpts=PTS-STARTPTS[y];"
     f"[x][y]acrossfade=d=0.12:c1=tri:c2=tri,loudnorm=I=-14:TP=-1.0:LRA=11[o]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.song, "-filter_complex", f, "-map", "[o]",
                "-ar", "48000", "-c:a", "pcm_s16le", os.path.join(a.work, "audio.wav")], check=True)
print("wrote", os.path.join(a.work, "audio.wav"))
