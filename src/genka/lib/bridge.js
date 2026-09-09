// 焼肉ロス管理アプリ(index.html)への原価の受け渡し。
//
// 両アプリは同じホストから配信されるので localStorage を共有する。
// ロス管理側のキーは bl_menu / bl_menu_ver。構造は
//   [{ id, category, iconType, defaultUnit, items: [{ id, name, unit, cost, defaultQty }] }]
//
// 注意: ロス管理アプリは起動時に bl_menu_ver を見て、値が合わないとメニューを
// 初期データに戻す。bl_menu_ver には触らない。まだ一度も起動されていない
// (=verが無い)ときは書き込まない。書いても次回起動時に消えるため。

import { nfkc } from './units.js';

export const LOSS_KEYS = { menu: 'bl_menu', ver: 'bl_menu_ver' };
export const BACKUP_KEY = 'gk_bl_menu_backup';

/** 名寄せ用のキー。全角半角と空白の揺れだけ潰す。中身は変えない。 */
export const normName = (s) => nfkc(s ?? '').toLowerCase().replace(/[\s　]/g, '');

/**
 * ロス管理側のメニューを読む。
 * @returns {{menu:Array, ver:string}|{error:string}}
 */
export function readLossMenu(storage = globalThis.localStorage) {
  let raw, ver;
  try {
    raw = storage.getItem(LOSS_KEYS.menu);
    ver = storage.getItem(LOSS_KEYS.ver);
  } catch {
    return { error: 'localStorage を読めません' };
  }
  if (!raw) {
    return { error: 'ロス管理アプリのメニューが見つかりません。同じ配信元(同じドメイン)から一度ロス管理アプリを開いてください。' };
  }
  if (!ver) {
    // ver が無い状態で書いても、ロス管理アプリの次回起動時に初期化されて消える。
    return { error: 'ロス管理アプリがまだ初期化されていません。先に一度そちらを開いてから戻ってきてください。' };
  }
  let menu;
  try { menu = JSON.parse(raw); } catch { return { error: 'メニューの形式が壊れています' }; }
  if (!Array.isArray(menu)) return { error: 'メニューの形式が想定と違います' };
  return { menu, ver };
}

/** メニューを平らにして [{categoryId, category, item}] にする。 */
export function flattenMenu(menu) {
  const out = [];
  for (const c of menu ?? []) {
    for (const it of c.items ?? []) out.push({ categoryId: c.id, category: c.category, item: it });
  }
  return out;
}

/**
 * 料理名からメニュー品目を当てる。完全一致 → 部分一致の順。
 * 曖昧なものは当てない(null)。勝手に結びつけない。
 */
export function autoMatch(recipeName, menu) {
  const n = normName(recipeName);
  if (!n) return null;
  const flat = flattenMenu(menu);
  const exact = flat.filter((f) => normName(f.item.name) === n);
  if (exact.length === 1) return exact[0];
  if (exact.length > 1) return null; // 同名が複数。人が選ぶ
  const partial = flat.filter((f) => {
    const m = normName(f.item.name);
    return m.includes(n) || n.includes(m);
  });
  return partial.length === 1 ? partial[0] : null;
}

/**
 * 反映プランをメニューに適用する。元の配列は変更しない。
 * @param plan [{ target: {categoryId, itemId} | {categoryId, newName}, cost }]
 * @returns {{menu:Array, updated:number, added:number}}
 */
export function applyPlan(menu, plan) {
  let updated = 0, added = 0;
  const byCat = new Map();
  for (const p of plan) {
    if (!p?.target || p.cost === null || p.cost === undefined) continue;
    const list = byCat.get(p.target.categoryId) ?? [];
    list.push(p);
    byCat.set(p.target.categoryId, list);
  }

  const next = menu.map((c) => {
    const ps = byCat.get(c.id);
    if (!ps) return c;
    let items = c.items ?? [];
    // 既存品目の原価を差し替える
    items = items.map((it) => {
      const hit = ps.find((p) => p.target.itemId === it.id);
      if (!hit) return it;
      const cost = Math.max(0, Math.round(hit.cost));
      if (cost === it.cost) return it;
      updated++;
      return { ...it, cost };
    });
    // 新規品目を足す
    for (const p of ps.filter((x) => x.target.newName)) {
      const name = String(p.target.newName).trim();
      if (!name) continue;
      if (items.some((it) => normName(it.name) === normName(name))) continue; // 同名は足さない
      items = [...items, {
        // ロス管理側の generateId と衝突しない接頭辞にする
        id: 'i-gk-' + Math.random().toString(36).slice(2, 9) + '-' + Date.now().toString(36),
        name,
        unit: c.defaultUnit || '皿',
        cost: Math.max(0, Math.round(p.cost)),
        defaultQty: 1,
      }];
      added++;
    }
    return { ...c, items };
  });

  return { menu: next, updated, added };
}
