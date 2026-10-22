#!/usr/bin/env python3
"""フルボイス化のための収録台本を出す。

crc/index.html の全台詞に voiceId を振って一覧にする。
voiceId は本体の JS と同じ計算なので、ここで出した ID のまま
`VOICE_CLIPS` に音声を入れれば、その行だけ本物の声に差し替わる。

    python3 tools/voicelist.py                 # 話数ごとの集計
    python3 tools/voicelist.py --csv script.csv # 収録台本をCSVで書き出す
    python3 tools/voicelist.py --speaker エルザ  # 話者で絞る
    python3 tools/voicelist.py --ep 8           # 話数で絞る

voiceId は「話者 + 本文」から決まる。だから:
  - 行を挿しても既存のIDは動かない(増築は「間に挟む」方式なのでこれが要る)
  - 本文を書き換えるとIDが変わる = 録り直しが必要な行が自動で外れる
"""
import argparse, csv, os, re, sys

HTML = os.path.join(os.path.dirname(__file__), "..", "crc", "index.html")

# 本体の VOICE_KEY と同じ対応。増やしたら両方直すこと
VOICE_KEY = {
    "": "narr", "ユウジ": "yu", "エルザ": "el", "ソメイ": "somei", "咲耶": "sakuya",
    "潮": "ushio", "白仮面": "eleven", "白仮面のひとり": "eleven",
    "《トランジスタ》": "tra", "源三の声": "genzo", "灰色の男": "hai",
    "蔵馬": "kurama", "回収機体": "kikai", "???": "nazo",
}

def voice_id(speaker, text):
    """本体の voiceId() と同じ FNV-1a 32bit。
    JS の charCodeAt は UTF-16 コードユニットを返すので、こちらも合わせる。"""
    sp = VOICE_KEY.get(speaker, "etc")
    src = speaker + "\u0001" + text
    units = src.encode("utf-16-le")
    h = 0x811c9dc5
    for k in range(0, len(units), 2):
        h ^= units[k] | (units[k + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return "%s-%08x" % (sp, h)

def episode_sources(src):
    """各話の配列ソースを切り出す。EP_ORDER の順に (話数キー, 変数名, ソース)。"""
    m = re.search(r"const\s+EPISODES\s*=\s*\{(.*?)\}\s*;", src, re.S)
    if not m:
        sys.exit("EPISODES が見つからない")
    pairs = dict(re.findall(r'"([^"]+)"\s*:\s*(\w+)', m.group(1)))
    order = re.search(r"const\s+EP_ORDER\s*=\s*\[(.*?)\]", src, re.S)
    keys = re.findall(r'"([^"]+)"', order.group(1)) if order else list(pairs)
    out = []
    for k in keys:
        var = pairs.get(k)
        if not var:
            continue
        mm = re.search(r"\bconst\s+" + var + r"\s*=\s*\[", src)
        if not mm:
            continue
        i = mm.end() - 1
        depth = 0
        for j in range(i, len(src)):
            if src[j] == "[":
                depth += 1
            elif src[j] == "]":
                depth -= 1
                if depth == 0:
                    out.append((k, var, src[i:j + 1]))
                    break
    return out

def speaker_names(src):
    """const EL="エルザ" の類を集めて、識別子 -> 表示名 の辞書にする。"""
    names = {}
    for mm in re.finditer(r"\bconst\s+((?:[A-Z][A-Z0-9_]*\s*=\s*\"[^\"]*\"\s*,?\s*)+);", src):
        for ident, val in re.findall(r"([A-Z][A-Z0-9_]*)\s*=\s*\"([^\"]*)\"", mm.group(1)):
            names.setdefault(ident, val)
    return names

def collect(src):
    names = speaker_names(src)
    titles = {}
    mt = re.search(r"const\s+EP_TITLES\s*=\s*\{(.*?)\n\s*\}\s*;", src, re.S)
    if mt:
        for k, a in re.findall(r'"([^"]+)"\s*:\s*\[\s*"([^"]*)"', mt.group(1)):
            titles[k] = a
    rows = []
    for ep, var, body in episode_sources(src):
        for mm in re.finditer(r"\{[^{}]*?\bt\s*:\s*\"((?:[^\"\\]|\\.)*)\"[^{}]*?\}", body):
            chunk = mm.group(0)
            text = mm.group(1)
            ms = re.search(r"\bn\s*:\s*([A-Z][A-Z0-9_]*|\"(?:[^\"\\]|\\.)*\")", chunk)
            if not ms:
                continue                      # n を持たない命令(curtain など)は台詞ではない
            raw = ms.group(1)
            speaker = raw[1:-1] if raw.startswith('"') else names.get(raw, raw)
            text = text.replace('\\"', '"').replace("\\\\", "\\")
            rows.append({
                "ep": ep, "title": titles.get(ep, ""), "speaker": speaker or "(地の文)",
                "voiceId": voice_id(speaker, text), "chars": len(text), "text": text,
            })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="収録台本をこのパスにCSVで書き出す")
    ap.add_argument("--speaker", help="話者で絞る(表示名)")
    ap.add_argument("--ep", help="話数キーで絞る")
    a = ap.parse_args()

    src = open(HTML, encoding="utf-8").read()
    rows = collect(src)
    if a.speaker:
        rows = [r for r in rows if r["speaker"] == a.speaker]
    if a.ep:
        rows = [r for r in rows if r["ep"] == a.ep]

    dup = len(rows) - len({r["voiceId"] for r in rows})

    if a.csv:
        with open(a.csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["ep", "title", "speaker", "voiceId", "chars", "text"])
            w.writeheader()
            w.writerows(rows)
        print("書き出した: %s (%d行)" % (a.csv, len(rows)))

    by_sp = {}
    for r in rows:
        d = by_sp.setdefault(r["speaker"], {"n": 0, "chars": 0})
        d["n"] += 1
        d["chars"] += r["chars"]
    print("\n%-14s %6s %8s %7s" % ("話者", "台詞数", "字数", "平均"))
    print("-" * 40)
    for sp, d in sorted(by_sp.items(), key=lambda x: -x[1]["n"]):
        print("%-14s %6d %8d %7.1f" % (sp, d["n"], d["chars"], d["chars"] / d["n"]))
    print("-" * 40)
    print("%-14s %6d %8d" % ("合計", len(rows), sum(r["chars"] for r in rows)))
    if dup:
        # 同じ話者が同じ台詞を言う行。1つ録れば両方に当たるので、収録数はその分減る
        print("\n同一の台詞(話者も同じ): %d行 → 収録が必要なのは %d種" % (dup, len(rows) - dup))

if __name__ == "__main__":
    main()
