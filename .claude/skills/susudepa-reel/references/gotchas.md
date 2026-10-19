# ffmpeg まわりの落とし穴

リール 3 本を作る過程で実際に踏んだもの。どれも「出力はできるのに結果が
おかしい」たちの悪い種類なので、知らないと原因にたどり着くのに時間がかかる。

## 音

### loudnorm を書き出しに通さない

いちばん高くついた。`loudnorm` は測定にだけ使い、出力の経路には入れない。

**何が起きたか（2 回）**

1. 狙った値に寄せられないと動的モードに落ち、音が暴れる。環境音版で
   真ピークが **+6.6 dBFS** まで振れた。
2. 動的モードは先読みに 3 秒使う。`amix` と組み合わせたとき、**末尾 3 秒が
   丸ごと落ちた**。映像 31.7 秒に対して音声 28.8 秒。フェードアウトごと
   消えていて、尺を測るまで気づかなかった。

**代わりにどうするか**

各系統を一度測り、静的ゲイン（`volume`）で揃えてから混ぜる。はみ出す瞬間
だけ `alimiter` で止める。測定は `loudnorm=print_format=json` を `-f null`
で流して JSON を読む。これなら結果が読めるし、長さも変わらない。

書き出したら**映像と音声の長さが一致しているか必ず確認する**。

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 out.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 out.mp4
```

### alimiter は既定で音を大きくする

`alimiter` の `level` は既定 true で、出力を上限まで持ち上げる。頭打ちに
だけ使いたいなら `level=disabled` を付ける。付け忘れると、リミッターを
足したのに音が大きくなって真ピークが上がる。

### 使えない音は混ぜない

クリップの音が **-30 LUFS より下**なら、それはノイズフロアだけで中身が無い。
目標の -16 LUFS に揃えようとすると 15〜20dB 持ち上げることになり、ヒスを
増幅するだけになる。そういう素材は音を捨てて、曲だけにするか無音にする。

判断は測ってから。`ffmpeg -i x.mov -map 0:a:0 -af ebur128 -f null -`

### フェードアウトは尺に対して決める

短い動画に `qsin` の緩いカーブを使うと、最後の 1 秒で急に落ちる感じになる。
15 秒前後なら直線（`tri`）のほうが「引き始めた」のが分かる。30 秒あるなら
`qsin` のほうが終わり際が自然。

音を引き切るために、**ロゴの後ろに 0.4〜0.6 秒の黒**を置く。これが無いと
ロゴの終わりで曲がぶつっと切れる。

## 映像

### 回転メタデータは二重に当てない

iPhone の `.mov` は回転メタデータ付き、`.jpg` は EXIF Orientation 付き。
**どちらも ffmpeg が自動で当てる。** よかれと思って `transpose` を足すと
二重回転になり、上下逆さまになる。

確認は、小さく書き出して実際に目で見るのが早い。
`ffmpeg -i x.jpg -vf scale=200:-1 -frames:v 1 check.jpg`

### crop に eval=frame は無い（ffmpeg 6.x）

時間で変わる切り出しをやろうとして `crop=w='...t...':eval=frame` と書くと
`Option not found` で落ちる。6.x の crop は w/h を初期化時にしか評価しない。
ゆっくりズームは `zoompan` でやる。

`zoompan` は座標を整数に丸めるので、等倍のまま使うとカクつく。**2 倍解像度の
台紙に載せてから寄って、最後に縮める**と滑らかになる。

### 先頭フレームを黒くしない

頭にフェードインを入れると 1 フレーム目が真っ黒になる。投稿先がそこを
ポスター画像として拾うと、一覧に黒い絵が出る。リールは `fade_in=0` にして、
1 フレーム目から絵が出るようにする。

確認はこれで（1 枚目が 20 以下なら黒）。

```bash
ffmpeg -i out.mp4 -vf "select='lt(n,3)',signalstats,metadata=print:file=-" \
  -vsync 0 -f null - | grep YAVG
```

### 小さい素材・比率の違う素材は切らずに埋める

480x640 の素材を 9:16 に切ると横が 25% 落ちるうえ 3 倍に伸ばすことになる。
幅だけ合わせれば 2.25 倍で済み、中身も切れない。余白は同じ絵をぼかして
埋める（`fit: "blur"`）。4:3 の写真で被写体が端まである場合も同じ。

## 文字

### drawtext はカラー絵文字を描けない

`NotoColorEmoji` を `drawtext` に渡すと `Monocromatic (1bpp) fonts are not
supported` と言って**落ちる**（segfault することもある）。

絵文字を使うなら Pillow で透過 PNG に描いて、ffmpeg では `overlay` で
重ねる。縁取り・影・傾きも Pillow のほうが自由が利くので、おどけた見出しは
まとめてそちらで作ったほうがいい（`scripts/make_title.py`）。

### NotoColorEmoji は 109px にしか開けない

ビットマップフォントなので、その寸法でしか読み込めない。`ImageFont.truetype`
に他のサイズを渡すと `invalid pixel size`。原寸で描いてから縮める。
`draw.text(..., embedded_color=True)` を忘れると色が出ない。

ZWJ の組み合わせ（🧑‍🍳 など）は Pillow が Raqm 付きなら正しく 1 文字に
なる。`PIL.features.check("raqm")` で確認できる。

### Pillow が入っている python を間違えない

この環境では `python3` が 3.11、Pillow が入っているのは `/usr/bin/python3`
（3.13）。`make_title.py` はフルパスで実行する。

### テロップは textfile で渡す

日本語を filter_complex に直接書くと `:` や `'` のエスケープで事故る。
ファイルに書いて `textfile=` で渡せば何も考えなくていい。

## 投稿先

### Instagram はカバーの中央 1:1 しか一覧に出さない

プロフィールのグリッドはカバー画像の中央を正方形に切る。1080x1920 なら
**y=420〜1500** がその範囲。タイトルも主役もここに収める。外に置いたものは
一覧では見えない。

### テロップは下端 1410 くらいまで

リール再生時、画面下部はキャプションやボタンに隠れる。下端 1410 あたりに
揃えておくと被らない。文字を大きくする速いテンポ版では 1270 くらいまで
上げる。

## 作業の進め方

### 映像は 1 回だけエンコードする

音違いを何本も出すとき、そのたびに映像を焼き直すと時間がかかる。映像を
一度 `video.mp4` に書き出して、音声だけ差し替えて `-c copy` で mux する。
構成を変えていないなら `--audio-only` で映像の焼き直しを飛ばせる。

### 出来上がりは必ずコンタクトシートで見る

数値だけ見て「できた」と言わない。1 秒おきに並べた 1 枚絵にして、実際に
目で確認する。構図のずれ、テロップの被り、暗すぎるカットはこれで分かる。

```bash
ffmpeg -i out.mp4 -vf "fps=1.2,scale=190:-1,\
drawtext=fontfile=/usr/share/fonts/truetype/fonts-japanese-gothic.ttf:\
text='%{pts\:hms}':fontsize=22:fontcolor=yellow:box=1:boxcolor=black:x=3:y=3,\
tile=5x4:padding=3:color=white" -frames:v 1 grid.jpg
```
