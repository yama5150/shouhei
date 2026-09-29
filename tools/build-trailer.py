#!/usr/bin/env python3
"""Cyber Rose Crimson トレーラー(縦 1080x1920 / 30fps)を合成する。

使い方:
  python3 tools/build-trailer.py --music obscure.mp3 --sheet sheet-motion.mp4 \
      --fonts <フォントのあるディレクトリ> --out motion/trailer.mp4

素材:
  motion/koya-motion.mp4 / motion/tsukishio-motion.mp4  (12秒ループ。-stream_loop で延長して使う)
  --sheet   設定シートを動かした動画(448x672 / 24fps)
  --music   Track 01「obscure」
  --fonts   ShipporiMincho-Medium.ttf / ShipporiMincho-Bold.ttf / Cinzel[wght].ttf
必要なもの: numpy, pillow, imageio-ffmpeg
"""
import argparse, pathlib, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------- 曲の編集点 ----------
# obscure は 169.92 BPM。拍の格子 g(k) = 0.122 + k*BEAT 上で切ってつなぐ
BEAT = 60 / 169.92
A = (0.0, 14.246)                     # イントロ。2.96秒で鳴り出し、9.5秒で一段上がる
B = (91.930, 91.930 + 48 * BEAT)      # サビ 48拍
C = (190.094 - 6 * BEAT, 197.2)       # 終盤。190.21秒の決めの一撃へ
XF = 0.08                             # つなぎ目のクロスフェード
TB = A[1] - A[0]                      # トレーラー上でサビが始まる時刻
TC = TB + (B[1] - B[0])               # 終盤が始まる時刻
HIT = TC + (190.21 - C[0])            # 決めの一撃
TOTAL = TC + (C[1] - C[0])


def beat(n):
    """サビ頭から n 拍目のトレーラー時刻"""
    return TB + n * BEAT


# ---------- ショット ----------
# rect = (中心x, 中心y, 高さの割合)。開始 → 終了へ補間(Ken Burns)
KOYA, TIDE, SHEET = 'koya', 'tide', 'sheet'
FIT = (.5, .5, 1.2)                   # 高さ割合が 1 を超えたら全体をぼかし背景に収める


def shot(t0, t1, src, st, r0, r1=None, fx='cut', out=None):
    return dict(t0=t0, t1=t1, src=src, st=st, r0=r0, r1=r1 or r0, fx=fx, out=out)


SHOTS = [
    # イントロ:紅夜に寄っていく → 月潮の月から海へ
    shot(2.96, 10.30, KOYA, 0.0, (.5, .52, 1.0), (.52, .30, .55), fx='fade'),
    shot(10.30, TB, TIDE, 0.0, (.42, .16, .40), (.47, .30, .62), fx='fade'),
]
# サビ:4拍 → 2拍 → 1拍と詰めていく
chorus = [
    (SHEET, 0.0, FIT, FIT),
    (TIDE, 2.0, (.73, .48, .20), (.73, .50, .15)),       # ステージ
    (KOYA, 4.0, (.52, .23, .30), (.52, .24, .24)),       # 紅夜の顔
    (TIDE, 5.0, (.43, .22, .24), (.45, .26, .30)),       # 月と船
    (SHEET, 2.2, (.50, .62, .55), (.50, .66, .45)),
    (KOYA, 1.2, (.24, .15, .30), (.24, .16, .24)),       # 花火
    (TIDE, 7.0, (.51, .40, .22), (.50, .40, .17)),       # 鴉と海
    (TIDE, 3.0, (.25, .33, .36), (.26, .35, .28)),       # 月潮の横顔
    (SHEET, 4.0, (.30, .30, .45), (.32, .32, .38)),
    (KOYA, 7.0, (.60, .55, .60), (.58, .50, .50)),
    (TIDE, 9.0, (.47, .80, .30), (.47, .78, .24)),       # 足元の魔法陣
    (SHEET, 5.0, (.70, .40, .45), (.70, .42, .38)),
    (KOYA, 9.0, (.88, .27, .28), (.88, .27, .22)),       # 提灯
    (TIDE, 11.0, (.82, .10, .30), (.82, .10, .24)),      # 天井の魔法陣
    (SHEET, 1.0, (.25, .20, .40), (.27, .22, .33)),
    (TIDE, 1.0, (.74, .53, .16), (.75, .53, .12)),       # 薔薇の紋
    (KOYA, 10.0, (.52, .24, .22), (.52, .24, .18)),
    (SHEET, 5.6, FIT, FIT),
]
lens = [4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 5]
assert sum(lens) == 48 and len(lens) == len(chorus)
n = 0
for (src, st, r0, r1), L in zip(chorus, lens):
    SHOTS.append(shot(beat(n), beat(n + L), src, st, r0, r1, fx='flash'))
    n += L
# 終盤:月潮を暗く引いて、一撃でタイトル
SHOTS.append(shot(TC, HIT, TIDE, 6.0, (.45, .30, .55), (.45, .28, .75), fx='cut'))
SHOTS.append(shot(HIT, TOTAL, TIDE, 8.2, (.5, .45, 1.0), (.5, .42, .92), fx='hit', out='title'))

# ---------- 文字 ----------
TEXTS = [
    # (開始, 終了, 文言, 大きさ, y位置)
    (0.35, 2.75, '薔薇は、愛か、呪いか。', 64, .50),
    (3.40, 6.60, '音を奪われた世界で', 56, .80),
    (6.90, 10.10, '七度、封じられた心がある。', 56, .80),
    (11.00, 14.00, '――初めましてから、何回でも。', 52, .80),
    (beat(24), beat(32), '揺らぎは、心だ。', 60, .82),
]


def font(p, size):
    return ImageFont.truetype(str(p), size)


def text_layer(txt, size, fpath, glow=(200, 20, 70), spacing=6):
    """白文字+紅い滲み。RGBA を返す"""
    f = font(fpath, size)
    # 明朝に無い字(α など)は DejaVu Serif で補う
    alt = font('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', int(size * .9))
    fonts = [alt if ch in 'αβ' else f for ch in txt]
    tw = sum(ff.getlength(ch) + spacing for ch, ff in zip(txt, fonts))
    im = Image.new('RGBA', (int(tw) + 160, size * 2 + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 60
    for ch, ff in zip(txt, fonts):  # 字送りに少しだけ字間を足す
        d.text((x, 40 + size), ch, font=ff, fill=(255, 244, 248, 255), anchor='ls')  # ベースラインでそろえる
        x += ff.getlength(ch) + spacing
    x0, y0, x1, y1 = im.getbbox()
    im = im.crop((x0 - 40, y0 - 40, x1 + 40, y1 + 40))  # 滲みの余白を残して詰める
    a = np.asarray(im)[..., 3]
    g = Image.fromarray(a).filter(ImageFilter.GaussianBlur(size * .28))
    ga = (np.asarray(g).astype(float) * 1.6).clip(0, 255)
    out = np.zeros((*a.shape, 4))
    out[..., :3] = glow
    out[..., 3] = ga
    # 滲みの上に本体を重ねる
    fa = a.astype(float) / 255
    out[..., :3] = out[..., :3] * (1 - fa[..., None]) + np.asarray(im)[..., :3] * fa[..., None]
    out[..., 3] = np.maximum(out[..., 3], a)
    return out.astype(np.float32)


# ---------- 素材の読み出し ----------
class Reader:
    """ffmpeg から 1 ショット分のフレームを順に読む"""
    def __init__(self, path, st, n, native):
        self.w, self.h = native
        cmd = [FF, '-loglevel', 'error', '-stream_loop', '-1', '-ss', f'{st:.3f}', '-i', str(path),
               '-map', '0:v:0', '-vf', f'fps={FPS}', '-frames:v', str(n + 2),
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.last = None

    def next(self):
        b = self.p.stdout.read(self.w * self.h * 3)
        if len(b) == self.w * self.h * 3:
            self.last = Image.frombytes('RGB', (self.w, self.h), b)
        return self.last

    def close(self):
        self.p.stdout.close(); self.p.wait()


def ease(x):
    return x * x * (3 - 2 * x)


def frame_from(img, rect, src):
    cx, cy, hs = rect
    sw, sh = img.size
    ch = sh * hs
    cw = ch * W / H
    if hs > 1:  # シート動画の全体表示 → ぼかした背景に収める
        fg = img.resize((W, int(sh * W / sw)), Image.LANCZOS)
        bg = img.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BICUBIC)
        bg = Image.fromarray((np.asarray(bg) * .45).astype(np.uint8))
        bg.paste(fg, (0, (H - fg.size[1]) // 2 + int((.5 - cy) * H)))
        return bg
    x0 = min(max(cx * sw - cw / 2, 0), sw - cw)
    y0 = min(max(cy * sh - ch / 2, 0), sh - ch)
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--music', required=True)
    ap.add_argument('--sheet', required=True)
    ap.add_argument('--fonts', required=True)
    ap.add_argument('--out', default=str(ROOT / 'motion' / 'trailer.mp4'))
    ap.add_argument('--preview', type=float, nargs='*', help='この時刻の静止画だけ書き出す')
    a = ap.parse_args()
    fdir = pathlib.Path(a.fonts)
    MED, BOLD, CINZEL = fdir / 'ShipporiMincho-Medium.ttf', fdir / 'ShipporiMincho-Bold.ttf', fdir / 'Cinzel[wght].ttf'

    SRC = {KOYA: (ROOT / 'motion' / 'koya-motion.mp4', (1080, 1920)),
           TIDE: (ROOT / 'motion' / 'tsukishio-motion.mp4', (1080, 1920)),
           SHEET: (pathlib.Path(a.sheet), (448, 672))}

    texts = [(t0, t1, text_layer(s, sz, MED, spacing=3), y) for t0, t1, s, sz, y in TEXTS]
    title = text_layer('CYBER ROSE', 118, CINZEL, spacing=14)
    title2 = text_layer('CRIMSON', 150, CINZEL, glow=(230, 10, 50), spacing=22)
    copy1 = text_layer('全12話＋α のノベル × アルバム', 44, MED)
    copy2 = text_layer('iPhoneひとつで、遊べる。', 44, MED)

    yy, xx = np.mgrid[0:H, 0:W]
    vign = (1 - (((xx / W - .5) ** 2) + ((yy / H - .5) ** 2) * .6) * 1.1).clip(.3, 1)[..., None].astype(np.float32)

    def paste(fr, layer, cx, cy, alpha):
        if alpha <= 0: return
        h, w = layer.shape[:2]
        x0, y0 = int(cx * W - w / 2), int(cy * H - h / 2)
        xs, ys = max(0, -x0), max(0, -y0)
        xe, ye = min(w, W - x0), min(h, H - y0)
        sub = fr[y0 + ys:y0 + ye, x0 + xs:x0 + xe]
        L = layer[ys:ye, xs:xe]
        al = L[..., 3:4] / 255 * alpha
        sub[:] = sub * (1 - al) + L[..., :3] * al

    N = int(round(TOTAL * FPS))
    frames = range(N) if not a.preview else sorted(int(t * FPS) for t in a.preview)
    enc = None
    if not a.preview:
        silent = str(pathlib.Path(a.out).with_suffix('.v.mp4'))
        enc = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow',
                                '-crf', '23', '-pix_fmt', 'yuv420p', silent], stdin=subprocess.PIPE)

    cur, reader = None, None
    for i in frames:
        t = i / FPS
        s = next((s for s in SHOTS if s['t0'] <= t < s['t1']), None)
        if s is None:
            fr = np.zeros((H, W, 3), np.float32)
        else:
            if cur is not s or a.preview:
                if reader: reader.close()
                path, native = SRC[s['src']]
                n = int((s['t1'] - s['t0']) * FPS) + 2
                st = s['st'] + (t - s['t0']) if a.preview else s['st']
                reader, cur = Reader(path, st, n, native), s
            img = reader.next()
            k = ease((t - s['t0']) / (s['t1'] - s['t0']))
            rect = tuple(p + (q - p) * k for p, q in zip(s['r0'], s['r1']))
            fr = np.asarray(frame_from(img, rect, s['src'])).astype(np.float32)
            dt = t - s['t0']
            if s['fx'] == 'fade':
                fr *= min(1, dt / .6)
            elif s['fx'] == 'flash':  # 拍の頭で紅く光る
                f = np.exp(-dt * 14)
                fr = fr + np.array([255, 70, 110], np.float32) * f * .55
            elif s['fx'] == 'hit':
                f = np.exp(-dt * 5)
                fr = fr * (.35 + .1 * min(1, dt)) + 255 * f * .9
            if s['src'] == TIDE and s is SHOTS[-2]:
                fr *= .55 - .25 * k
            if dt > (s['t1'] - s['t0']) - .5 and s is SHOTS[1]:
                fr *= max(0, ((s['t1'] - s['t0']) - dt) / .5) * .7 + .3
        fr *= vign
        for t0, t1, L, y in texts:
            if t0 <= t < t1:
                al = min(1, (t - t0) / .5, (t1 - t) / .5)
                paste(fr, L, .5, y + .006 * (1 - al), al)
        if t >= HIT:
            dt = t - HIT
            end = min(1, (TOTAL - t) / 1.2)
            paste(fr, title, .5, .43, min(1, dt / .15) * end)
            paste(fr, title2, .5, .50, min(1, dt / .15) * end)
            paste(fr, copy1, .5, .62, min(1, max(0, dt - 1.2) / .8) * end)
            paste(fr, copy2, .5, .66, min(1, max(0, dt - 1.8) / .8) * end)
        if t > TOTAL - 1.2:
            fr *= max(0, (TOTAL - t) / 1.2)
        out = fr.clip(0, 255).astype(np.uint8)
        if a.preview:
            Image.fromarray(out).save(pathlib.Path(a.out).parent / f'preview-{t:05.2f}.jpg', quality=85)
        else:
            enc.stdin.write(out.tobytes())
        if i % 150 == 0: print(f'{t:5.1f}s / {TOTAL:.1f}s', file=sys.stderr)
    if reader: reader.close()
    if a.preview: return
    enc.stdin.close(); enc.wait()

    # 音:3区間を拍の上でつなぐ
    fc = (f'[1:a]atrim={A[0]}:{A[1] + XF},asetpts=PTS-STARTPTS[a];'
          f'[1:a]atrim={B[0] - XF}:{B[1] + XF},asetpts=PTS-STARTPTS[b];'
          f'[1:a]atrim={C[0] - XF}:{C[1]},asetpts=PTS-STARTPTS,afade=t=out:st={C[1] - C[0] - 1.4}:d=1.4[c];'
          f'[a][b]acrossfade=d={2 * XF}:c1=tri:c2=tri[ab];[ab][c]acrossfade=d={2 * XF}:c1=tri:c2=tri[m]')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', silent, '-i', a.music, '-filter_complex', fc,
                    '-map', '0:v', '-map', '[m]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', a.out], check=True)
    pathlib.Path(silent).unlink()
    print('wrote', a.out, f'{TOTAL:.2f}s')


if __name__ == '__main__':
    main()
