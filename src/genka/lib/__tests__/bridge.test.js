import test from 'node:test';
import assert from 'node:assert/strict';
import { readLossMenu, autoMatch, applyPlan, flattenMenu, normName } from '../bridge.js';

const menu = () => [
  { id: 'c-gyu', category: '牛', defaultUnit: '皿', items: [
    { id: 'i-牛カルビ', name: '牛カルビ', unit: '皿', cost: 0, defaultQty: 1 },
    { id: 'i-牛タン', name: '牛タン', unit: '皿', cost: 250, defaultQty: 1 },
  ] },
  { id: 'c-tori', category: '鶏', defaultUnit: '皿', items: [
    { id: 'i-鶏もも', name: '鶏もも', unit: '皿', cost: 0, defaultQty: 1 },
  ] },
];

const fakeStorage = (obj) => ({ getItem: (k) => (k in obj ? obj[k] : null) });

test('bl_menu が無ければ理由を返す', () => {
  const r = readLossMenu(fakeStorage({}));
  assert.ok(r.error.includes('見つかりません'));
});

test('bl_menu_ver が無いときは書かせない(次回起動で初期化され消えるため)', () => {
  const r = readLossMenu(fakeStorage({ bl_menu: '[]' }));
  assert.ok(r.error.includes('初期化されていません'));
});

test('揃っていれば読める', () => {
  const r = readLossMenu(fakeStorage({ bl_menu: JSON.stringify(menu()), bl_menu_ver: '4' }));
  assert.equal(r.error, undefined);
  assert.equal(r.menu.length, 2);
  assert.equal(r.ver, '4');
});

test('壊れたJSONで落ちない', () => {
  const r = readLossMenu(fakeStorage({ bl_menu: '{壊れ', bl_menu_ver: '4' }));
  assert.ok(r.error.includes('壊れて'));
});

test('名寄せは全角半角と空白の揺れだけ潰す', () => {
  assert.equal(normName('牛カルビ'), normName('牛 カルビ'));
  assert.equal(normName('ﾎﾙﾓﾝ'), normName('ホルモン'));
  assert.notEqual(normName('牛カルビ'), normName('豚カルビ'));
});

test('完全一致で当てる', () => {
  const m = autoMatch('牛タン', menu());
  assert.equal(m.item.id, 'i-牛タン');
  assert.equal(m.categoryId, 'c-gyu');
});

test('候補が絞れないときは当てない', () => {
  assert.equal(autoMatch('存在しない料理', menu()), null);
  assert.equal(autoMatch('', menu()), null);
});

test('部分一致は1件に絞れるときだけ当てる', () => {
  assert.equal(autoMatch('牛タン塩', menu()).item.id, 'i-牛タン');
  // 「カルビ」は牛カルビ1件だけなので当たる
  assert.equal(autoMatch('カルビ', menu()).item.id, 'i-牛カルビ');
});

test('既存品目の原価を差し替える。元の配列は変えない', () => {
  const before = menu();
  const snapshot = JSON.stringify(before);
  const { menu: after, updated, added } = applyPlan(before, [
    { target: { categoryId: 'c-gyu', itemId: 'i-牛カルビ' }, cost: 133.4 },
  ]);
  assert.equal(updated, 1);
  assert.equal(added, 0);
  assert.equal(after[0].items[0].cost, 133); // 四捨五入
  assert.equal(JSON.stringify(before), snapshot, '入力を破壊していない');
});

test('原価以外のフィールドは触らない', () => {
  const { menu: after } = applyPlan(menu(), [
    { target: { categoryId: 'c-gyu', itemId: 'i-牛タン' }, cost: 300 },
  ]);
  const it = after[0].items[1];
  assert.equal(it.name, '牛タン');
  assert.equal(it.unit, '皿');
  assert.equal(it.defaultQty, 1);
  assert.equal(it.id, 'i-牛タン');
});

test('値が同じなら更新件数に数えない', () => {
  const { updated } = applyPlan(menu(), [
    { target: { categoryId: 'c-gyu', itemId: 'i-牛タン' }, cost: 250 },
  ]);
  assert.equal(updated, 0);
});

test('新規品目を足せる。idはロス管理側と衝突しない接頭辞', () => {
  const { menu: after, added } = applyPlan(menu(), [
    { target: { categoryId: 'c-tori', newName: '鶏ハラミ' }, cost: 180 },
  ]);
  assert.equal(added, 1);
  const it = after[1].items.at(-1);
  assert.equal(it.name, '鶏ハラミ');
  assert.equal(it.cost, 180);
  assert.equal(it.unit, '皿');
  assert.ok(it.id.startsWith('i-gk-'));
});

test('同名がすでにあれば新規追加しない', () => {
  const { menu: after, added } = applyPlan(menu(), [
    { target: { categoryId: 'c-gyu', newName: '牛 タン' }, cost: 999 },
  ]);
  assert.equal(added, 0);
  assert.equal(after[0].items.length, 2);
});

test('targetがnullの行は無視する', () => {
  const { updated, added } = applyPlan(menu(), [{ target: null, cost: 100 }]);
  assert.equal(updated + added, 0);
});

test('costがnullの行は書かない(未確定を0で埋めない)', () => {
  const { menu: after, updated } = applyPlan(menu(), [
    { target: { categoryId: 'c-gyu', itemId: 'i-牛タン' }, cost: null },
  ]);
  assert.equal(updated, 0);
  assert.equal(after[0].items[1].cost, 250, '元の値が残る');
});

test('flattenMenu はカテゴリ情報を保つ', () => {
  const f = flattenMenu(menu());
  assert.equal(f.length, 3);
  assert.equal(f[0].category, '牛');
});
