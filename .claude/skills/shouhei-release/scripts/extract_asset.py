#!/usr/bin/env python3
"""crc/index.html の ASSETS から、指定したキーの画像・音・動画をファイルに書き出す。

使い方:
  python3 extract_asset.py sprSomei imgMatsuri --out /tmp/x
  python3 extract_asset.py --ref origin/claude/elegant-dijkstra-w9yj7t sprSomei --out /tmp/x
  python3 extract_asset.py --list                    # キーの一覧だけ出す

--ref を付けると、そのブランチ(コミット)の crc/index.html から取り出す。
ASSETS は1行が数MBあるので、grep や cat で直接開かないこと。
"""
import argparse, base64, os, re, subprocess, sys

EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "video/mp4": "mp4"}

def load(ref):
    if ref:
        return subprocess.run(["git", "show", f"{ref}:crc/index.html"],
                              check=True, capture_output=True).stdout.decode("utf-8")
    with open("crc/index.html", encoding="utf-8") as f:
        return f.read()

def assets(src):
    # 画像・動画は data URI、音は data: 無しの生 base64(SUQz… = ID3 で始まる MP3)
    pat = re.compile(r'\b(\w+)\s*:\s*"((?:data:[^;"]+;base64,)?)([A-Za-z0-9+/=]{2000,})"')
    for m in pat.finditer(src):
        key, pre, b64 = m.groups()
        mime = pre[5:-8] if pre else "audio/mpeg"
        yield key, mime, b64

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--ref")
    ap.add_argument("--out", default=".")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    found = {k: (mime, b) for k, mime, b in assets(load(a.ref))}
    if a.list or not a.keys:
        for k, (mime, b) in found.items():
            print(f"{k:16} {mime:12} {len(b) * 3 // 4 // 1024:>6} KB")
        return
    os.makedirs(a.out, exist_ok=True)
    missing = [k for k in a.keys if k not in found]
    if missing:
        sys.exit("見つからないキー: " + ", ".join(missing))
    for k in a.keys:
        mime, b = found[k]
        path = os.path.join(a.out, f"{k}.{EXT.get(mime, 'mp3')}")
        with open(path, "wb") as f:
            f.write(base64.b64decode(b))
        print(path)

if __name__ == "__main__":
    main()
