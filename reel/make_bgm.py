#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
リール用のオリジナル BGM を合成する (和モダン / 84BPM / Aマイナーペンタトニック)。

既成曲を使うと権利の確認が要るので、琴ふうの撥弦・太鼓ふうのキック・
パッドをその場で合成している。完全なオリジナルなので、どこに出しても
権利まわりの心配がない。

    python3 reel/make_bgm.py [長さ秒]     -> reel/out/bgm.wav
"""

import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 48000
BPM = 84.0
BEAT = 60.0 / BPM          # 0.714s
BAR = BEAT * 4             # 2.857s

OUT = Path(__file__).resolve().parent / "out" / "bgm.wav"

_PITCH = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
          "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(name):
    """'A3' のような音名を周波数に。"""
    return 440.0 * 2 ** ((_PITCH[name[:-1]] + 12 * (int(name[-1]) + 1) - 69) / 12)


# ---------------------------------------------------------------- 音色

def pluck(freq, dur, amp=1.0, decay=0.9965, tone=0.55):
    """Karplus-Strong の撥弦。琴・三味線っぽい減衰の速い音。"""
    n = max(int(SR / freq), 2)
    rng = np.random.default_rng(int(freq * 100) % 65536)
    buf = rng.uniform(-1, 1, n)
    buf = np.convolve(buf, np.ones(5) / 5, mode="same")   # 角を落として柔らかく

    out = np.zeros(int(dur * SR))
    idx = 0
    prev = 0.0
    for i in range(out.size):
        cur = buf[idx]
        out[i] = cur
        # ループ内で軽くローパス。tone が小さいほどこもる
        filtered = tone * cur + (1 - tone) * prev
        buf[idx] = decay * 0.5 * (filtered + buf[(idx + 1) % n])
        prev = cur
        idx = (idx + 1) % n

    # 頭のアタックだけ立てる
    env = np.ones(out.size)
    a = int(0.004 * SR)
    env[:a] = np.linspace(0, 1, a)
    env *= np.exp(-np.linspace(0, dur, out.size) * 1.4)
    return amp * out * env


def taiko(dur=0.55, amp=1.0):
    """太鼓ふうの低い一発。ピッチが落ちながら減衰する。"""
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    freq = 46 + 95 * np.exp(-t * 26)
    body = np.sin(np.cumsum(2 * np.pi * freq / SR)) * np.exp(-t * 7.5)
    rng = np.random.default_rng(7)
    click = rng.normal(0, 1, t.size) * np.exp(-t * 260) * 0.35
    return amp * (body + click)


def shaker(dur=0.09, amp=1.0):
    """裏拍に置く軽いノイズ。刻みを感じさせるだけの役。"""
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    rng = np.random.default_rng(11)
    n = rng.normal(0, 1, t.size)
    n = np.diff(np.concatenate([[0.0], n]))          # 簡易ハイパス
    return amp * n * np.exp(-t * 42)


def pad(freqs, dur, amp=1.0):
    """やわらかいパッド。倍音の少ないノコギリ波をローパスして重ねる。"""
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    sig = np.zeros(t.size)
    for f in freqs:
        for det in (-4.0, 0.0, 4.0):                 # セント単位のデチューン
            ff = f * 2 ** (det / 1200)
            ph = (t * ff) % 1.0
            sig += (2 * ph - 1) / len(freqs)

    # 一次ローパス (カットオフ 700Hz くらい)
    k = np.exp(-2 * np.pi * 700 / SR)
    y = np.zeros_like(sig)
    acc = 0.0
    for i, v in enumerate(sig):
        acc = (1 - k) * v + k * acc
        y[i] = acc

    env = np.minimum(t / 0.6, 1.0) * np.minimum((dur - t) / 1.1, 1.0)
    return amp * y * np.clip(env, 0, 1) * 0.13


def bass(freq, dur, amp=1.0):
    """下を支えるだけのサイン。倍音を少しだけ足す。"""
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    sig = np.sin(2 * np.pi * freq * t) + 0.22 * np.sin(4 * np.pi * freq * t)
    env = np.minimum(t / 0.12, 1.0) * np.minimum((dur - t) / 0.45, 1.0)
    return amp * sig * np.clip(env, 0, 1)


# ---------------------------------------------------------------- 構成

# 2 小節ずつのコード進行。Am - F - C - G - Am
PROGRESSION = [
    ("A2", ["A3", "C4", "E4"]),
    ("F2", ["F3", "A3", "C4"]),
    ("C3", ["C4", "E4", "G4"]),
    ("G2", ["G3", "B3", "D4"]),
    ("A2", ["A3", "C4", "E4"]),
]

# 小節ごとの琴のフレーズ（コード構成音のインデックス + ペンタの経過音）
KOTO_BARS = [
    [(0.0, "A4"), (1.0, "E4"), (2.0, "C5"), (3.0, "A4")],
    [(0.0, "E4"), (1.5, "A4"), (2.0, "C5"), (3.0, "D5"), (3.5, "C5")],
    [(0.0, "F4"), (1.0, "C5"), (2.0, "A4"), (3.0, "F4")],
    [(0.0, "C5"), (1.5, "A4"), (2.0, "F4"), (3.0, "G4")],
    [(0.0, "C5"), (1.0, "G4"), (2.0, "E4"), (3.0, "C5")],
    [(0.0, "G4"), (1.5, "C5"), (2.0, "E5"), (3.0, "D5"), (3.5, "C5")],
    [(0.0, "D5"), (1.0, "B4"), (2.0, "G4"), (3.0, "D5")],
    [(0.0, "B4"), (1.5, "D5"), (2.0, "G4"), (3.0, "A4")],
    [(0.0, "A4"), (1.0, "E4"), (2.0, "C5"), (3.0, "E5")],
    [(0.0, "A4"), (2.0, "E4")],
]


def reverb(sig, amount=0.26, tail=1.4):
    """指数減衰のノイズを畳み込んだ簡易リバーブ。

    ウェットは元信号と同じ RMS に合わせてから混ぜる。ここを揃えないと
    拡散音だけが大きくなって、全体にサーッとしたノイズが乗ってしまう。
    """
    n = int(tail * SR)
    rng = np.random.default_rng(3)
    ir = rng.normal(0, 1, n) * np.exp(-np.linspace(0, tail, n) * 5.0)
    ir[: int(0.006 * SR)] = 0.0                 # 直接音は原音側で担当する
    wet = fftconvolve(sig, ir)[: sig.size]

    rms_dry = np.sqrt(np.mean(sig ** 2)) or 1e-9
    rms_wet = np.sqrt(np.mean(wet ** 2)) or 1e-9
    wet *= rms_dry / rms_wet
    return (1 - amount) * sig + amount * wet


def add(buf, sig, at):
    i = int(at * SR)
    j = min(buf.size, i + sig.size)
    if i < buf.size:
        buf[i:j] += sig[: j - i]


def compose(duration):
    total = duration + 2.0                     # 余韻ぶんを足して後で切る
    n = int(total * SR)
    koto = np.zeros(n)
    low = np.zeros(n)
    perc = np.zeros(n)
    pads = np.zeros(n)

    bars = len(KOTO_BARS)
    for b in range(bars):
        t0 = b * BAR
        if t0 > duration:
            break
        root, chord = PROGRESSION[min(b // 2, len(PROGRESSION) - 1)]

        # ベースとパッドは 2 小節つづき。次のコードに 1 秒ぶんかぶせて、
        # 切り替わりで音が途切れないようにしている
        if b % 2 == 0:
            add(low, bass(hz(root), BAR * 2 + 0.30, amp=0.30), t0)
            add(pads, pad([hz(x) for x in chord], BAR * 2 + 1.10, amp=1.0), t0)

        # 琴
        for beat, name in KOTO_BARS[b]:
            vel = 0.34 if beat == 0.0 else 0.22
            add(koto, pluck(hz(name), 2.2, amp=vel), t0 + beat * BEAT)

        # 打楽器は 3 小節目から入れて、最後の小節で抜く
        if 2 <= b < bars - 1:
            add(perc, taiko(amp=0.42), t0)
            add(perc, taiko(amp=0.26), t0 + 2 * BEAT)
            for k in (1, 3):
                add(perc, shaker(amp=0.12), t0 + (k + 0.5) * BEAT)

    koto = reverb(koto, amount=0.30)
    pads = reverb(pads, amount=0.22)
    mix = koto + low + perc + pads

    # 全体を少しだけ丸める
    mix = np.tanh(mix * 1.25) / 1.25

    # ステレオ化。琴とパッドだけ左右に広げる
    delay = int(0.011 * SR)
    left = mix.copy()
    right = mix.copy()
    spread = 0.35 * np.concatenate([np.zeros(delay), (koto + pads)[:-delay]])
    left += spread
    right -= spread

    stereo = np.stack([left, right], axis=1)
    stereo /= max(np.abs(stereo).max(), 1e-9)
    stereo *= 0.72                               # -2.8dBFS くらい

    # 頭とお尻をならす
    keep = int(duration * SR)
    stereo = stereo[: keep + int(1.6 * SR)]
    a = int(0.35 * SR)
    stereo[:a] *= np.linspace(0, 1, a)[:, None]
    r = int(1.6 * SR)
    stereo[-r:] *= np.linspace(1, 0, r)[:, None]
    return stereo


if __name__ == "__main__":
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 27.2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    audio = compose(dur)
    wavfile.write(OUT, SR, (audio * 32767).astype(np.int16))
    print(f"   完成: {OUT}  {audio.shape[0] / SR:.1f}秒")
