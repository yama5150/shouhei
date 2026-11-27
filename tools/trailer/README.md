# Cyber Rose Crimson トレーラーの作り方

2026-11-27 に作った公式トレーラー(縦 9:16 と横 16:9、約40秒)を、もう一度組み立てるための道具。
LP の `#trailer` に載っているのはこれを Web 向けに縮めたもの(`crc/lp/trailer-9x16.mp4` / `trailer-16x9.mp4`)。

## 中身

| ファイル | 役割 |
|---|---|
| `make_audio.py` | 原曲から使う部分を切り出してつなぎ、拍の表 `plan.json` と `audio.wav` を作る |
| `render.py` | 拍の表に合わせて絵と文字を1コマずつ描き、mp4 にする。**ショット表と文字はこの中** |
| `desk.jpg` | 最後に敷いている机の絵(本編・LPには無い。翔平が 2026-11-27 に渡したもの) |

## 必要なもの

- **原曲**:Suno からダウンロードした「Eruza: Cyber Rose Crimson (Remastered)」(4:49 版)。
  **本編に入っている 56kbps モノラルは使わない**(設定集 第9節「トレーラーには原曲」)。リポジトリには入れていない
- Python の部品:`librosa soundfile pillow fonttools`(作業用の venv に入れる)
- `ffmpeg`

## 手順

```bash
WORK=/どこか/work; mkdir -p $WORK/img $WORK/font
python3 -m venv /tmp/av && /tmp/av/bin/pip -q install librosa soundfile pillow fonttools

# 1. 音声と拍の表(切り方を変えたいときは --survey で曲の形を見てから引数で指定)
/tmp/av/bin/python tools/trailer/make_audio.py 原曲.mp3 $WORK

# 2. 絵(本編から取り出す。--ref は新しい絵が入っているブランチ)
python3 .claude/skills/shouhei-release/scripts/extract_asset.py --ref origin/main \
  imgSea imgSalvage sprN imgKobo2 sdTsun imgMatsuri imgHanabi sprEleven imgUshio imgKishin \
  sprSakuyaKen sprSomei imgBattle imgSeal imgCore imgDaiseido imgAoi imgCity imgRosy --out $WORK/img
cp tools/trailer/desk.jpg $WORK/img/

# 3. フォント(npm から。本文は Shippori Mincho B1、タイトルは Cinzel)
(cd $WORK/font && npm pack -s @expo-google-fonts/shippori-mincho-b1 @expo-google-fonts/cinzel \
  && for f in *.tgz; do tar xzf $f; mv package ${f%.tgz}; rm $f; done)

# 4. 確認用(数秒)→ 本番(縦は約80秒)
/tmp/av/bin/python tools/trailer/render.py $WORK --preview
/tmp/av/bin/python tools/trailer/render.py $WORK
/tmp/av/bin/python tools/trailer/render.py $WORK --landscape

# 5. LP 用に縮める
ffmpeg -i $WORK/trailer_9x16.mp4  -vf scale=720:1280 -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 160k crc/lp/trailer-9x16.mp4
ffmpeg -i $WORK/trailer_16x9.mp4 -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 160k crc/lp/trailer-16x9.mp4
```

LP の表紙(`crc/lp/img/trailer-*.webp`)は、タイトルが出ている 33.0 秒のコマ。

## 今の切り方(曲 123 BPM)

| 映像 | 曲 | |
|---|---|---|
| 0.0s | 174.96s | 間奏で静かになる拍から入る |
| 9.5s | 184.48s | 5小節後、盛り上がりの頭。白く光らせる |
| 34.4s | 209.40s → 284.05s | 13小節使ったところで、曲の終わり方へ 0.12秒重ねてつなぐ |
| 38.3s | 287.88s | 最後の一音 |

**つなぎ目(34.4s)は耳で確かめていない。** 不自然なら `--bars` か `--tail` を小節単位で動かす。

## 決めごと

- 台詞は**本編にある台詞だけ**(最終話の PV で使っているもの)。ネタバレ(「7回目」など)は入れない
- 本編の「──」(罫線 U+2500)は Shippori Mincho に無く文字化けする。トレーラーでは「――」(U+2015)にする
- 横長では、縦長・正方形の絵はぼかした同じ絵を背景に敷き、絵全体を中央に置く(切ると顔しか残らない)
- 文字の後ろには暗い帯を敷く。どの絵の上でも読めるように
