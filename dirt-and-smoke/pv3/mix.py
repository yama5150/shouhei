#!/usr/bin/env python3
"""PV（姉妹版・約3分）の音を組み立てる。timeline.js と同じ秒数を使う。

使い方:  python3 mix.py   → 同じフォルダに mix.m4a ができる
"""
import subprocess, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(HERE, '..', 'audio')
LULLABY = os.path.join(AUD, 'dirt_and_smoke_unplugged.mp3')
THEME = os.path.join(AUD, 'dirt_and_smoke_guitar_ballad.mp3')
OUT = os.path.join(HERE, 'mix.m4a')
END = 183.0
SR = 44100

# 子守唄：(動画の開始秒, 動画の終了秒, 曲の開始秒, 速さ, 音量, フェードイン秒, フェードアウト秒)
# 速さを落とすと音程も下がる（歌が溶けていく）
LULL = [
    (0.0,   61.0,  0.0,    1.00, .60, 3.0, .03),
    (61.0,  62.84, 61.0,   0.92, .58, .03, .03),
    (62.84, 66.6,  None,   0.85, .52, .03, .03),
    (66.6,  74.6,  None,   0.78, .40, .03, .02),   # 74.6 で一瞬で消える
    (87.1,  101.0, 68.1,   0.70, .30, 3.0, 1.5),
]
THEME_AT, THEME_FROM, THEME_VOL = 116.0, 213.5, .95
BELL_AT = 0.3
BREATHS = [61.0, 61.7, 62.32, 62.84, 63.26, 63.64, 64.34, 64.60, 64.838, 65.054, 65.248, 65.42, 65.57,
           76.0, 76.8, 77.5, 78.1, 92.3, 93.32, 94.41]

def main():
    filters, labels, srcs = [], [], []
    # 子守唄の各区間
    prev_end_src = 0.0
    for i, (t0, t1, s0, r, v, fi, fo) in enumerate(LULL):
        if s0 is None: s0 = prev_end_src
        dur_src = (t1 - t0) * r
        prev_end_src = s0 + dur_src
        srcs.append(['-ss', f'{s0:.3f}', '-t', f'{dur_src:.3f}', '-i', LULLABY])
        idx = len(srcs) - 1
        d = t1 - t0
        filters.append(f'[{idx}:a]aresample={SR},asetrate={SR*r:.0f},aresample={SR},volume={v},'
                       f'afade=t=in:d={fi},afade=t=out:st={max(0,d-fo):.3f}:d={fo},adelay={int(t0*1000)}:all=1[l{i}]')
        labels.append(f'[l{i}]')
    # 主題歌
    srcs.append(['-ss', f'{THEME_FROM}', '-i', THEME]); idx = len(srcs) - 1
    filters.append(f'[{idx}:a]aresample={SR},volume={THEME_VOL},afade=t=in:d=0.15,adelay={int(THEME_AT*1000)}:all=1[th]')
    labels.append('[th]')
    # 鐘
    bell = '+'.join(f'{0.16/(k+1):.3f}*sin(2*PI*{f}*t)*exp(-t/1.6)' for k, f in enumerate([220, 441, 662, 883]))
    srcs.append(['-f', 'lavfi', '-t', '5', '-i', f'aevalsrc={bell}:s={SR}']); idx = len(srcs) - 1
    filters.append(f'[{idx}:a]aformat=channel_layouts=stereo,adelay={int(BELL_AT*1000)}:all=1[bell]'); labels.append('[bell]')
    # 息の音
    for j, bt in enumerate(BREATHS):
        srcs.append(['-f', 'lavfi', '-t', '0.5', '-i', f'anoisesrc=d=0.5:c=white:a=0.6:r={SR}:s={j+1}']); idx = len(srcs) - 1
        filters.append(f'[{idx}:a]bandpass=f=1200:width_type=q:w=0.8,volume=0.35,afade=t=in:d=0.22,afade=t=out:st=0.25:d=0.25,'
                       f'aformat=channel_layouts=stereo,adelay={int(bt*1000)}:all=1[br{j}]')
        labels.append(f'[br{j}]')
    filters.append(f'{"".join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0,'
                   f'apad=whole_dur={END},atrim=0:{END},alimiter=limit=0.95[out]')
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for a in srcs: cmd += a
    cmd += ['-filter_complex', ';'.join(filters), '-map', '[out]', '-c:a', 'aac', '-b:a', '192k', OUT]
    subprocess.run(cmd, check=True)
    print('wrote', OUT)

if __name__ == '__main__':
    main()
