// 納品書からの当日単価取り込み。
//
// 紙の納品書が来る仕入先がある。写真から品名・数量・単価を読み取って表に起こしたものを
// 貼り付けて、単価マスターに当日単価として入れる。
//
// 読めない行は推測で埋めない。確認事項として列挙して人に返す。
// (ブラウザ内OCRは日本語の納品書では精度が出ないので、読み取り自体はここではやらない)

import { nfkc, num } from './units.js';
import { normName } from './bridge.js';

/** 数値として読めるトークンか。「1,200」「¥350」「2.5」を通す。 */
const asNum = (t) => {
  if (!/[0-9]/.test(t)) return null;
  if (!/^[¥￥]?[0-9,]+(\.[0-9]+)?[円]?$/.test(t)) return null;
  return num(t);
};

const SEP_TAB = /\t/;
const SEP_COMMA = /,/;

/**
 * 桁区切りのカンマを外す。「1,400」を列の区切りと読み違えないため。
 * 後読みは古い iOS Safari で使えないので、安定するまで置換を繰り返す。
 */
function stripThousands(s) {
  let prev;
  do { prev = s; s = s.replace(/(\d),(\d{3})(?!\d)/g, '$1$2'); } while (s !== prev);
  return s;
}

/** ヘッダ行っぽいか。取り込み対象から外す。 */
const isHeader = (cells) => {
  const j = cells.join('');
  return /品名|商品名|数量|単価|金額|規格/.test(j) && !cells.some((c) => asNum(c) !== null);
};

/**
 * 貼り付けたテキストを1行ずつ解釈する。
 *
 * 対応する形:
 *   タブ / カンマ区切り  → 品名, 数量, 単価 (4列以上なら 金額 で検算)
 *   スペース区切り       → 先頭の非数値を品名、続く数値を拾う
 *
 * 数値が3つ以上あるときは 数量×単価≒金額 で単価の位置を確かめる。
 * 確かめられないものは ok:false にして理由を残す。埋めない。
 */
export function parseReceiptText(text) {
  const lines = nfkc(text ?? '').split(/\r\n|\r|\n/).map((l) => l.trim()).filter(Boolean);
  return lines.map((original) => {
    const raw = stripThousands(original);
    const cells = (SEP_TAB.test(raw) ? raw.split(SEP_TAB)
      : SEP_COMMA.test(raw) ? raw.split(SEP_COMMA)
        : raw.split(/\s+/)).map((c) => c.trim()).filter((c) => c !== '');

    if (cells.length < 2) return { raw: original, ok: false, reason: '品名と単価が読み取れません' };
    if (isHeader(cells)) return { raw: original, ok: false, header: true, reason: '見出し行として除外' };

    const 品名 = cells[0];
    if (asNum(品名) !== null) return { raw: original, ok: false, reason: '先頭が品名になっていません' };

    const nums = cells.slice(1).map(asNum).filter((n) => n !== null);
    if (nums.length === 0) return { raw: original, ok: false, reason: '数値が見つかりません' };

    if (nums.length === 1) {
      // 単価だけ。数量は不明のまま残す(0で埋めない)。
      return { raw: original, 品名, 数量: null, 単価: nums[0], ok: true, note: '数量が読めないので単価だけ取り込みます' };
    }

    if (nums.length === 2) {
      const [数量, 単価] = nums;
      return { raw: original, 品名, 数量, 単価, ok: true };
    }

    // 3つ以上。数量×単価≒金額 になる並びを探して確かめる。
    for (let i = 0; i + 2 < nums.length + 1; i++) {
      const [q, u, amt] = [nums[i], nums[i + 1], nums[i + 2]];
      if (q === undefined || u === undefined || amt === undefined) break;
      if (amt > 0 && Math.abs(q * u - amt) <= Math.max(1, amt * 0.01)) {
        return { raw: original, 品名, 数量: q, 単価: u, 金額: amt, ok: true, note: '金額と突き合わせて確認済み' };
      }
    }
    return {
      raw: original, 品名, ok: false,
      reason: '数値が' + nums.length + '個あり、どれが単価か決められません（' + nums.join(' / ') + '）',
    };
  });
}

/**
 * 読めた行を単価マスターに突き合わせる。
 * 完全一致 → 部分一致が1件のときだけ当てる。複数候補は当てない。
 */
export function matchToMaster(rows, items) {
  return rows.map((r) => {
    if (!r.ok) return { ...r, match: null };
    const n = normName(r.品名);
    const exact = items.filter((it) => normName(it.食材名称) === n);
    if (exact.length === 1) return { ...r, match: exact[0], matchKind: '完全一致' };
    if (exact.length > 1) return { ...r, match: null, matchNote: '同名が' + exact.length + '件。どれか選んでください' };
    const partial = items.filter((it) => {
      const m = normName(it.食材名称);
      return m && (m.includes(n) || n.includes(m));
    });
    if (partial.length === 1) return { ...r, match: partial[0], matchKind: '部分一致' };
    if (partial.length > 1) return { ...r, match: null, matchNote: '候補が' + partial.length + '件。どれか選んでください' };
    return { ...r, match: null, matchNote: 'マスターに無い品目' };
  });
}

/**
 * 適用する。仕入単価と更新日だけ書き換える。入り数・歩留まりは触らない。
 * @returns {{items:Array, applied:number}}
 */
export function applyReceipt(items, plan, 日付) {
  const byId = new Map(plan.filter((p) => p.itemId && p.単価 !== null && p.単価 !== undefined)
    .map((p) => [p.itemId, p.単価]));
  let applied = 0;
  const next = items.map((it) => {
    if (!byId.has(it.id)) return it;
    const v = byId.get(it.id);
    if (it.仕入単価 === v) return it;
    applied++;
    return { ...it, 仕入単価: v, 更新日: 日付 ?? null };
  });
  return { items: next, applied };
}
