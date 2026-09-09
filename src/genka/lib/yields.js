// 歩留まりの記録。
//
// 丸一本仕入れ(本鮪など)は、可食部歩留まりを1本ごとに記録する。
// 記録項目は「誰が捌いたか・ラウンド重量・柵の総重量」の3つ。
// 卸し手で歩留まりは変わるので、担当者を残さないと数字の意味が読めない。

import { num } from './units.js';
import { normName } from './bridge.js';

/**
 * 歩留まり = 可食部重量 ÷ ラウンド重量。
 * 片方でも読めなければ null。0除算・1超えは記録ミスとして弾く。
 * @returns {{rate:number}|{error:string}}
 */
export function yieldRate(round, edible) {
  const r = num(round), e = num(edible);
  if (r === null || e === null) return { error: '重量が両方入っていません' };
  if (r <= 0) return { error: 'ラウンド重量が0以下です' };
  if (e <= 0) return { error: '可食部重量が0以下です' };
  if (e > r) return { error: '可食部がラウンドを超えています。入力を確認してください' };
  return { rate: e / r };
}

/** 記録が有効(歩留まりが出せる)かどうか。 */
export const isValidLog = (log) => 'rate' in yieldRate(log.ラウンド重量, log.可食部重量);

/**
 * 食材ごとにまとめる。平均・最新・件数・ばらつきを出す。
 * 1件しかないものは平均と言い張らない(件数を必ず添えて表示側で判断させる)。
 */
export function summarize(logs) {
  const byName = new Map();
  for (const log of logs) {
    const y = yieldRate(log.ラウンド重量, log.可食部重量);
    if (y.error) continue;
    const k = normName(log.食材名);
    if (!k) continue;
    if (!byName.has(k)) byName.set(k, { 食材名: log.食材名, itemId: log.itemId ?? null, rates: [], logs: [] });
    const g = byName.get(k);
    g.rates.push(y.rate);
    g.logs.push({ ...log, rate: y.rate });
    if (!g.itemId && log.itemId) g.itemId = log.itemId;
  }
  return [...byName.values()].map((g) => {
    const sorted = [...g.rates].sort((a, b) => a - b);
    const avg = g.rates.reduce((a, b) => a + b, 0) / g.rates.length;
    const byDate = [...g.logs].sort((a, b) => String(a.日付 || '').localeCompare(String(b.日付 || '')));
    return {
      食材名: g.食材名,
      itemId: g.itemId,
      件数: g.rates.length,
      平均: avg,
      最小: sorted[0],
      最大: sorted[sorted.length - 1],
      最新: byDate[byDate.length - 1]?.rate ?? avg,
      logs: g.logs,
    };
  }).sort((a, b) => b.件数 - a.件数);
}

/** 担当者ごとの歩留まり。卸し手で変わるので分けて見る。 */
export function byHandler(logs) {
  const m = new Map();
  for (const log of logs) {
    const y = yieldRate(log.ラウンド重量, log.可食部重量);
    if (y.error) continue;
    const k = (log.担当者 || '').trim() || '(記録なし)';
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(y.rate);
  }
  return [...m.entries()]
    .map(([担当者, rates]) => ({
      担当者, 件数: rates.length,
      平均: rates.reduce((a, b) => a + b, 0) / rates.length,
    }))
    .sort((a, b) => b.件数 - a.件数);
}
