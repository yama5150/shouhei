// 原価計算。
//
// 型はスキルに従う:
//  - 仕込み単位で出す(1皿ではなく「2kg仕込みで何個」)
//  - 歩留まりは主材料にかける。使用量の合計にはかけない
//  - 出す数字は 1仕込み原価 / 1個あたり / 100gあたり / 原価率
//  - バイキングは一人あたりで見る
//  - 揚げ物の衣は実付着量(3〜7割)の試算も並べる

import { num } from './units.js';

/** マスター1件のグラム単価(= 使用量1単位あたりの原価)。時価品や未換算は null。 */
export function itemUnitPrice(item) {
  if (!item) return null;
  const p = num(item.仕入単価);
  if (p === null) return null;
  const count = num(item.入り数);
  if (count === null || count <= 0) return null;
  const y = num(item.歩留まり) ?? 1.0;
  if (y <= 0) return null;
  return p / count / y;
}

/**
 * レシピ1行の原価を出す。
 * 手入力単価は自動参照より優先する(時価品はこちらで当日単価を入れる)。
 */
export function lineCost(line, itemsById) {
  const qty = num(line.使用量);
  const manual = num(line.手入力単価);
  const item = line.itemId ? itemsById.get(line.itemId) : null;
  const auto = itemUnitPrice(item);
  const unitPrice = manual !== null ? manual : auto;
  const 照合 = line.itemId ? (item ? 'OK' : '未登録') : (manual !== null ? '手入力' : '未登録');
  return {
    unitPrice,
    源: manual !== null ? '手入力' : auto !== null ? 'マスター' : null,
    照合,
    cost: unitPrice === null || qty === null ? null : unitPrice * qty,
  };
}

const COATING_RATIOS = [1.0, 0.7, 0.5, 0.3];

/**
 * レシピ全体を計算する。
 * @param recipe {{lines, 仕上がり重量, 個数, 売価, 取り分け人数}}
 * @param itemsById Map<id, masterItem>
 */
export function calcRecipe(recipe, itemsById) {
  const rows = (recipe.lines || []).map((l) => ({ line: l, ...lineCost(l, itemsById) }));

  const sum = (pred) => rows.reduce((a, r) => (pred(r) && r.cost !== null ? a + r.cost : a), 0);
  const 衣原価 = sum((r) => r.line.区分 === '衣');
  const 衣以外 = sum((r) => r.line.区分 !== '衣');
  const 仕込み原価 = 衣以外 + 衣原価;

  const 未確定 = rows.filter((r) => r.cost === null);
  const 個数 = num(recipe.個数);
  const 仕上がり重量 = num(recipe.仕上がり重量);
  const 売価 = num(recipe.売価);
  const 人数 = num(recipe.取り分け人数);

  const perPiece = 個数 && 個数 > 0 ? 仕込み原価 / 個数 : null;
  const per100g = 仕上がり重量 && 仕上がり重量 > 0 ? (仕込み原価 / 仕上がり重量) * 100 : null;
  const 原価率 = 売価 && 売価 > 0 && perPiece !== null ? (perPiece / 売価) * 100 : null;
  const 一人あたり = 人数 && 人数 > 0 && perPiece !== null ? perPiece / 人数 : null;

  // 衣は、まぶし粉の全量ではなく実付着量でも並べる。
  const 衣試算 = 衣原価 > 0
    ? COATING_RATIOS.map((r) => {
        const total = 衣以外 + 衣原価 * r;
        return {
          付着率: r,
          仕込み原価: total,
          '1個原価': 個数 && 個数 > 0 ? total / 個数 : null,
        };
      })
    : [];

  // 主材料の合計重量 × 歩留まり。仕上がり重量を手で量る前の目安として出す。
  // 衣や調味料は製品に残らないので合計にはかけない。
  const 主材料 = rows.filter((r) => r.line.区分 === '主材料');
  const 主材料重量 = 主材料.reduce((a, r) => a + (num(r.line.使用量) ?? 0), 0);
  const 主材料歩留 = 主材料.length
    ? 主材料.reduce((a, r) => {
        const item = r.line.itemId ? itemsById.get(r.line.itemId) : null;
        return a + (num(r.line.歩留まり) ?? num(item?.歩留まり) ?? 1.0);
      }, 0) / 主材料.length
    : null;
  const 仕上がり目安 = 主材料重量 > 0 && 主材料歩留 ? 主材料重量 * 主材料歩留 : null;

  return {
    rows,
    仕込み原価,
    衣原価,
    '1個原価': perPiece,
    '100g原価': per100g,
    原価率,
    一人あたり,
    衣試算,
    仕上がり目安,
    未確定件数: 未確定.length,
    未登録: rows.filter((r) => r.照合 === '未登録').map((r) => r.line.食材名 || '(名称なし)'),
  };
}

/** 同名重複の検出。VLOOKUPは上の行しか拾わないため、仕入先違いの同名は事故になる。 */
export function findDuplicates(items) {
  const byName = new Map();
  for (const it of items) {
    const n = (it.食材名称 || '').trim();
    if (!n) continue;
    if (!byName.has(n)) byName.set(n, []);
    byName.get(n).push(it);
  }
  return [...byName.entries()]
    .filter(([, v]) => v.length > 1)
    .map(([name, v]) => ({
      name,
      count: v.length,
      仕入先: [...new Set(v.map((x) => x.仕入先).filter(Boolean))],
    }));
}
