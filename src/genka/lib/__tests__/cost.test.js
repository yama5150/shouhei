// node --test src/genka/lib/__tests__/
import test from 'node:test';
import assert from 'node:assert/strict';
import { unitPack, isCaseUnit, gramPrice } from '../units.js';
import { findAmount, parseCsv, convertRow, COL } from '../infomart.js';
import { calcRecipe, findDuplicates, itemUnitPrice } from '../cost.js';

const NEL = String.fromCharCode(0x85);

test('単位の正規化: 全角・異体字を吸収する', () => {
  for (const u of ['kg', 'ｋｇ', 'Kg', 'KG', 'Ｋｇ']) {
    assert.equal(unitPack(u).count, 1000, u);
  }
  for (const u of ['L', 'Ｌ', 'ℓ']) assert.equal(unitPack(u).count, 1000, u);
  assert.equal(unitPack('100g').count, 100);
  for (const u of ['個', '本', '枚', 'PC', '袋', '尾', '丁', '玉', '束', '箱', 'CS', '肩', '杯', '缶', '瓶']) {
    assert.equal(unitPack(u).count, 1, u);
  }
});

test('表に無い単位は推定せず null', () => {
  assert.equal(unitPack('ケース入り'), null);
  assert.equal(unitPack(''), null);
  assert.equal(unitPack('謎単位'), null);
});

test('グラム単価 = 仕入単価 ÷ 入り数 ÷ 歩留まり', () => {
  assert.equal(gramPrice({ price: 3000, unit: 'kg' }), 3);
  // 歩留まり60%なら可食部のグラム単価は上がる
  assert.equal(gramPrice({ price: 3000, unit: 'kg', yieldRate: 0.6 }), 5);
  assert.equal(gramPrice({ price: 250, unit: '個' }), 250);
});

test('仕入単価が空欄の行は時価品。埋めない', () => {
  assert.equal(gramPrice({ price: '', unit: 'kg' }), null);
  assert.equal(gramPrice({ price: null, unit: 'kg' }), null);
});

test('入り数が分からなければ未換算のまま', () => {
  assert.equal(gramPrice({ price: 1000, unit: '謎単位' }), null);
});

// --- スキルの「よくある落とし穴」 ---

test('サイズ等級のLを容量のLと誤読しない', () => {
  assert.equal(findAmount('大根 2L'), null);
  assert.equal(findAmount('軟白ネギ 3L'), null);
  // 小数点付き・ml/cc表記だけ容量として拾う
  assert.deepEqual(findAmount('1.8L'), { amount: 1800, kind: 'volume' });
  assert.deepEqual(findAmount('500ml'), { amount: 500, kind: 'volume' });
  assert.deepEqual(findAmount('180cc'), { amount: 180, kind: 'volume' });
});

test('有頭20-30 2kg は 2kg入りとして読む(サイズ等級に釣られない)', () => {
  assert.deepEqual(findAmount('有頭20-30 2kg'), { amount: 2000, kind: 'weight' });
});

test('ケース入数の×Nは、単位がC/S・箱のときだけ掛ける', () => {
  const row = [];
  row[COL.商品名] = 'ちくわ';
  row[COL.規格] = '40g×50本';
  row[COL.単価] = '2000';

  row[COL.単位] = '本';
  const 本 = convertRow(row);
  assert.equal(本.入り数, 40, '単位が本なら1本=40g。掛けると50倍ずれる');
  assert.ok(本.warnings.some((w) => w.includes('掛けない')));

  row[COL.単位] = 'C/S';
  const cs = convertRow(row);
  assert.equal(cs.入り数, 2000, '単位がC/Sならケース全量 40g×50');
});

test('isCaseUnit は C/S・箱・ケース・函 のみ', () => {
  for (const u of ['C/S', 'CS', 'ケース', '箱', '函']) assert.equal(isCaseUnit(u), true, u);
  for (const u of ['本', '個', '枚', 'kg']) assert.equal(isCaseUnit(u), false, u);
});

test('単位kgならそのまま円/kg。規格は見に行かない', () => {
  const row = [];
  row[COL.商品名] = '豚バラ 500g';
  row[COL.規格] = '500g';
  row[COL.単位] = 'kg';
  row[COL.単価] = '1200';
  const r = convertRow(row);
  assert.equal(r.入り数, 1000);
  assert.equal(r.換算元, '単位kg');
});

test('商品名から読んだ内容量は目視確認の警告を付ける', () => {
  const row = [];
  row[COL.商品名] = '醤油 1.8L';
  row[COL.規格] = '';
  row[COL.単位] = '本';
  row[COL.単価] = '900';
  const r = convertRow(row);
  assert.equal(r.入り数, 1800);
  assert.equal(r.換算元, '商品名');
  assert.ok(r.warnings.some((w) => w.includes('目視確認')));
});

test('内容量が読めなければ未換算。歩留まりは勝手に推定しない', () => {
  const row = [];
  row[COL.商品名] = '謎の惣菜';
  row[COL.単位] = '';
  row[COL.単価] = '500';
  const r = convertRow(row);
  assert.equal(r.入り数, null);
  assert.equal(r.歩留まり, 1.0);
  assert.ok(r.warnings.some((w) => w.includes('未換算')));
});

test('CSVは CRLF と NEL の混在を両方行区切りとして読む', () => {
  const rows = parseCsv('a,b\r\nc,d' + NEL + 'e,f\n');
  assert.deepEqual(rows, [['a', 'b'], ['c', 'd'], ['e', 'f']]);
});

test('引用符の中のカンマと改行は壊さない', () => {
  const rows = parseCsv('"あ,い","う\r\nえ"\r\n');
  assert.deepEqual(rows, [['あ,い', 'う\r\nえ']]);
});

// --- 原価計算 ---

const master = new Map([
  ['m1', { 食材名称: '真鱈フィーレ', 仕入単価: 1400, 単位: 'kg', 入り数: 1000, 歩留まり: 0.7 }],
  ['m2', { 食材名称: '片栗粉', 仕入単価: 300, 単位: 'kg', 入り数: 1000, 歩留まり: 1.0 }],
  ['m3', { 食材名称: '本鮪(時価)', 仕入単価: null, 単位: 'kg', 入り数: 1000, 歩留まり: 1.0 }],
]);

test('マスターのグラム単価に歩留まりが乗る', () => {
  assert.equal(itemUnitPrice(master.get('m1')), 2); // 1400/1000/0.7
  assert.equal(itemUnitPrice(master.get('m3')), null); // 時価品
});

test('仕込み単位で 1個 / 100g / 原価率 を出す', () => {
  const r = calcRecipe({
    lines: [
      { itemId: 'm1', 食材名: '真鱈', 使用量: 2000, 区分: '主材料' },
      { itemId: 'm2', 食材名: '片栗粉', 使用量: 200, 区分: '衣' },
    ],
    仕上がり重量: 1500,
    個数: 30,
    売価: 380,
  }, master);

  assert.equal(r.仕込み原価, 2000 * 2 + 200 * 0.3); // 4060
  assert.equal(r['1個原価'], 4060 / 30);
  assert.equal(r['100g原価'], (4060 / 1500) * 100);
  assert.ok(Math.abs(r.原価率 - (4060 / 30 / 380) * 100) < 1e-9);
});

test('手入力単価はマスター参照より優先する(時価品の当日単価)', () => {
  const r = calcRecipe({
    lines: [{ itemId: 'm3', 食材名: '本鮪', 使用量: 500, 手入力単価: 12, 区分: '主材料' }],
    個数: 10,
  }, master);
  assert.equal(r.仕込み原価, 6000);
  assert.equal(r.rows[0].源, '手入力');
});

test('時価品を手入力せずに置くと未確定として残る。0で埋めない', () => {
  const r = calcRecipe({
    lines: [{ itemId: 'm3', 食材名: '本鮪', 使用量: 500, 区分: '主材料' }],
    個数: 10,
  }, master);
  assert.equal(r.rows[0].cost, null);
  assert.equal(r.未確定件数, 1);
});

test('衣は実付着量3〜7割の試算も並べる', () => {
  const r = calcRecipe({
    lines: [
      { itemId: 'm1', 食材名: '真鱈', 使用量: 2000, 区分: '主材料' },
      { itemId: 'm2', 食材名: '片栗粉', 使用量: 200, 区分: '衣' },
    ],
    個数: 30,
  }, master);
  assert.deepEqual(r.衣試算.map((x) => x.付着率), [1.0, 0.7, 0.5, 0.3]);
  assert.equal(r.衣試算[0].仕込み原価, 4060);
  assert.equal(r.衣試算[2].仕込み原価, 4000 + 60 * 0.5); // 付着5割
});

test('バイキングは一人あたりで見る', () => {
  const r = calcRecipe({
    lines: [{ itemId: 'm1', 食材名: '真鱈', 使用量: 1000, 区分: '主材料' }],
    個数: 1,
    取り分け人数: 10,
  }, master);
  assert.equal(r['1個原価'], 2000);
  assert.equal(r.一人あたり, 200);
});

test('歩留まりは主材料にかける。衣や調味料の使用量には乗せない', () => {
  const r = calcRecipe({
    lines: [
      { itemId: 'm1', 食材名: '真鱈', 使用量: 2000, 区分: '主材料', 歩留まり: 0.7 },
      { itemId: 'm2', 食材名: '片栗粉', 使用量: 200, 区分: '衣' },
    ],
  }, master);
  assert.equal(r.仕上がり目安, 1400); // 2000×0.7。衣の200gは足さない
});

test('マスターに無い食材は未登録として可視化する', () => {
  const r = calcRecipe({
    lines: [{ itemId: null, 食材名: 'サーモン', 使用量: 100, 区分: '主材料' }],
  }, master);
  assert.deepEqual(r.未登録, ['サーモン']);
});

test('同名で仕入先違いを重複として洗い出す', () => {
  const dup = findDuplicates([
    { 食材名称: '宗八カレイ', 仕入先: 'ヤマヨ' },
    { 食材名称: '宗八カレイ', 仕入先: '知床' },
    { 食材名称: '大根', 仕入先: '青果' },
  ]);
  assert.equal(dup.length, 1);
  assert.equal(dup[0].name, '宗八カレイ');
  assert.deepEqual(dup[0].仕入先, ['ヤマヨ', '知床']);
});
