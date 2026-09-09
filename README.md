# shouhei

## 中身

| | パス |
|---|---|
| 焼肉ロス管理アプリ | `index.html` |
| ハムスターゲーム | `hamster.html` |
| 原価出しツール | `genka/index.html` |
| Cyber Rose Crimson | `crc/index.html` |

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

## 原価出しツール

仕入単価から料理の原価・原価率・1個原価を出す。単一 HTML なので `crc/` と同じく
raw.githack からそのまま配信できる。データは localStorage に入る（端末内のみ・共有はされない）。

```
https://raw.githack.com/yama5150/shouhei/main/genka/index.html
```

### できること

- インフォマートのマイカタログ CSV（cp932 のまま）を取り込んでグラム単価に換算
- 仕込み単位での原価計算（1仕込み / 1個 / 100g / 原価率 / バイキングの一人あたり）
- 揚げ物の衣を実付着量 3〜7割で並べた試算
- 社内 LINE 用テキスト（現場向け簡潔版・新人向け詳細版）と CSV 書き出し

### 数字を作らない方針

- 単価が空欄の行は時価品として**未確定のまま残す**。0 では埋めない
- 歩留まりの既定は 100%。実測が出た品目だけ上書きする
- 内容量が読めない品目は未換算のまま。実際に使う品目だけ手で入れれば足りる

### ビルド

焼肉ロス管理アプリとは入口・出力・CSS の走査範囲をすべて分けてある
（`vite.genka.config.js`）。`npm run build` 側には影響しない。

```bash
npm run dev:genka     # 開発サーバ
npm run build:genka   # genka/index.html を作り直す
npm test              # 単位換算・CSV換算・原価計算のテスト
```

換算まわりは 10 倍ずれる落とし穴（`2L` は等級であって容量ではない、
`40g×50本` の ×50 は単位が C/S のときだけ掛ける、など）が多いので、
`src/genka/lib/__tests__/` に固定してある。ロジックを触ったら `npm test` を通すこと。
