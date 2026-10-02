#!/usr/bin/env python3
"""Cyber Rose Crimson トレーラー(縦 1080x1920 / 30fps)を合成する。

使い方:
  python3 tools/build-trailer.py --cut 40 --music obscure.mp3 --sheet sheet-motion.mp4 \
      --fonts <フォントのあるディレクトリ> --out motion/trailer.mp4
  python3 tools/build-trailer.py --cut 30 --music obscure.mp3 --sheet sheet-motion.mp4 \
      --yuji yuji.png --fonts <フォントのあるディレクトリ> --out motion/trailer-30s.mp4
  python3 tools/build-trailer.py --cut eruza --music <リマスター版.m4a> --sheet sheet-motion.mp4 \
      --stills <静止画のディレクトリ> --fonts <フォントのあるディレクトリ> --out motion/trailer-eruza.mp4

素材:
  motion/koya-motion.mp4 / motion/tsukishio-motion.mp4  (12秒ループ。-stream_loop で延長して使う)
  --sheet   設定シートを動かした動画(448x672 / 24fps)
  --yuji    30秒版のみ。雨の夜に手を取るユウジの一枚絵(正方形)
  --stills  eruza 版のみ。下の STILLS の名前.png を置いたディレクトリ
            (eden / yuji と、CRC_trailer_18s.mp4 から抜いた sea workshop coffee city rose
             redmoon mecha sword kimono titlebg)
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
HIT_SONG = 190.21                     # 終盤の決めの一撃(曲の時刻)
XF = 0.08                             # つなぎ目のクロスフェード
KOYA, TIDE, SHEET, YUJI, MOON = 'koya', 'tide', 'sheet', 'yuji', 'moon'
# eruza 版で使う一枚絵(--stills の中の 名前.png)
STILLS = ['eden', 'yuji', 'sea', 'workshop', 'coffee', 'city', 'rose', 'redmoon', 'mecha', 'sword', 'kimono', 'titlebg']
FIT = (.5, .5, 1.2)                   # 高さ割合が 1 を超えたら全体をぼかし背景に収める


def shot(t0, t1, src, st, r0, r1=None, fx='cut', dim=None, fadeout=False, rain=False):
    """rect = (中心x, 中心y, 高さの割合)。開始 → 終了へ補間(Ken Burns)"""
    return dict(t0=t0, t1=t1, src=src, st=st, r0=r0, r1=r1 or r0, fx=fx, dim=dim, fadeout=fadeout, rain=rain)


# サビのカット候補(素材, 素材の開始秒, 始めの枠, 終わりの枠)
CHORUS = [
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


def chorus_shots(t0, picks, lens):
    out, n = [], 0
    for (src, st, r0, r1), L in zip(picks, lens):
        out.append(shot(t0 + n * BEAT, t0 + (n + L) * BEAT, src, st, r0, r1, fx='flash'))
        n += L
    return out


def plan(cut):
    """曲の区間(曲の時刻), ショット, 文字, 一撃の時刻, 全長 を返す"""
    if cut == 40:
        segs = [(0.0, 14.246),                        # イントロ。2.96秒で鳴り出し、9.5秒で一段上がる
                (91.930, 91.930 + 48 * BEAT),         # サビ 48拍
                (HIT_SONG - .116 - 6 * BEAT, 197.2)]  # 終盤。一撃の6拍前から
        TB = segs[0][1]
        TC = TB + segs[1][1] - segs[1][0]
        shots = [
            shot(2.96, 10.30, KOYA, 0.0, (.5, .52, 1.0), (.52, .30, .55), fx='fade'),
            shot(10.30, TB, TIDE, 0.0, (.42, .16, .40), (.47, .30, .62), fx='fade', fadeout=True),
        ]
        shots += chorus_shots(TB, CHORUS, [4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 5])
        texts = [
            (0.35, 2.75, '薔薇は、愛か、呪いか。', 64, .50),
            (3.40, 6.60, '音を奪われた世界で', 56, .80),
            (6.90, 10.10, '七度、封じられた心がある。', 56, .80),
            (11.00, 14.00, '――初めましてから、何回でも。', 52, .80),
            (TB + 24 * BEAT, TB + 32 * BEAT, '揺らぎは、心だ。', 60, .82),
        ]
    elif cut == 30:
        segs = [(0.0, 0.122 + 19 * BEAT),             # イントロを短く
                (91.930, 91.930 + 28 * BEAT),         # サビ 28拍
                (112.060, 112.060 + 16 * BEAT),       # 曲が引く16拍 ― ユウジ
                (HIT_SONG - .116 - 6 * BEAT, 195.4)]  # 終盤
        TB = segs[0][1]
        TD = TB + segs[1][1] - segs[1][0]
        TC = TD + segs[2][1] - segs[2][0]
        picks = [CHORUS[i] for i in (0, 1, 2, 3, 5, 4, 7, 12, 15, 8, 16)]  # ユウジはサビに出さず、曲が引いたところで初めて見せる
        shots = [shot(2.96, TB, KOYA, 0.0, (.5, .52, 1.0), (.52, .32, .62), fx='fade')]
        shots += chorus_shots(TB, picks, [4, 4, 4, 2, 2, 2, 2, 2, 1, 1, 4])
        # 手を取る。繋いだ手から引いて、顔が見えたところで止まる
        shots.append(shot(TD, TC, YUJI, 0, (.56, .74, .42), (.55, .50, .98), fx='fade', rain=True, fadeout=True))
        texts = [
            (0.35, 2.75, '薔薇は、愛か、呪いか。', 64, .50),
            (3.30, 6.60, '音を奪われた世界で', 56, .80),
            (TB + 12 * BEAT, TB + 20 * BEAT, '揺らぎは、心だ。', 60, .82),
            (TD + 1.2, TC - .1, '――初めましてから、何回でも。', 52, .86),
        ]
    elif cut == 'eruza':
        return plan_eruza()
    else:
        raise SystemExit(f'--cut は 40 / 30 / eruza: {cut}')
    HIT = TC + (HIT_SONG - segs[-1][0])
    TOTAL = TC + segs[-1][1] - segs[-1][0]
    # 終盤:月潮を暗く引いて、一撃でタイトル
    shots.append(shot(TC, HIT, TIDE, 6.0, (.45, .30, .55), (.45, .28, .75), dim=(.55, .30)))
    shots.append(shot(HIT, TOTAL, TIDE, 8.2, (.5, .45, 1.0), (.5, .42, .92), fx='hit'))
    return segs, shots, texts, HIT, TOTAL, {}


# ---------- eruza 版:リマスター版の歌詞で見せる ----------
# 曲は 94.58 BPM。拍の格子 g(k) = 0.144 + k*EBEAT(曲の時刻)。曲は切らずに1本で使う
EBEAT = 60 / 94.58
S0 = 0.144 + 67 * EBEAT               # 「君のコードが 私を呼んでる」の頭
S_END = 100.7                         # 2番の歌い出し(100.85秒)の手前まで
SUNO_HANDLE = '@shou.5150'            # Suno で検索できるよう名前は画面に残す
LYRICS = [  # 曲の時刻(埋め込みの歌詞データから)
    (42.686, '君のコードが　私を呼んでる'),
    (47.074, '記憶をアップロード　空へ投げて'),
    (53.059, 'データの海で　離さないで'),
    (58.324, '仮想のキスを　本物に変えて'),
    (62.394, '今夜、運命さえ組み替える'),
    (68.138, 'エルザ　サイバーローズの花咲く夜'),
    (73.564, '未来を染める　光の香り'),
    (80.186, 'エルザ　ホログラムの微笑み'),
    (84.415, '幻でもいい　そう、君となら真実'),
]


def plan_eruza():
    g = lambda k: 0.144 + k * EBEAT - S0          # k 拍目のトレーラー時刻
    HIT = g(143)                                  # サビを歌い切ったところでタイトル
    TOTAL = S_END - S0
    cuts = [  # (始めの拍, 素材, 素材の開始秒, 始めの枠, 終わりの枠, 効果)
        # 導入:血の夜のエルザに雨。顔へ寄る
        (67, 'eden', 0, (.50, .45, 1.0), (.44, .30, .62), 'fade'),
        # プレコーラス:4拍ずつ
        (74, 'sea', 0, (.30, .18, .40), (.26, .16, .32), 'cut'),            # 312年、海の底
        (78, MOON, 0.0, (.45, .30, .95), (.42, .22, .70), 'cut'),           # 紅月
        (83, TIDE, 4.0, (.50, .36, .30), (.50, .38, .24), 'cut'),           # データの海
        (87, 'workshop', 0, (.50, .40, .55), (.52, .42, .45), 'cut'),       # 月島電脳修理店
        (91, KOYA, 5.0, (.52, .24, .30), (.52, .24, .25), 'cut'),           # 紅夜の顔
        (95, 'coffee', 0, (.45, .30, .55), (.45, .28, .46), 'cut'),
        (98, 'eden', 0, (.93, .25, .44), (.93, .24, .38), 'cut'),           # 「音楽は、世界を変える」
        (102, 'rose', 0, (.50, .40, .60), (.50, .38, .50), 'cut'),
        (104, 'eden', 0, (.07, .22, .34), (.07, .20, .28), 'cut'),          # Cyber Rose Project
        # サビ:2拍ずつ、拍の頭で紅く光る
        (107, SHEET, 0.0, FIT, FIT, 'flash'),
        (111, 'redmoon', 0, (.50, .36, .70), (.50, .34, .58), 'flash'),
        (113, KOYA, 1.2, (.24, .15, .30), (.24, .16, .24), 'flash'),        # 花火
        (115, 'city', 0, (.50, .32, .58), (.50, .30, .48), 'flash'),
        (117, TIDE, 2.0, (.73, .48, .20), (.73, .50, .15), 'flash'),        # ステージ
        (119, 'mecha', 0, (.50, .42, .70), (.50, .40, .58), 'flash'),
        (121, KOYA, 9.0, (.88, .27, .28), (.88, .27, .22), 'flash'),        # 提灯
        (123, TIDE, 5.0, (.43, .22, .24), (.45, .26, .30), 'flash'),        # 月と船
        (125, 'sword', 0, (.50, .30, .55), (.50, .28, .45), 'flash'),
        (127, MOON, 3.0, (.62, .28, .55), (.62, .26, .45), 'flash'),        # 紅月の横顔
        (128, 'eden', 0, (.42, .26, .34), (.42, .25, .28), 'flash'),
        (129, 'kimono', 0, (.45, .33, .55), (.45, .30, .46), 'flash'),
        (131, SHEET, 2.2, (.50, .62, .55), (.50, .66, .45), 'flash'),
        # 「幻でもいい そう、君となら真実」:繋いだ手から引いてユウジ → エルザの顔
        (133, 'yuji', 0, (.56, .74, .42), (.55, .50, .98), 'fade'),
        (139, 'eden', 0, (.43, .27, .40), (.43, .26, .30), 'fade'),
        (143, 'titlebg', 0, (.50, .32, .58), (.50, .30, .52), 'hit'),
    ]
    shots = []
    for j, (k, src, st, r0, r1, fx) in enumerate(cuts):
        t1 = g(cuts[j + 1][0]) if j + 1 < len(cuts) else TOTAL
        rain = src in ('eden', 'yuji')
        shots.append(shot(g(k), t1, src, st, r0, r1, fx=fx, rain=rain,
                          fadeout=src in ('eden',) and j + 1 < len(cuts) and cuts[j + 1][5] == 'fade',
                          dim=(.9, .6) if k == 139 else None))
    texts = []
    for j, (ts, line) in enumerate(LYRICS):
        te = LYRICS[j + 1][0] - .15 if j + 1 < len(LYRICS) else HIT + S0 - .25
        texts.append((ts - S0, te - S0, line, 50, .86))
    return [(S0, S_END)], shots, texts, HIT, TOTAL, {'credit': 'Music: shou.5150', 'card': True}


def font(p, size):
    return ImageFont.truetype(str(p), size)


def text_layer(txt, size, fpath, glow=(200, 20, 70), spacing=6):
    """白文字+紅い滲み。RGBA を返す"""
    f = font(fpath, size)
    # 明朝に無い字(α など)は DejaVu Serif で補う
    alt = font('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', int(size * .9))
    sym = font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', int(size * .8))   # ▶ ♪ など
    fonts = [alt if ch in 'αβ' else sym if ch in '▶♪' else f for ch in txt]
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


class Still:
    """一枚絵をショットの長さだけ返す"""
    def __init__(self, img): self.img = img
    def next(self): return self.img
    def close(self): pass


def rain_layer(seed=3):
    """斜めに降る雨。縦に2画面ぶん作って、毎フレームずらして使う"""
    r = np.random.default_rng(seed)
    im = Image.new('L', (W, H * 2), 0)
    d = ImageDraw.Draw(im)
    for _ in range(900):
        x, y = r.uniform(-200, W), r.uniform(0, H * 2)
        L = r.uniform(30, 90)
        d.line([(x, y), (x + L * .18, y + L)], fill=int(r.uniform(40, 120)), width=1 if r.random() < .8 else 2)
    im = im.filter(ImageFilter.GaussianBlur(.6))
    return np.asarray(im).astype(np.float32) / 255


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
    ap.add_argument('--cut', default='40', help='40 / 30(秒)/ eruza')
    ap.add_argument('--music', required=True)
    ap.add_argument('--sheet', required=True)
    ap.add_argument('--yuji', help='30秒版で使うユウジの一枚絵')
    ap.add_argument('--stills', help='eruza 版で使う一枚絵のディレクトリ')
    ap.add_argument('--fonts', required=True)
    ap.add_argument('--out', default=str(ROOT / 'motion' / 'trailer.mp4'))
    ap.add_argument('--preview', type=float, nargs='*', help='この時刻の静止画だけ書き出す')
    a = ap.parse_args()
    fdir = pathlib.Path(a.fonts)
    MED, BOLD, CINZEL = fdir / 'ShipporiMincho-Medium.ttf', fdir / 'ShipporiMincho-Bold.ttf', fdir / 'Cinzel[wght].ttf'

    cut = int(a.cut) if a.cut.isdigit() else a.cut
    segs, SHOTS, TEXTS, HIT, TOTAL, END = plan(cut)
    if cut == 30 and not a.yuji: raise SystemExit('30秒版には --yuji が要る')
    if cut == 'eruza' and not a.stills: raise SystemExit('eruza 版には --stills が要る')
    stills = {}
    if a.yuji: stills[YUJI] = Image.open(a.yuji).convert('RGB')
    if a.stills:
        for n in STILLS: stills[n] = Image.open(pathlib.Path(a.stills) / f'{n}.png').convert('RGB')
    rain = rain_layer()
    SRC = {KOYA: (ROOT / 'motion' / 'koya-motion.mp4', (1080, 1920)),
           TIDE: (ROOT / 'motion' / 'tsukishio-motion.mp4', (1080, 1920)),
           SHEET: (pathlib.Path(a.sheet), (448, 672)),
           MOON: (ROOT / 'motion' / 'kougetsu-motion.mp4', (1320, 960))}

    texts = [(t0, t1, text_layer(s, sz, MED, spacing=3), y) for t0, t1, s, sz, y in TEXTS]
    title = text_layer('CYBER ROSE', 118, CINZEL, spacing=14)
    title2 = text_layer('CRIMSON', 150, CINZEL, glow=(230, 10, 50), spacing=22)
    copy1 = text_layer('全12話＋α のノベル × アルバム', 44, MED)
    copy2 = text_layer('iPhoneひとつで、遊べる。', 44, MED)
    credit_l = text_layer(END['credit'], 40, MED, glow=(120, 60, 140), spacing=2) if END.get('credit') else None
    if END.get('card'):  # 商品説明と導線
        small1 = text_layer('CYBER ROSE', 64, CINZEL, spacing=8)
        small2 = text_layer('CRIMSON', 82, CINZEL, glow=(230, 10, 50), spacing=12)
        feats = [text_layer(x, 42, MED, spacing=2) for x in (
            '全12話＋α のノベル × アルバム',
            '曲が物語の中で鳴る、再生する物語アルバム',
            '収録曲 全11曲 ／ MUSIC ROOM 搭載',
            'iPhoneひとつで、遊べる。')]
        # 動画の中の URL は押せないので、押せるリンクはプロフィールのリンクページ(links/)に置く
        play_h = text_layer('▶ PLAY   /   ♪ LISTEN', 46, CINZEL, glow=(230, 10, 50), spacing=6)
        play_u = text_layer('ゲームと音楽は、プロフィールのリンクから', 46, MED, glow=(230, 10, 50), spacing=2)
        suno_h = text_layer('♪ MUSIC ON SUNO', 40, CINZEL, glow=(150, 60, 220), spacing=6)
        suno_u = text_layer(SUNO_HANDLE, 46, MED, glow=(150, 60, 220), spacing=1)
        rule = np.zeros((6, 640, 4), np.float32); rule[..., :3] = (220, 60, 110)
        rule[..., 3] = (255 * np.sin(np.linspace(0, np.pi, 640)) ** 2)[None, :] * .8

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
                if s['src'] in stills:
                    reader, cur = Still(stills[s['src']]), s
                else:
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
            if s['dim']:
                fr *= s['dim'][0] + (s['dim'][1] - s['dim'][0]) * k
            if s['rain']:  # 雨と、街灯に濡れた紅い照り返し
                off = int(t * 1400) % H
                rr = rain[H - off:2 * H - off, :, None]
                fr = fr * (1 - rr * .35) + np.array([255, 205, 220], np.float32) * rr * .45
            if s['fadeout'] and dt > (s['t1'] - s['t0']) - .5:
                fr *= max(0, ((s['t1'] - s['t0']) - dt) / .5) * .7 + .3
        fr *= vign
        for t0, t1, L, y in texts:
            if t0 <= t < t1:
                al = min(1, (t - t0) / .5, (t1 - t) / .5)
                paste(fr, L, .5, y + .006 * (1 - al), al)
        if t >= HIT:
            dt = t - HIT
            end = min(1, (TOTAL - t) / 1.2)
            if END.get('card'):
                # 一撃でタイトル → 2.4秒後に商品説明のカードへ
                ph2 = min(1, max(0, dt - 2.4) / .5)
                a1 = min(1, dt / .15) * (1 - ph2)
                paste(fr, title, .5, .43, a1)
                paste(fr, title2, .5, .50, a1)
                paste(fr, credit_l, .5, .60, min(1, max(0, dt - .6) / .6) * (1 - ph2))
                if ph2 > 0:
                    fr *= 1 - .45 * ph2                     # 文字が読めるよう背景を沈める
                    fade = lambda d: min(1, max(0, dt - 2.4 - d) / .4) * end
                    paste(fr, small1, .5, .17, fade(0))
                    paste(fr, small2, .5, .215, fade(0))
                    paste(fr, rule, .5, .265, fade(.2))
                    for j, L in enumerate(feats):
                        paste(fr, L, .5, .31 + j * .045, fade(.3 + j * .15))
                    paste(fr, rule, .5, .50, fade(.9))
                    paste(fr, play_h, .5, .56, fade(1.0))
                    paste(fr, play_u, .5, .605, fade(1.1))
                    paste(fr, suno_h, .5, .69, fade(1.3))
                    paste(fr, suno_u, .5, .735, fade(1.4))
            else:
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

    # 音:区間を拍の上でつなぐ。つなぎ目の前後 XF ずつ重ねる
    parts, n = [], len(segs)
    for j, (s0, s1) in enumerate(segs):
        lo = s0 - (XF if j else 0)
        hi = s1 + (XF if j < n - 1 else 0)
        tail = f',afade=t=out:st={hi - lo - 1.4}:d=1.4' if j == n - 1 else ''
        parts.append(f'[1:a]atrim={lo}:{hi},asetpts=PTS-STARTPTS{tail}[s{j}]')
    prev = 's0'
    for j in range(1, n):
        nxt = 'm' if j == n - 1 else f'x{j}'
        parts.append(f'[{prev}][s{j}]acrossfade=d={2 * XF}:c1=tri:c2=tri[{nxt}]')
        prev = nxt
    if n == 1: parts[0] = parts[0].replace('[s0]', '[m]')
    fc = ';'.join(parts)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', silent, '-i', a.music, '-filter_complex', fc,
                    '-map', '0:v', '-map', '[m]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', a.out], check=True)
    pathlib.Path(silent).unlink()
    print('wrote', a.out, f'{TOTAL:.2f}s')


if __name__ == '__main__':
    main()
