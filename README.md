# shouhei

## 中身

| | パス |
|---|---|
| 焼肉ロス管理アプリ | `index.html` |
| ハムスターゲーム | `hamster.html` |
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

ビジュアルノベル。全16章・単一 HTML(素材は base64 で内包、約 34.5MB)。

- 本体は `crc/index.html` の**1ファイルのみ**
- **ファイル名を変えないこと。** 変えると配信 URL が変わる
- 更新は `crc/index.html` を丸ごと差し替えて push
- 設定集(正史)は `reference/settings.md`

### ビルド前チェック

```bash
# JS構文 ── <script>は3ブロックある。欲張りな正規表現で1個に繋げると
#            途中の </script> で必ず SyntaxError になるので、1ブロックずつ見る
python3 - <<'EOF'
import io,re
s=io.open('crc/index.html',encoding='utf-8').read()
for i,b in enumerate(re.findall(r'<script>(.*?)</script>',s,re.S)):
    io.open('/tmp/c%d.js'%i,'w',encoding='utf-8').write(b)
    print('block',i,len(b))
EOF
for f in /tmp/c*.js; do node --check "$f" && echo "$f OK"; done

# 参照整合(bg/spr/bgm/yu の実在、label/jump、ifFlag、EP_ORDER 三者整合)
node tools/verify.cjs crc/index.html
```
