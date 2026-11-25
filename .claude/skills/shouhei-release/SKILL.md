---
name: shouhei-release
description: 翔平(shou.5150)の作品を Vercel(shouhei.vercel.app)で公開・更新する手順と、紹介LP(crc/lp/)の直し方。新しい作品をサイトに載せる、作品の更新を本番に反映する、LPの絵・文・カードを変える、短いURLやQRを作る、「公開して」「本番に出して」「反映されない」「404」「LP」「Vercel」「QR」「Coming Soon」が出てきたら最初に読むこと。どの作品(Cyber Rose Crimson / Dirt and Smoke / リゼ丸 / 新作)の作業でも、本番に出す段階では必ずこれに従う。
---

# 翔平の作品を公開・更新する

この文書は Claude 専用ではない。GPT など他の AI もリポジトリ直下の `AGENTS.md` からここに来る。
道具の名前に依存しない書き方にしてある。

## 全体の形

```
GitHub: yama5150/shouhei(全作品がこの1リポジトリに入っている)
   │  main に入った瞬間に
   ▼
Vercel プロジェクト「shouhei」(Hobby・無料)── 1〜2分で自動デプロイ
   ▼
https://shouhei.vercel.app
```

- **本番 = `main`。** `main` に入れる以外に本番を変える方法は無いし、要らない
- `main` 以外のブランチに push すると、Vercel がプレビューを自動で作る
  (PR に vercel[bot] が表を貼る)。プレビューは Vercel のログインが要ることがある
- ビルドは無い。リポジトリの中身がそのまま配られる(`vercel.json` がそう指定している)

## いまのURL

| URL | 中身 | 実体 |
|---|---|---|
| `/` | 紹介LP へ転送 | `crc/lp/index.html` |
| `/play` `/crimson` | Cyber Rose Crimson 本編へ転送 | `crc/index.html` |
| `/hamster.html` | リゼ丸のプチプチ冒険🟢島 | `hamster.html` |
| `/rizemaru` `/rize` `/hamster` | ↑へ転送 | |
| `/yakiniku.html` | 焼肉ロス管理アプリ(仕事用。宣伝しない) | |

転送は `vercel.json` の `redirects`。**新しい短いURLもここに足す。**

## 作業の流れ(毎回これ)

1. **作業用ブランチで直す。** `main` に直接 push しない
2. **ローカルで確かめる。** `python3 -m http.server` で配って、ヘッドレスのブラウザで
   スマホ幅(390x844、横向きゲームは 844x390 か iPhone landscape)を開き、
   JSエラー・404・横スクロールが無いことを見る
3. **PR を作る。** 何を変えたか・何を確かめたかを日本語で書く
4. **翔平の OK をもらってからマージする。** マージ = 世界に公開、なので必ず聞く
5. **本番で確かめる。** マージ後 1〜2分で切り替わる。変えたファイルが本番から返るまで
   待ち(`curl` で中身の一部を grep するのが確実)、ブラウザで開いて最後まで動かす
6. **翔平に URL を渡す**(渡し方の注意は下)

作品ごとの検証手順がある場合はそれも通す。CRC なら `crc-build` スキルの
`verify.cjs` と `qa.py` が必須。

## 新しい作品を載せるとき

1. 作品を**専用のフォルダ**に置く(例:`dirt/index.html`)。直下に散らかさない
2. 中のファイル参照は**全部相対パス**(`./img/a.png`、`../icon.png`)。
   `https://raw.githack.com/...` のような絶対URLは本番で古い版を指す(下の罠 4)
3. 短いURLが欲しければ `vercel.json` の `redirects` に足す
4. LP の「次の作品」カードを更新する(Coming Soon → 遊べるようになったら「遊ぶ ▶」)
5. QR が要るなら作る(後述)

## 紹介LP(`crc/lp/`)

- 本体は `crc/lp/index.html` の1枚。素材は `crc/lp/img/`(WebP)、`crc/lp/audio/`(試聴30秒 MP3)、
  `crc/lp/hero.mp4`(トップの動画)、`crc/lp/dirt-pv.mp4`(Dirt and Smoke の PV)
- 節の並び:トップ → Story → Concept → 登場人物 → 収録曲(12曲、Sunoへのリンク付き)
  → ギャラリー → 遊びかた → 最後のCTA → 次の作品(Coming Soon)→ フッター(Instagram・Suno)
- 作者表記:原作・企画・音楽・ビジュアル **shou.5150** / シナリオ shou.5150 × Claude
- Instagram:`https://www.instagram.com/shou.5150/` / Suno:`https://suno.com/@shouyama`
- **リゼ丸のカードは意図して Coming Soon のまま**(ゲーム自体は公開済み。LP からは辿らせない。
  URL と QR を知っている人だけが遊べる、という翔平の判断)

### CRC の絵を LP に持ってくる

CRC の絵はすべて `crc/index.html` の `ASSETS` に base64 で埋まっている。**新しい絵は
`main` ではなくビジュアル担当のブランチにあることが多い**(2026-11 時点では
`claude/elegant-dijkstra-w9yj7t`)。LP の絵が「旧型のまま」と言われたらまずそこを見る。

```bash
python3 .claude/skills/shouhei-release/scripts/extract_asset.py \
    --ref origin/claude/elegant-dijkstra-w9yj7t sprSomei sprEleven --out /tmp/x
convert /tmp/x/sprSomei.jpg -resize 600x900 -quality 80 crc/lp/img/somei.webp
```

ファイル名を変えずに上書きしてよい(全ファイル `no-cache` なので、次に開いたとき新しい絵になる)。

**ネタバレ禁止:** 美月(`sprMizuki`)・最終話の内容・「7回の周回」・ソメイの本当の年齢は LP に出さない。
人物紹介は `reference/settings.md` の第5節から、**本編に実在する台詞だけ**を引く(作文しない)。

## 翔平とのやりとり

- **日本語で、くだけた口調で。** 英語で返すと「めっさ英語だけど大丈夫?」と言われる
- **翔平は iPhone 1台で作業している。** 手順は「どの画面の、どのボタンか」まで書く。
  英語の画面は何が書いてあるか訳す
- **URL は1行に単独で置く。** 直後に文字を続けない(罠 1)
- 翔平の作品の中身(あらすじ・紹介文)は、もらった素材か本編にあるものだけを使う。
  無いものは「タイトルだけ」にして、足すかどうかを聞く

## QR を作る

```bash
python3 -m venv /tmp/qv && /tmp/qv/bin/pip -q install "qrcode[pil]" opencv-python-headless
```

`qrcode` で作り、**必ず読み取り直して中身を確かめる**(`cv2.QRCodeDetector().detectAndDecode`)。
日本語の文字を載せるならフォントは `/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf`
(指定しないと文字が出ない)。QR 画像はリポジトリに入れず、翔平に直接渡す。

## 踏んだ罠

全部、実際に起きたこと。

1. **URL の直後に文字を書いたら 404。** 「https://…/hamster.html(QRと同じ行き先)」と書いたら、
   チャットがカッコまでリンクにして、翔平は存在しないページを開いた。
   → URL は1行に単独で。後ろに句読点やカッコをつけない
2. **`vercel.json` が無いと焼肉アプリしか公開されない。** `vite.config.js` と `package.json` があるので、
   Vercel は Vite と判定して `npm run build` → `dist/` だけを配る。ゲームも LP も 404 になる。
   → `vercel.json` の `framework: null` / `installCommand: ""` / `outputDirectory: "."` を消さない。
   Vercel の画面の「Application Preset」が Vite でも、`vercel.json` が勝つ
3. **`outputDirectory` を書き忘れると、プリセットが Vite のプロジェクトでは `dist` のまま。**
   `/` の転送は効くのに転送先が全部 404、という分かりにくい壊れ方をした
4. **githack の絶対URLが残っていると、本番が githack 側の古い版を読む。**
   リゼ丸の `manifest.webmanifest` とアイコンがそうだった。→ 相対パスにする
5. **`.html` 無しのURLは 404。** `cleanUrls` は使わない(`/crc/lp/` の末尾スラッシュが消えて、
   LP の相対パスが全部壊れる)。代わりに `redirects` で個別に転送する
6. **`<img>` に `width`/`height` 属性を書いたら、`height:auto` が無いせいで縦に引き伸ばされた。**
   → CSS の `img{height:auto}` を消さない
7. **Vercel の初回設定中に本人確認(メールの6桁コード)が割り込むと、入力がリセットされて
   同じリポジトリのプロジェクトが2つできた。** 余分な方は Settings → Advanced(または General)
   の一番下「Delete Project」で消した。残すのは `shouhei`
8. **作業環境から外に出られないことがある。** Claude のクラウド環境では許可したホストにしか
   繋がらない。`shouhei.vercel.app` と `vercel.com` は許可済み。プレビューURL(`*-git-*.vercel.app`)は
   見られないので、本番で確かめるか翔平に見てもらう

## 他の作業との関係

- CRC 本編:`crc-build` スキルに従う。ビジュアルの作業は別チャット(ブランチ `claude/elegant-dijkstra-w9yj7t`)。
  `crc/index.html` を両方から触ると食い違うので、触る前に `main` の最新を取る
- Dirt and Smoke:別チャット(ブランチ `claude/dirt-smoke-visual-novel-x984pk`)
- リゼ丸:`hamster.html`(`main` に入っている)
- 予算:Hobby の転送量は月100GB。CRC 本編は初回1回で約41MB なので、初回プレイ換算で月2,400回前後
