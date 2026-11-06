# DIRT AND SMOKE — 現在地

> このフォルダの入口。迷ったらまずここ。（最終更新：2026-11-06）
> 総監督・音楽：shouyama ／ ビジュアル：ChatGPT ／ シナリオ：Claude

## ひとことで
**愛していたから、ひとつになった。けれど、そこに残ったのは誰だったのか。**
死んだ妹を作り直した姉と、目覚めた「妹の形をした少女」のゴシック心理ホラー。主題歌は総監督の「Dirt and Smoke」。

## いまの状態
| | 状態 |
|---|---|
| **PV（姉妹版・約3分）** | ✅ **完成**　`works/pv_final/DIRT_AND_SMOKE_PV.mp4` |
| イタイ演出デモ | ✅ 完成（60分版・第五章の原型）　`works/demo_itai/` |
| **60分版ビジュアルノベル** | ⏸ 章別プロット v0.1。**総監督の判断待ち（7項目）** → `docs/04_未決事項.md` |
| 博士版（最初のVN試作・6分半PV） | 📦 保管　`archive/博士版/` |

## 次にやること
1. 総監督：`docs/04_未決事項.md` の A1〜A7 に答える（「推奨でOK」でも可）
2. Claude：60分版の脚本を第一章から書く。並行して横画面のエンジンを用意
3. ChatGPT：`docs/05_ChatGPT共有用_現状まとめ.md` を共有。絵の発注はプロット確定後

## フォルダの中身
```
dirt-and-smoke/
├─ README.md                ← いまここ（現在地）
├─ docs/                    ← 文書
│   ├─ 00_原案_企画書.md       最初の構想（総監督の企画書そのまま）
│   ├─ 01_構想の変遷.md        何を作り、何が分かり、なぜ変えたか
│   ├─ 02_設定資料_姉妹編.md   作品のバイブル（確定／提案／未決つき）
│   ├─ 03_決定事項ログ.md      いつ誰が何を決めたか
│   ├─ 04_未決事項.md          総監督に聞くこと
│   ├─ 05_ChatGPT共有用_現状まとめ.md   そのまま貼れる
│   └─ 60分版/
│       ├─ 章別プロット_v0.1.md
│       └─ 第五章_イタイ_演出案.md
├─ works/                   ← 出来たもの
│   ├─ pv_final/               完成PV（MP4・Web版・作り直し用の部品）
│   └─ demo_itai/              イタイ演出デモ（Web）
├─ assets/                  ← 素材（README.md に一覧）
│   ├─ img/                    絵（ChatGPT制作）
│   └─ audio/                  音楽（総監督制作）4曲
└─ archive/博士版/          ← 保管（消していない）
    ├─ docs/                   構成案・脚本・依頼文など 01〜10
    ├─ game_v1/                最初のビジュアルノベル試作（スマホ縦）
    ├─ pv_v1_6min/             最初のPV（約6分半・C案）
    └─ mock_文字色/            「私」の色のモック画像
```

## 見る・遊ぶ
ブラウザで開けるもの（GitHub のブランチから直接配信）。ブランチ名を差し替えれば、ほかのブランチからも開ける。
- 完成PV（Web版）：`https://raw.githack.com/yama5150/shouhei/claude/dirt-smoke-visual-novel-x984pk/dirt-and-smoke/works/pv_final/index.html`
- イタイデモ：`https://raw.githack.com/yama5150/shouhei/claude/dirt-smoke-visual-novel-x984pk/dirt-and-smoke/works/demo_itai/index.html`
- 完成PV（MP4をダウンロード）：`https://github.com/yama5150/shouhei/raw/claude/dirt-smoke-visual-novel-x984pk/dirt-and-smoke/works/pv_final/DIRT_AND_SMOKE_PV.mp4`

※ ブランチ名に「/」を含むため、raw.githack でうまく開けない場合は、ブランチ名のかわりにコミットの番号（SHA）を入れる。

## 作品のルール（崩すと壊れるもの）
詳しくは `docs/02_設定資料_姉妹編.md`。
- 「私」の一文字だけに色：青＝姉／赤＝妹／白＝境界の消失／紫＝最後の意識（作品中ただ一度）
- 鏡は現実より少しだけ先に動く
- 縫い目 23 → 24 → （25）
- 真相は明かさない。最後の一言は「おやすみ。」
- 怖さは「違和感」と「不在」から。美しい顔と涙は怖さを薄める
