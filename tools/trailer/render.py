"""Cyber Rose Crimson トレーラーを1コマずつ描いて ffmpeg に流す。手順は同じフォルダの README.md。

    python render.py WORK              # 縦 1080x1920 / 30fps → WORK/trailer_9x16.mp4
    python render.py WORK --landscape  # 横 1920x1080        → WORK/trailer_16x9.mp4
    python render.py WORK --preview    # 1/3 解像度・15fps で速く確認

WORK には make_audio.py が作った plan.json と audio.wav、img/(絵)、font/(フォント)を置く。
ショット表(どの絵を何拍目から出すか)と文字は、この下の「ショット表」「文字」を直す。
"""
import json, math, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
    sys.exit(__doc__)
D = os.path.abspath(sys.argv[1])
IMG = os.path.join(D, "img")
FONT_JP = os.path.join(D, "font/expo-google-fonts-shippori-mincho-b1-0.4.1/600SemiBold/ShipporiMinchoB1_600SemiBold.ttf")
FONT_EN = os.path.join(D, "font/expo-google-fonts-cinzel-0.4.2/600SemiBold/Cinzel_600SemiBold.ttf")

args = sys.argv[2:]
PREVIEW = "--preview" in args
W, H = (1080, 1920)
if "--landscape" in args: W, H = 1920, 1080
SC = 1 / 3 if PREVIEW else 1
W, H = int(W * SC), int(H * SC)
FPS = 15 if PREVIEW else 30
OUT = os.path.join(D, ("preview" if PREVIEW else "trailer") + ("_16x9" if "--landscape" in args else "_9x16") + ".mp4")

plan = json.load(open(os.path.join(D, "plan.json")))
vb = plan["vbeats"]
TOTAL = round(plan["total"] - .15, 2)   # 最後の数コマは無音なので少し手前で終える
b = lambda i: vb[i]
BODY_END = b(72)

# ---------------- ショット表 ----------------
# (画像, 開始, 終了, 動き, 焦点x, 焦点y)  動き: in=寄る / out=引く / pan=横に流す / still
shots = []
def S(img, t0, t1, mv="in", fx=.5, fy=.45, amt=.12):
    shots.append(dict(img=img, t0=t0, t1=t1, mv=mv, fx=fx, fy=fy, amt=amt))

S("imgSea.jpg", 0, b(8), "pan", .5, .5, .10)
S("imgSalvage.jpg", b(8), b(20), "in", .5, .38, .14)
S("sprN.jpg", b(20), b(28), "out", .5, .3, .16)
for k, im in enumerate(["imgKobo2.jpg", "sdTsun.jpg", "imgMatsuri.jpg", "imgHanabi.jpg"]):
    S(im, b(28 + 2 * k), b(30 + 2 * k), "in", .5, .45, .08)
for k, im in enumerate(["sprEleven.jpg", "imgUshio.jpg", "imgKishin.jpg", "sprSakuyaKen.jpg", "sprSomei.jpg", "imgBattle.jpg"]):
    S(im, b(36 + 2 * k), b(38 + 2 * k), "in" if k % 2 == 0 else "out", .5, .38, .10)
for k, im in enumerate(["imgSeal.jpg", "imgCore.jpg", "imgDaiseido.jpg", "imgAoi.jpg"]):
    S(im, b(48 + k), b(49 + k), "in", .5, .45, .06)
S("imgCity.jpg", b(52), b(60), "in", .5, .55, .10)
S("imgRosy.jpg", b(60), BODY_END, "out", .5, .42, .14)
S("desk.jpg", BODY_END, TOTAL, "in", .45, .55, .06)

# ショットの切れ目でのクロスフェード(秒)。静かな前半だけ柔らかく、盛り上がり以降は拍でカット
XF = {b(8): .8, BODY_END: .7}

# ---------------- 文字 ----------------
texts = []
def T(lines, t0, t1, y=.78, size=54, font=FONT_JP, glow=True, track=.12, fade=.45):
    texts.append(dict(lines=lines, t0=t0, t1=t1, y=y, size=size, font=font, glow=glow, track=track, fade=fade))

T(["深度470。"], .9, b(8) - .2, y=.5, size=66, track=.4)
T(["電脳の海の底から引き揚げた、", "一輪の薔薇。"], b(9) + .2, b(20) - .25, y=.80, size=54)
T(["「……随分と、", "小さいのが来たのね」"], b(21), b(28) - .1, y=.80, size=58, fade=.3)
T(["「私の修理、あなたがやるのよ」"], b(28) + .15, b(36) - .1, y=.84, size=54, fade=.25)
T(["「――続けるよ。何回でも」"], b(53), b(60) - .1, y=.80, size=58, fade=.3)
T(["CYBER ROSE", "CRIMSON"], b(64), BODY_END + .2, y=.47, size=112, font=FONT_EN, track=.10, fade=.25)
T(["薔薇は、愛か、呪いか。"], b(66), BODY_END + .2, y=.64, size=56, track=.25, fade=.4)
T(["全16話 × 12曲"], BODY_END + .5, TOTAL, y=.42, size=50, track=.3)
T(["iPhoneひとつで、遊べる。"], BODY_END + .9, TOTAL, y=.50, size=60, track=.18)
T(["shouhei.vercel.app"], BODY_END + 1.5, TOTAL, y=.60, size=46, track=.06)

# 白い閃光:盛り上がりの頭、タイトル
FLASH = [(b(20), .55, .9), (b(64), .45, .7)] + [(b(36 + 2 * k), .18, .25) for k in range(6)] + [(b(48 + k), .12, .2) for k in range(4)]

# ---------------- 下ごしらえ ----------------
def cover(im, w, h, scale):
    r = max(w / im.width, h / im.height) * scale
    return im.resize((max(w, int(im.width * r)), max(h, int(im.height * r))), Image.LANCZOS)

cache = {}
FIT = {}   # 横長の画面に縦長・正方形の絵を出すとき: ぼかした同じ絵を背景に、絵全体を中央に置く
LAND = W > H
for s in shots:
    if s["img"] in cache: continue
    im = Image.open(os.path.join(IMG, s["img"])).convert("RGB")
    cache[s["img"]] = cover(im, W, H, 1 + s["amt"] + .02)
    if LAND and im.width / im.height < 1.3:
        bg = cover(im, W, H, 1.0)
        bx, by = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((bx, by, bx + W, by + H)).filter(ImageFilter.GaussianBlur(int(40 * SC)))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (6, 2, 12)), .45)
        FIT[s["img"]] = (bg, im)

def frame_of(s, t):
    big = cache[s["img"]]
    p = min(1, max(0, (t - s["t0"]) / max(.001, s["t1"] - s["t0"])))
    e = p * p * (3 - 2 * p)                      # なめらかに
    a = s["amt"]
    z = {"in": 1 + a * e, "out": 1 + a * (1 - e), "pan": 1 + a * .5, "still": 1}[s["mv"]]
    if s["img"] in FIT:
        bg, im = FIT[s["img"]]
        fh = int(H * .94 * (1 + (z - 1) * .6))
        fw = int(im.width * fh / im.height)
        fg = im.resize((fw, fh), Image.BILINEAR)
        fr = bg.copy()
        fr.paste(fg, ((W - fw) // 2, (H - fh) // 2 + int(H * .02)))
        return fr
    # big は「画面を (1+a+.02) 倍で覆う大きさ」。z 倍に寄る = 切り出す窓を 1/z にする
    base_w = big.width / (1 + a + .02)
    base_h = base_w * H / W
    if base_h > big.height / (1 + a + .02):
        base_h = big.height / (1 + a + .02); base_w = base_h * W / H
    ww, hh = base_w * (1 + a + .02) / z, base_h * (1 + a + .02) / z
    ww, hh = min(ww, big.width), min(hh, big.height)
    if s["mv"] == "pan":
        cx = (big.width - ww) * (.15 + .7 * e) + ww / 2
    else:
        cx = s["fx"] * big.width
    cy = s["fy"] * big.height
    x0 = min(max(0, cx - ww / 2), big.width - ww)
    y0 = min(max(0, cy - hh / 2), big.height - hh)
    return big.crop((int(x0), int(y0), int(x0 + ww), int(y0 + hh))).resize((W, H), Image.BILINEAR)

# 周辺減光
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig)
for i in range(40):
    r = i / 40
    vd.ellipse((-W * .35 + W * .35 * r, -H * .25 + H * .25 * r, W * 1.35 - W * .35 * r, H * 1.25 - H * .25 * r), fill=int(170 * (1 - r) ** 2))
vig = vig.filter(ImageFilter.GaussianBlur(W / 10))
black = Image.new("RGB", (W, H), (6, 2, 12))

def text_layer(tx):
    f = ImageFont.truetype(tx["font"], int(tx["size"] * SC))
    lh = int(tx["size"] * SC * 1.55)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    n = len(tx["lines"])
    y = int(H * tx["y"] - lh * n / 2)
    for line in tx["lines"]:
        tr = tx["size"] * SC * tx["track"]
        widths = [d.textlength(c, font=f) for c in line]
        tw = sum(widths) + tr * (len(line) - 1)
        if tw > W * .9:  # はみ出すなら字間を詰める
            tr = max(0, (W * .9 - sum(widths)) / max(1, len(line) - 1))
            tw = sum(widths) + tr * (len(line) - 1)
        x = (W - tw) / 2
        for c, cw in zip(line, widths):
            d.text((x, y), c, font=f, fill=(246, 238, 250, 255))
            x += cw + tr
        y += lh
    # 読みやすさ: 文字の後ろにぼかした暗い帯を敷く
    bb = layer.getbbox()
    if bb:
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pad_x, pad_y = int(90 * SC), int(46 * SC)
        ImageDraw.Draw(band).rounded_rectangle((bb[0] - pad_x, bb[1] - pad_y, bb[2] + pad_x, bb[3] + pad_y),
                                                radius=int(60 * SC), fill=(6, 2, 12, 150))
        band = band.filter(ImageFilter.GaussianBlur(int(36 * SC)))
    if tx["glow"]:
        g = layer.split()[3].filter(ImageFilter.GaussianBlur(max(2, int(10 * SC))))
        glow = Image.new("RGBA", (W, H), (232, 55, 95, 0)); glow.putalpha(g.point(lambda v: int(v * .85)))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(layer.split()[3].filter(ImageFilter.GaussianBlur(max(1, int(4 * SC)))).point(lambda v: int(v * .9)))
        out = Image.alpha_composite(sh, glow); out = Image.alpha_composite(out, layer)
        return Image.alpha_composite(band, out) if bb else out
    return Image.alpha_composite(band, layer) if bb else layer

tl = [text_layer(t) for t in texts]

def shot_at(t):
    for i, s in enumerate(shots):
        if s["t0"] <= t < s["t1"]: return i
    return len(shots) - 1

# ---------------- 書き出し ----------------
nframes = int(TOTAL * FPS)
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", os.path.join(D, "audio.wav"), "-c:v", "libx264", "-preset", "medium" if not PREVIEW else "veryfast",
       "-crf", "18" if not PREVIEW else "26", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "256k",
       "-movflags", "+faststart", "-shortest", OUT]
ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(nframes):
    t = n / FPS
    i = shot_at(t); s = shots[i]
    fr = frame_of(s, t)
    # 前のショットからのクロスフェード
    xf = XF.get(s["t0"])
    if xf and i > 0 and t < s["t0"] + xf:
        fr = Image.blend(frame_of(shots[i - 1], t), fr, (t - s["t0"]) / xf)
    # 色: 少し落として紅を足す
    fr = ImageEnhance.Contrast(fr).enhance(1.06)
    if s["img"] == "desk.jpg":
        fr = Image.blend(fr, black, .38)
    fr = Image.composite(black, fr, vig)
    # 冒頭の暗転明け・最後の暗転
    if t < .8: fr = Image.blend(black, fr, t / .8)
    if t > TOTAL - 1.2: fr = Image.blend(fr, black, min(1, (t - (TOTAL - 1.2)) / 1.0))
    # 閃光
    for ft, strength, dur in FLASH:
        if ft <= t < ft + dur:
            fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 236, 242)), strength * (1 - (t - ft) / dur) ** 2)
    fr = fr.convert("RGBA")
    for tx, layer in zip(texts, tl):
        if tx["t0"] <= t < tx["t1"]:
            a = min(1, (t - tx["t0"]) / tx["fade"], (tx["t1"] - t) / tx["fade"])
            if a <= 0: continue
            if a < 1:
                l2 = layer.copy(); l2.putalpha(layer.split()[3].point(lambda v, a=a: int(v * a))); fr = Image.alpha_composite(fr, l2)
            else:
                fr = Image.alpha_composite(fr, layer)
    ff.stdin.write(fr.convert("RGB").tobytes())
    if n % (FPS * 5) == 0: print(f"{t:5.1f}s", flush=True)
ff.stdin.close(); ff.wait()
print("wrote", OUT)
