#!/usr/bin/env python3
"""motion/src/ から配信用の motion/index.html(下絵を base64 で内包した単一ファイル)を作る。"""
import base64, pathlib
root = pathlib.Path(__file__).resolve().parent.parent / 'motion'
html = (root / 'src' / 'index.html').read_text(encoding='utf-8')
b64 = base64.b64encode((root / 'src' / 'base.jpg').read_bytes()).decode()
assert html.count('__BASE_IMAGE__') == 1
(root / 'index.html').write_text(html.replace('__BASE_IMAGE__', 'data:image/jpeg;base64,' + b64), encoding='utf-8')
print('motion/index.html', (root / 'index.html').stat().st_size, 'bytes')
