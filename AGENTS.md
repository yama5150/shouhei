# AGENTS.md — このリポジトリで作業する AI へ

Claude・GPT(Codex)・その他、どの AI でもまずこれを読むこと。

## このリポジトリは何か

翔平(shou.5150)の作品置き場。全部が1つのリポジトリに入っていて、
**`main` に入ったものが 1〜2分で https://shouhei.vercel.app に自動公開される**(Vercel)。

| 作品 | 場所 | 公開URL |
|---|---|---|
| 紹介LP | `crc/lp/index.html` | `/` |
| Cyber Rose Crimson(ビジュアルノベル) | `crc/index.html` | `/play` |
| リゼ丸のプチプチ冒険🟢島(ゲーム) | `hamster.html` | `/rizemaru` |
| Dirt and Smoke(ビジュアルノベル) | ブランチ `claude/dirt-smoke-visual-novel-x984pk` | 未公開(LP で Coming Soon) |
| 焼肉ロス管理アプリ(仕事用) | `index.html` / `src/` | `/yakiniku.html` |

## 守ること

1. **`main` に直接 push しない。** ブランチで作業 → PR → **翔平の OK をもらってから**マージ。
   マージ = 世界に公開
2. **公開・LP・URL・QR に関わる作業は、先に手順書を読む:**
   `.claude/skills/shouhei-release/SKILL.md`(道具に依存しない書き方。Claude 以外も読める)
3. **Cyber Rose Crimson(`crc/index.html`)に触るなら、先に:**
   `.claude/skills/crc-build/SKILL.md` と `reference/settings.md` の第0節。
   約41MB の単一 HTML で、`grep` や `cat` でそのまま開くと base64 で埋まる。検証(`tools/verify.cjs`・`tools/qa.py`)を通さずに出さない
4. **`vercel.json` を消さない・`outputDirectory: "."` を外さない。** 外すと焼肉アプリしか公開されず、他は全部 404 になる
5. **ファイル参照は相対パスで。** `raw.githack.com` などの絶対 URL を作品の中に書かない
6. **同じ作品を複数の AI / チャットが同時に触ることがある。** 作業前に `main` の最新を取り込み、
   どのブランチで誰が何をしているかは `reference/settings.md` 第0節と上の手順書の末尾を見る

## 翔平とのやりとり

- 日本語・くだけた口調で
- 翔平は iPhone 1台で作業している。手順は「どの画面のどのボタンか」まで書く
- URL は1行に単独で置き、直後に文字やカッコを続けない(チャットがリンクに巻き込んで 404 になった実例あり)
- 作品の紹介文・台詞は、本編か翔平の素材にあるものだけを使う。作文しない
