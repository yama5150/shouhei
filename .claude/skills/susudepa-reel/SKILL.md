---
name: susudepa-reel
description: |
  スマホで撮った写真・動画から、ススキノデパート（すすきののバイキング／寿司）の
  SNS 縦型リール（1080x1920 の mp4）とサムネイル、投稿文を組み立てる。
  素材（.mov/.jpg/.mp3）を渡されて「リール作って」「動画にして」「告知の動画」
  「インスタ用に」「ショート作って」などと言われたら必ずこれを使うこと。
  フェアの告知、新メニュー、季節の装飾、リニューアル、日々の仕入れなど
  題材を問わず使える。「こんな感じで」と参考動画やイメージだけ渡された場合、
  既存の素材で作り直す場合、尺やテンポを変えた別バージョンが欲しい場合、
  BGM を差し替える場合、サムネのタイトルだけ作る場合も同じ。
  ffmpeg の落とし穴（音が末尾で切れる、上下逆になる、絵文字で落ちる）を
  踏まないための手順と、店の文言のトーンが入っている。
---

# ススデパのリール制作

素材を受け取って、投稿できる状態まで持っていく。出すのは **本番用 mp4 /
無音版 mp4 / サムネ jpg / 投稿文** の 4 点。

作業は構成ファイル（JSON）を書いて `build_reel.py` に渡すだけ。毎回ゼロから
ffmpeg を組まない。踏みやすい罠は `references/gotchas.md` にまとめてある。

## 手順

### 1. 素材を下見する

```bash
python3 scripts/inspect_sources.py <素材ディレクトリ>
```

ファイルごとに長さ・解像度・回転・平均輝度・音量が出て、動画は秒数つきの
コンタクトシートが保存される。**出てきた jpg は必ず実際に見ること。** どの
クリップのどこが使えるかは、数値では分からない。シートの数字がそのまま
構成ファイルの `start` になる。

ここで次を押さえる。

- 使える瞬間はどこか（手が動いている、料理が映っている、ブレていない）
- 沈んでいる写真はどれか（輝度 100 未満なら `lift` 1.3〜1.45）
- 音が使えるか（-30 LUFS より下ならノイズだけ。混ぜない）
- **素材に混ざってはいけないものが無いか**（他人の SNS 画面、社内 LINE など。
  `references/house-style.md` の最後）

### 2. 曲の使いどころを決める

```bash
python3 scripts/pick_music.py <曲.mp3> <使う秒数>
```

数分の曲から十数秒を切り出すので、どこから使うかで印象が変わる。静かな
ブレイク明け（セクションの頭）から始めると、音が入ってくるところで始まる
ので収まりがいい。「区切り明けの候補」から選ぶ。

### 3. 構成を書く

`references/config.md` の形式で JSON を書く。構成の型と文言のトーンは
`references/house-style.md`。

おおまかには **掴み → 中身 → 締めのカード → ロゴ → 黒**。全体 15〜30 秒、
1 カット 1.4〜2.4 秒。黒を最後に 0.5 秒置くのは、音を引き切るため。

テロップで品名を言い切らない、裏取りできない鮮度を書かない、未確定の
日付と価格を出さない。理由は house-style.md に書いてある。

### 4. 焼く

```bash
# サムネに文字を入れるなら先に（Pillow は /usr/bin/python3 にしか無い）
TITLE_L1="ハロウィンコーデの" TITLE_L2="バイキング" TITLE_EMOJI="⁉🎃🧑‍🍳⁉" \
  /usr/bin/python3 scripts/make_title.py --out <出力先>

python3 scripts/build_reel.py <構成>.json
```

映像は 1 回だけエンコードして、音声だけ差し替えて mux する。テロップも
カットも変えずに音量だけ直すときは `--audio-only`、サムネだけなら
`--cover-only`。

### 5. 見直す

**ここを飛ばさない。** 数値が通っていても絵が破綻していることがある。

```bash
# 1秒おきに並べて目で見る
ffmpeg -i out/xxx.mp4 -vf "fps=1.2,scale=190:-1,\
drawtext=fontfile=/usr/share/fonts/truetype/fonts-japanese-gothic.ttf:\
text='%{pts\:hms}':fontsize=22:fontcolor=yellow:box=1:boxcolor=black:x=3:y=3,\
tile=5x4:padding=3:color=white" -frames:v 1 grid.jpg

# 映像と音声の長さが一致しているか
ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 out/xxx.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 out/xxx.mp4

# 画面の明るさ（110〜160 に揃っているか）
ffmpeg -i out/xxx.mp4 -vf "fps=1,signalstats,metadata=print:file=-" -f null - | grep YAVG
```

コンタクトシートで見るのは、構図のずれ（被写体が切れていないか）、
テロップの被り、暗すぎるカット、カットのつながり。直すのは構成ファイルの
`focus` / `zoom` / `lift` / `dur`。

**音声の長さが映像と違ったら、音の経路に loudnorm が紛れている。**
gotchas.md を読むこと。

### 6. 渡す

mp4 2 本とサムネを送り、投稿文とハッシュタグはチャットに貼る。あわせて
伝えること。

- 何秒か、どういう流れか
- 判断したこと（曲のどこを使ったか、なぜその構図か、何を外したか）
- **音は聴けていない**こと。レベルとフェードの形は確認済みでも、気持ちよさは
  本人に聴いてもらう必要がある
- 素材から外したものがあれば、外したことと理由

## よくある追加注文

| 言われること | やること |
|---|---|
| もっとテンポ速く | 構成ファイルをもう 1 つ作る。1 カット 0.9〜1.3 秒、`caption_bottom` を 1100、`chip` を `@0.00` にして `caption_border: 8`。カットが短くなるぶん、同じクリップの別の場面を足して絵の種類を保つ。実測の根拠は house-style.md の「速い版」 |
| 色が暗い | 出来上がりの輝度を測ってから、沈んでいるカットの `lift` を上げる。全体を一律に上げない |
| BGM 変えて | `pick_music.py` で使いどころを出し直して `music.file` と `start` を差し替え、`--audio-only` で焼き直す |
| 素材追加して | `sources` に足して `segments` に差し込む。尺が伸びるぶん、既存のカットを 0.2 秒ずつ詰めて相殺する |
| サムネのタイトル変えて | `make_title.py` の環境変数を変えて `--cover-only` |
| テロップをド派手に | 構成ファイルに `font: "maru"` ＋ 太い `caption_border` ＋ アクセント色を足す。文は「小さい白／大きいアクセント色の名詞 1 語」の 2 行で組む。全項目は config.md の「ド派手なテロップ」 |
| 日付が決まった | 締めのカードと投稿文の両方を直す。片方だけだとズレる |

## 参考動画を渡されたら

TikTok / Instagram のリンクは**この環境のネットワークポリシーで開けない**
ことが多い。見られないなら素直にそう言って、動画ファイルかスクショを
もらう。mp4 があればカットの秒数・テロップの位置・音ハメを実測して写せる。

もらえないまま進めるなら、推測で作ったことを明示して、いまの版と並べて
出す。選んでもらうほうが早い。

## 参照

- `references/gotchas.md` — ffmpeg の落とし穴。**音が末尾で切れる、上下が
  逆になる、絵文字で落ちる**といった症状に当たったら必ず読む
- `references/config.md` — 構成ファイルの全項目
- `references/house-style.md` — 構成の型、文言のトーン、言わないこと、
  サムネ、投稿文、素材として使わないもの

## 必要なもの

```bash
apt-get install -y ffmpeg fonts-noto-cjk fonts-motoya-l-maruberi
```

Pillow（サムネのタイトル用）。この環境では `/usr/bin/python3` にだけ入って
いるので、`make_title.py` はフルパスで実行する。
