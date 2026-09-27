#!/usr/bin/env python3
"""motion/src/ から配信用の HTML(下絵を base64 で内包した単一ファイル)を作る。"""
import base64, pathlib
root = pathlib.Path(__file__).resolve().parent.parent / 'motion'
PAGES = {  # テンプレート: 下絵
    'index.html': 'base.jpg',   # 紅夜
    'moon.html': 'moon.jpg',    # 紅月
    'tide.html': 'tide.jpg',    # 月潮
}
for page, image in PAGES.items():
    html = (root / 'src' / page).read_text(encoding='utf-8')
    b64 = base64.b64encode((root / 'src' / image).read_bytes()).decode()
    assert html.count('__BASE_IMAGE__') == 1, page
    (root / page).write_text(html.replace('__BASE_IMAGE__', 'data:image/jpeg;base64,' + b64), encoding='utf-8')
    print('motion/' + page, (root / page).stat().st_size, 'bytes')
