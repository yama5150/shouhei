#!/usr/bin/env python3
"""crc/index.html の通しプレイQA。

全話を headless Chromium で最後まで自動で進め、停止・エラー・メモリを測る。
tools/verify.cjs が「参照が実在するか」を見るのに対し、こっちは
「実際に最後まで到達するか」を見る。verify.cjs では絶対に見つからない
停止(無限ループ、進まない選択肢、終了判定の取りこぼし)が対象。

    python3 tools/qa.py                # 全話
    python3 tools/qa.py 8 en3          # 話数を指定
    python3 tools/qa.py --mem          # 1話ごとに renderer の実メモリも出す

終了経路は3つある。全部見ないと誤って「停止」と判定する:
  {ed:true}  -> #ed.show        (第一話など)
  {fin:true} -> #curtain に「おわり」 (幕間・後日談・隠し章)
  最終話      -> #pv.show        (ed が PV に分岐する)
"""
import json, subprocess, sys, time, os

HTML = os.path.join(os.path.dirname(__file__), "..", "crc", "index.html")
# Chromium の版は環境で変わるので固定しない(1194 → 1243 で一度壊れた)
import glob as _glob
_c = sorted(_glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))
CHROME = _c[-1] if _c else "chromium"

# ページ内で完結させる。1行ごとに CDP を往復すると桁違いに遅くなる
DRIVER = r"""
async (args) => {
  const [ep, capMs] = args;
  try{ if(typeof leaveEd==='function') leaveEd(); }catch(e){}
  try{ if(typeof clearEdTimers==='function') clearEdTimers(); }catch(e){}
  const edEl = document.getElementById('ed');
  const pvEl = document.getElementById('pv');
  const box  = document.getElementById('choiceBox');
  const cur  = document.getElementById('curtain');
  const curT = document.getElementById('curtainText');
  edEl.classList.remove('show');
  startGame(ep, false);
  state.skip = true;
  const t0 = performance.now();
  let lastI = -1, lastChange = performance.now(), choices = 0, maxI = 0;
  const picks = [];
  const mk = (r) => Object.assign({
      ep, cmds: maxI, choices, picks,
      ms: Math.round(performance.now() - t0),
      n: (typeof SC !== 'undefined' && SC) ? SC.length : 0 }, r);
  while (true) {
    await new Promise(r => setTimeout(r, 12));
    if (edEl.classList.contains('show')) return mk({end:'ED'});
    if (pvEl && pvEl.classList.contains('show')) return mk({end:'PV'});
    if (cur.classList.contains('on') && /おわり/.test(curT.textContent))
      return mk({end:'FIN'});
    // 選択肢は押しても DOM に残り display:none になるだけ。
    // .show を見ないと見えないボタンを押し続けて無限ループする
    if (box.classList.contains('show')) {
      const cb = box.querySelectorAll('.choice');
      if (cb.length) {
        picks.push(state.i + ':' + cb[0].textContent.slice(0, 16));
        cb[0].click(); choices++; state.skip = true;
        lastChange = performance.now(); continue;
      }
    }
    if (typeof typing !== 'undefined' && typing) completeText();
    else if (typeof waitingTap !== 'undefined' && waitingTap) advance();
    if (!state.skip) state.skip = true;          // showChoice が毎回 false に戻す
    if (state.i > maxI) maxI = state.i;
    if (state.i !== lastI) { lastI = state.i; lastChange = performance.now(); }
    else if (performance.now() - lastChange > 9000)
      return mk({end:'STALL', at: state.i,
                 typing: (typeof typing !== 'undefined') ? typing : null});
    if (performance.now() - t0 > capMs) return mk({end:'CAP', at: state.i});
  }
}
"""

def renderer_rss():
    """chrome のレンダラプロセスの RSS(MB)。performance.memory は
    量子化された値を返して当てにならないので ps で見る。"""
    out = subprocess.run(["ps", "-o", "rss=,args=", "-C", "chrome"],
                         capture_output=True, text=True).stdout
    mb = 0
    for line in out.splitlines():
        p = line.strip().split(None, 1)
        if len(p) >= 2 and "--type=renderer" in p[1]:
            mb += int(p[0])
    return mb / 1024

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    want_mem = "--mem" in sys.argv
    from playwright.sync_api import sync_playwright

    errs, rows = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME,
                args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844})
        pg.on("pageerror", lambda e: errs.append(("pageerror", str(e)[:300])))
        pg.on("console", lambda m: errs.append(("console", m.text[:300]))
              if m.type == "error" else None)
        base = renderer_rss() if want_mem else 0
        t0 = time.time()
        pg.goto("file://" + os.path.abspath(HTML), wait_until="load", timeout=300000)
        pg.wait_for_timeout(2500)
        print("load %.1fs" % (time.time() - t0), end="")
        if want_mem:
            print("  起動直後 renderer=%.0fMB (+%.0fMB)" % (renderer_rss(), renderer_rss() - base), end="")
        print(flush=True)

        order = args or pg.evaluate("EP_ORDER")
        titles = pg.evaluate("EP_TITLES")
        pg.evaluate("ensureCtx && ensureCtx()")
        for ep in order:
            try:
                r = pg.evaluate(DRIVER, [ep, 150000])
            except Exception as e:
                r = {"ep": ep, "end": "EXCEPTION", "err": str(e)[:200]}
            t = titles.get(ep) if isinstance(titles, dict) else None
            r["title"] = t[0] if isinstance(t, list) and t else ""
            if want_mem:
                r["rendMB"] = round(renderer_rss())
            rows.append(r)
            print("%-4s %-9s %-10s %4s/%-4s 選択肢%-2s %6sms%s" % (
                ep, r.get("end"), r.get("title", "")[:10], r.get("cmds"), r.get("n"),
                r.get("choices"), r.get("ms"),
                "  renderer=%4dMB" % r["rendMB"] if want_mem else ""), flush=True)
        b.close()

    bad = [r for r in rows if r.get("end") not in ("ED", "FIN", "PV")]
    incomplete = [r for r in rows
                  if r.get("n") and r.get("cmds") is not None and r["cmds"] < r["n"] - 1]
    uniq, seen = [], set()
    for k, v in errs:
        if v not in seen:
            seen.add(v); uniq.append((k, v))

    print()
    if uniq:
        print("JSエラー %d種:" % len(uniq))
        for k, v in uniq: print("  ", k, ":", v)
    else:
        print("JSエラー なし")
    if bad:
        print("到達しなかった話:", ", ".join("%s(%s)" % (r["ep"], r.get("end")) for r in bad))
    if incomplete:
        print("最終コマンドまで届かなかった話:",
              ", ".join("%s(%s/%s)" % (r["ep"], r["cmds"], r["n"]) for r in incomplete))
    if not uniq and not bad and not incomplete:
        print("通しプレイ OK — %d話すべて最終コマンドに到達" % len(rows))
    return 1 if (uniq or bad or incomplete) else 0

if __name__ == "__main__":
    sys.exit(main())
