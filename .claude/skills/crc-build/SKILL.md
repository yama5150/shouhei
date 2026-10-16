---
name: crc-build
description: Cyber Rose Crimson (crc/index.html) のビルド・検証・配信の手順と、この作品特有の落とし穴。シナリオの増築、台詞の追加、話数の調整、素材(画像・音楽・動画)の差し替え、MUSIC ROOM やチャプターメニューやタイトル画面の変更、ジャケットの入れ替え、ビルド番号の更新、翔平への配信 ── crc/ 以下に触る作業なら必ず最初に読むこと。「CRC」「クリムゾン」「ビジュアルノベル」「第N話」「エルザ」「ユウジ」「ジャケット」「チャプター」「MUSIC ROOM」が出てきたときも同様。この作品は単一の巨大HTMLで、知らずに触ると壊れる罠が複数ある。verify.cjs と qa.py を通さずに push すると、動かない版が配信URLに乗る。
---

# Cyber Rose Crimson — ビルドと検証

## この作品の形

`crc/index.html` **1ファイルだけ**が本体。約34.5MB。画像58枚・音楽11曲・動画2本が
すべて base64 で `const ASSETS = {…}` に埋まっている。ビルドシステムは無い。
HTMLを直接書き換えて push すると、それがそのまま配信される。

だから壊したときの影響が直接的だ。手順を飛ばさないこと。

## 絶対に守ること

この6つは、過去に破って実際に壊した結果として残っているものだ。

1. **既存の台詞を削らない。** 増築は必ず「間に挟む」。翔平が書いた文はすべて残す
2. **話数の内部キーを変えない。** 表示名だけ変える。
   キーを変えるとセーブデータと PV 判定が壊れる
3. **`state.ep==="8"` が最終話判定。** ここに触るときは `startEd` が PV に分岐する
   経路も一緒に確認する
4. **画像は縦長(スマホ画角)優先。** 横長は上下が切れる
5. **公開ファイル名は `crc/index.html` 固定。** 変えると配信URLが変わり、
   翔平が持っているリンクが全部死ぬ
6. **翔平は iPhone 一台で作業している。** 成果物は「URL」と「HTMLファイル」の
   両方を渡す。どちらか片方だけだと詰まる

## 手順

### 1. 増築の前に方針を見せる

シナリオを増やすときは、本文を書く前にプロットを提示して可否をもらう。
いきなり本文を実装しない。翔平が「わがまま言うと」「恥ずかしいんだが」と
前置きしたことは、たいてい作業の核心になる。そこを拾う。

### 2. ASSETS に何か足すときは行の構造を見る

`ASSETS` は1行が数MBになる。`cat` や `grep` でそのまま開くとコンテキストが
base64 で埋まって作業できなくなる。**必ず base64 をマスクして読む:**

```bash
grep -n "探したいもの" crc/index.html | python3 -I -c "
import sys,re
for l in sys.stdin: print(re.sub(r'\"(data:|SUQz)[^\"]{40,}\"','\"…\"',l).rstrip()[:200])
"
```

挿入位置を決めたら、**アンカー行の末尾にカンマがあるかを assert で確かめてから**
書き込む。SDスプライトは3つで1行・行末カンマ無しの箇所があり、気づかず追記して
構文エラーを出したことがある。

```python
anchor='  imgChapter:"'
i=s.index(anchor); j=s.index("\n", i)
assert s[j-1]==",", "imgChapter 行末にカンマが無い"
```

### 3. ビルド前チェック(3つ全部通す)

```bash
# ① JS構文 ── <script> は3ブロックある。
#    欲張りな正規表現で1つに繋ぐと途中の </script> で必ず SyntaxError になり、
#    正しいビルドを「壊れている」と誤判定する
python3 - <<'EOF'
import io,re
s=io.open('crc/index.html',encoding='utf-8').read()
for i,b in enumerate(re.findall(r'<script>(.*?)</script>',s,re.S)):
    io.open('/tmp/c%d.js'%i,'w',encoding='utf-8').write(b)
    print('block',i,len(b))
EOF
for f in /tmp/c*.js; do node --check "$f" && echo "$f OK"; done

# ② 参照整合 ── bg/spr/bgm/yu/bgv の実在、label↔jump、ifFlag、EP_ORDER三者整合
node tools/verify.cjs crc/index.html

# ③ 通しプレイ ── 実ブラウザで全話を最後まで自動で進める
python3 tools/qa.py            # 全16話
python3 tools/qa.py 8 en3      # 話数指定
python3 tools/qa.py --mem      # renderer の実メモリも出す
```

②と③は役割が違う。`verify.cjs` は「参照が実在するか」、`qa.py` は
「実際に最後まで到達するか」。無限ループや進まない選択肢は ② では原理的に
見つからない。素材を差し替えただけでも ③ まで通す。

### 4. 変更した箇所を実ブラウザで見る

チェックが通っても「意図した見た目になったか」は別問題だ。
Playwright + `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`
(`--no-sandbox` が必要)を 390x844 で開いて、触った画面を実際に確認する。
この Chromium は **H.264 をデコードできない**。動画の確認だけは VP9 に変換して
行い、**本番は iOS Safari 向けに H.264 で出す**。

### 5. 配信

```bash
git push -u origin <branch>          # 失敗時は 2s/4s/8s/16s でリトライ
```

push したら **ローカルとリモートの blob ハッシュが一致することを確認する**:

```bash
git rev-parse HEAD:crc/index.html
git rev-parse origin/<branch>:crc/index.html
```

配信URLは**必ずコミットSHA直指定**にする。ブランチ名のURLは GitHub の raw CDN が
キャッシュを持つので、マージ直後に古い版が返る:

```
https://rawcdn.githack.com/yama5150/shouhei/<40桁のSHA>/crc/index.html
```

この作品は「更新したのに古い版が出る」を**2回**別の原因で踏んでいる
(1回目はファイル名ベースのURL、2回目はCDNキャッシュ)。だから
「ファイルは正しい」で終わらせず、必ず実データで確認する。

## 落とし穴の詳細

`references/traps.md` に、踏んだ罠とその原因を全部書いてある。
**エンジンの挙動が予想と違うとき、自分でデバッグを始める前にまずこれを読む。**
特に以下は知らないと必ず誤診する:

- 終了経路が3つある(`{ed:true}` / `{fin:true}` / 最終話のPV分岐)
- 選択肢は押しても DOM に残る(`display:none` になるだけ)
- `playBgm` は既定でループする(曲が尺切れすると頭から鳴り直す)
- 起動時メモリが +166MB(単一ファイル設計の固定費)

## 正史

設定・人物・話数構成・伏線の対応表・フラグ一覧・改訂履歴は
`reference/settings.md` にある。**シナリオに触る前に必ず読む。**
伏線を増やすときは「伏線 → 回収 対応表」に追記して、回収先を明示する。
