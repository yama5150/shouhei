#!/usr/bin/env python3
"""Instagram リール用のカバー画像(1080x1920)を作る。

リールのカバーは 9:16 だが、プロフィールのグリッドでは中央の 3:4(1080x1440、上下 240px ずつ
切れる)しか見えない。顔とタイトルはその範囲に収める。

使い方:
  python3 tools/build-thumbs.py --stills <eden.png のあるディレクトリ> --fonts <フォントのディレクトリ>
出力: motion/thumbs/reel-cover-*.jpg と、グリッドでの見え方の確認用 motion/thumbs/grid-preview.jpg
"""
import argparse, importlib.util, pathlib
import numpy as np
from PIL import Image, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = 1080, 1920
SAFE = (240, 1680)          # グリッドで見える縦の範囲

# 文字の描き方はトレーラーと同じものを使う
_spec = importlib.util.spec_from_file_location('bt', ROOT / 'tools' / 'build-trailer.py')
bt = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(bt)


def cover(img, cx, cy, hs):
    """img から 9:16 を切り出す。cx, cy は中心(0..1)、hs は高さの割合"""
    sw, sh = img.size
    ch = sh * hs; cw = ch * W / H
    if cw > sw: cw = sw; ch = cw * H / W
    x0 = min(max(cx * sw - cw / 2, 0), sw - cw)
    y0 = min(max(cy * sh - ch / 2, 0), sh - ch)
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def paste(fr, layer, cx, cy):
    h, w = layer.shape[:2]
    x0, y0 = int(cx * W - w / 2), int(cy - h / 2)
    xs, ys = max(0, -x0), max(0, -y0)
    xe, ye = min(w, W - x0), min(h, H - y0)
    sub = fr[y0 + ys:y0 + ye, x0 + xs:x0 + xe]
    L = layer[ys:ye, xs:xe]
    al = L[..., 3:4] / 255
    sub[:] = sub * (1 - al) + L[..., :3] * al


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stills', required=True)
    ap.add_argument('--fonts', required=True)
    a = ap.parse_args()
    fd = pathlib.Path(a.fonts)
    MED, BOLD, CZ = fd / 'ShipporiMincho-Medium.ttf', fd / 'ShipporiMincho-Bold.ttf', fd / 'Cinzel[wght].ttf'
    out = ROOT / 'motion' / 'thumbs'; out.mkdir(parents=True, exist_ok=True)

    t1 = bt.text_layer('CYBER ROSE', 112, CZ, spacing=12)
    t2 = bt.text_layer('CRIMSON', 156, CZ, glow=(230, 10, 50), spacing=20)
    hook = bt.text_layer('薔薇は、愛か、呪いか。', 64, BOLD, spacing=4)
    sub = bt.text_layer('全12話＋α のノベル × アルバム', 40, MED, spacing=2)
    tag = bt.text_layer('OFFICIAL TRAILER', 38, CZ, glow=(230, 10, 50), spacing=10)

    src = {
        # 名前: (画像, 中心x, 中心y, 高さの割合)
        'eden': (Image.open(pathlib.Path(a.stills) / 'eden.png'), .44, .5, 1.0),
        'koya': (Image.open(ROOT / 'motion' / 'src' / 'base.jpg'), .5, .5, 1.0),
        'tide': (Image.open(ROOT / 'motion' / 'src' / 'tide.jpg'), .5, .5, 1.0),
    }
    yy = np.linspace(0, 1, H)[:, None, None]
    # 下半分を沈めて文字を読ませる。上は少しだけ
    shade = (1 - .80 * np.clip((yy - .52) / .25, 0, 1)) * (1 - .25 * np.clip((.22 - yy) / .22, 0, 1))
    xx = np.linspace(-1, 1, W)[None, :, None]
    vign = 1 - .25 * xx ** 2

    tiles = []
    for name, (img, cx, cy, hs) in src.items():
        fr = np.asarray(cover(img.convert('RGB'), cx, cy, hs)).astype(np.float32)
        fr *= shade * vign
        paste(fr, tag, .5, 1040)
        paste(fr, t1, .5, 1150)
        paste(fr, t2, .5, 1290)
        paste(fr, hook, .5, 1450)
        paste(fr, sub, .5, 1560)
        im = Image.fromarray(fr.clip(0, 255).astype(np.uint8))
        p = out / f'reel-cover-{name}.jpg'
        im.save(p, quality=92)
        tiles.append(im.crop((0, SAFE[0], W, SAFE[1])))
        print('wrote', p.relative_to(ROOT))

    # プロフィールのグリッドでの見え方(3:4 で切れる)
    tw = 360; th = int(tw * 4 / 3)
    g = Image.new('RGB', (tw * 3 + 8, th), (0, 0, 0))
    for i, t in enumerate(tiles): g.paste(t.resize((tw, th), Image.LANCZOS), (i * (tw + 4), 0))
    g.save(out / 'grid-preview.jpg', quality=85)


if __name__ == '__main__':
    main()
