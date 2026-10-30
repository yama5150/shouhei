# 構成ファイルの書き方

`build_reel.py` に渡す JSON。素材のパスは `src` からの相対で書く。

## 最小の例

```json
{
  "name": "halloween",
  "src": "/root/.claude/uploads/xxxx",
  "out": "out",
  "sources": {
    "pumpkin": "IMG_1234.jpg",
    "corner": "IMG_1235.mov",
    "logo": "logo_sting.mp4"
  },
  "music": { "file": "bgm.mp3", "start": 37, "use_clip_audio": false },
  "segments": [
    { "src": "pumpkin", "kind": "photo", "dur": 1.8,
      "zoom": [1.06, 1.16], "focus": [0.5, 0.45], "lift": 1.2,
      "lines": [["ハロウィン、やってます。", 62, "ink"]] },
    { "src": "corner", "kind": "video", "start": 3.4, "dur": 2.0,
      "zoom": 1.15, "focus": [0.5, 0.5],
      "lines": [["焼き野菜も、充実。", 64, "ink"]] },
    { "src": "pumpkin", "kind": "card", "dur": 2.4,
      "lines": [["ススデパの ハロウィン", 54, "ink"],
                ["開催中", 84, "accent"],
                ["詳しくはプロフィールから", 44, "ink"]] },
    { "src": "logo", "kind": "video", "start": 0, "dur": 2.0, "plain": true },
    { "kind": "black", "dur": 0.5 }
  ],
  "cover": { "base": "pumpkin", "lift": 1.2, "title_y": 470 }
}
```

## カット（segments）

| 項目 | 意味 |
|---|---|
| `src` | `sources` のキー。`black` のときは不要 |
| `kind` | `photo` / `video` / `card` / `black` |
| `start` | 動画のどこから使うか（秒）。`inspect_sources.py` のコンタクトシートの数字をそのまま書ける |
| `dur` | 何秒使うか |
| `zoom` | 写真は `[開始, 終了]` でゆっくり寄る／引く。動画は固定倍率の数値 |
| `focus` | どこに寄るか `[横, 縦]`。0.0=左/上、0.5=中央、1.0=右/下 |
| `lift` | 暗いカットを持ち上げるガンマ。1.0 で無調整 |
| `fit` | `"blur"` で素材を切らずに全部見せ、余白を同じ絵のぼかしで埋める |
| `plain` | `true` でロゴなど完成済みの素材をそのまま出す（色調整もテロップも足さない） |
| `lines` | `[[文字列, 文字サイズ, 色], ...]` を下から積む。色は `ink` / `accent` / 任意の ffmpeg 色 |

`card` は地の写真を大きくぼかして暗く落とし、文字だけ載せる。告知の締めに使う。

### focus の決め方

`zoom` と `focus` は組み合わせで効く。寄るほど見える範囲が狭くなるので、
被写体が端にあるときは `focus` を大きく振らないと切れる。1 フレームだけ
試し焼きして見るのが早い。

```bash
ffmpeg -y -i 素材.jpg -vf "scale=2160:3840:force_original_aspect_ratio=increase,\
crop=2160:3840:(iw-ow)*0.26:(ih-oh)*0.08,crop=w=1741:h=3096:x='(in_w-out_w)*0.26':\
y='(in_h-out_h)*0.08',scale=1080:1920,scale=200:-1" -frames:v 1 試し.jpg
```

## 音（music）

| 項目 | 既定 | 意味 |
|---|---|---|
| `file` | — | 音源。無ければ曲なしで作る |
| `start` | 0 | 曲のどこから使うか。`pick_music.py` で決める |
| `lufs` | -18 | 曲の音量 |
| `use_clip_audio` | true | クリップの環境音を混ぜるか |
| `clip_lufs` | -22 | 混ぜる場合の環境音の音量（曲の 4dB 下） |

クリップの音が -30 LUFS より下ならノイズしか入っていないので
`use_clip_audio: false` にする。包丁や貝の音のように聴かせたい音が入って
いるときだけ true。もっと立たせたいなら `clip_lufs` を -20 まで上げる。

## 全体の設定（省略可）

| 項目 | 既定 | 意味 |
|---|---|---|
| `size` | `[1080, 1920]` | 書き出しサイズ |
| `fps` | 30 | |
| `crf` | 20 | 小さいほど高画質・大容量 |
| `target_lufs` | -16 | 書き出しの音量 |
| `caption_bottom` | 1410 | テロップの下端。文字を大きくするなら 1270 くらいまで上げる |
| `line_step` | 118 | 行送り |
| `chip` | `0x101010@0.60` | テロップの下地。濃くするなら @0.70、外すなら @0.00 |
| `caption_border` | 0 | 下地を薄くする／外すときの縁取りの太さ（px）。8 くらい |
| `caption_border_color` | `black@0.85` | 縁の色 |
| `accent` | `0xF0C071` | アクセント色 |
| `fade_in` | 0 | 0 のまま。入れると 1 フレーム目が黒くなる |
| `fade_out` | 0.20 | |
| `audio_tail` | 3.5 | 音のフェードアウトの長さ |
| `audio_curve` | `tri` | 短い動画は直線、30秒級は `qsin` |
| `basename` | `name` | 出力ファイル名の頭 |

## サムネ（cover）

| 項目 | 意味 |
|---|---|
| `base` | 地に使う素材のキー |
| `lift` | 地の明るさ |
| `title_y` | タイトル PNG を置く y 座標。既定 470 |
| `title` | タイトル PNG のファイル名。既定 `title.png` |
| `file` | 出力名。既定 `<name>_cover.jpg` |

タイトル PNG が無ければ、地の写真だけのサムネになる。文字を入れるなら
先に `make_title.py` を流す。

## 出力

```
out/
├── <basename>.mp4          本番用
├── <basename>_muted.mp4    無音版（アプリで曲を乗せる場合）
├── <basename>_cover.jpg    サムネ
└── _<name>/                中間ファイル。消してよい
```

## テンポ違いを作る

同じ素材で速い版を作るときは、構成ファイルをもう 1 つ作る。`name` と
`basename` を変えれば中間ファイルもぶつからない。

速い版の目安:

| | ふつう | 速い |
|---|---|---|
| 1 カット | 1.4〜2.4 秒 | 0.9〜1.3 秒 |
| 文字 | 56〜64px | 58〜62px |
| `caption_bottom` | 1410 | 1100 |
| `chip` | `@0.60` | `@0.00` + `caption_border: 8` |

カットを短くすると絵が足りなくなるので、同じクリップの別の場面を足す。

数字は `references/house-style.md` の「速い版（SNS のグルメ動画の型）」を
参照。プロが撮った参考動画を実測して合わせてある。
