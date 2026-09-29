# shouhei

## 中身

| | パス |
|---|---|
| 焼肉ロス管理アプリ | `index.html` |
| ハムスターゲーム | `hamster.html` |
| Cyber Rose Crimson | `crc/index.html` |
| 紅夜モーション(一枚絵を動かしたループ映像) | `motion/index.html` |
| 紅月モーション(同上・赤い月のカット) | `motion/moon.html` |
| 月潮モーション(同上・紅い月の海とライブステージ) | `motion/tide.html` |
| トレーラー(40秒・縦) | `motion/trailer.mp4` |
| トレーラー(30秒・縦) | `motion/trailer-30s.mp4` |

## 配信方法

### raw.githack(設定不要・すぐ使える)

```
https://raw.githack.com/yama5150/shouhei/main/crc/index.html
```

ブランチ名を差し替えれば、マージ前のブランチからも配信できる。
`raw.githack.com` は開発用でレート制限あり。人に配るときは CDN 版を使う:

```
https://rawcdn.githack.com/yama5150/shouhei/main/crc/index.html
```

### GitHub Pages(要・初回設定)

Settings → Pages → Source: `Deploy from a branch` → `main` / `(root)` を選ぶと有効になる。
過去に自動有効化ワークフローが失敗して削除された経緯があるため、**有効かどうかは設定画面で要確認**。

有効化後の URL:

```
https://yama5150.github.io/shouhei/crc/
```

### Netlify

`crc/index.html` をそのまま上げる。`crc/_headers` がキャッシュ制御を担当する。

## Cyber Rose Crimson

ビジュアルノベル。全16章・単一 HTML(素材は base64 で内包、約 28.6MB)。

- 本体は `crc/index.html` の**1ファイルのみ**
- **ファイル名を変えないこと。** 変えると配信 URL が変わる
- 更新は `crc/index.html` を丸ごと差し替えて push
- 設定集(正史)は `reference/settings.md`

### ビルド前チェック

```bash
# JS構文
python3 -c "import io,re; s=io.open('crc/index.html',encoding='utf-8').read(); \
io.open('/tmp/c.js','w',encoding='utf-8').write(re.search(r'<script>(.*)</script>',s,re.S).group(1))"
node --check /tmp/c.js

# 参照整合(bg/spr/bgm/yu の実在、label/jump、ifFlag、EP_ORDER 三者整合)
node tools/verify.cjs crc/index.html
```

## 紅夜モーション

一枚絵をブラウザで動かす 12 秒ループ(1080×1920)。花火の打ち上げと照り返し、髪・袖・髪飾りの揺れ、水面のさざ波、提灯のゆらめき、舞う花びら。

- 書き出し済みの動画: `motion/koya-motion.mp4`
- 画面の「1ループ書き出し」でも端末上で MP4/WebM を保存できる(継ぎ目なくループする)
### 紅月(`motion/moon.html`)

設定シートの赤い月のカットを切り出して拡大(1320×960)。紅い月の鼓動と光輪、月にかかる薄雲、街の灯のまたたき、左へなびく髪、右から左へ流れる薔薇の花弁、月へ昇る火の粉。7.4秒目に一瞬だけ画面が乱れる(紅い月＝データ嵐の予兆)。

- 書き出し済みの動画: `motion/kougetsu-motion.mp4`
- 元のカットが 458×333px しかないため、拡大した分だけ細部は甘い。高解像度の元画像があれば `motion/src/moon.jpg` を差し替えるだけで良くなる

### 月潮(`motion/tide.html`)

紅い月の海と、眼下のライブステージ(1080×1920)。紅い月の脈動と照らされる雲、海のさざ波と青い電脳の稲妻を伝う光、揺れる船、羽ばたく鴉、行きつ戻りつ回る天井と足元の魔法陣、120BPM で明滅するステージ照明とスポットライト、提灯と蝋燭のゆらめき、舞い落ちる薔薇の花弁と昇る光の粒。

- 書き出し済みの動画: `motion/tsukishio-motion.mp4`

### トレーラー(`motion/trailer.mp4`)

40秒・縦 1080×1920。Track 01「obscure」(169.92 BPM)のイントロ → サビ48拍 → 終盤の一撃を拍の格子上でつなぎ、カットもその拍に合わせている。紅夜・月潮・設定シートの動画で構成し、一撃でタイトル。

30秒版(`motion/trailer-30s.mp4`)はイントロとサビを詰め、曲が引く16拍(112秒台)に、雨の夜に手を取るユウジの一枚絵を入れた。繋いだ手から引いて顔を見せ、そこから一撃でタイトル。

作り直すときは `tools/build-trailer.py --cut 40|30`(使い方は冒頭のコメント)。曲・シート動画・フォントはリポジトリに入れていないので引数で渡す。

### 編集

- 編集するのは `motion/src/`。`python3 tools/build-motion.py` で下絵を内包した `motion/index.html` を作る
