import test from 'node:test';
import assert from 'node:assert/strict';
import { yieldRate, summarize, byHandler, isValidLog } from '../yields.js';
import { parseReceiptText, matchToMaster, applyReceipt } from '../receipt.js';

// --- 歩留まり記録 ---

test('歩留まり = 可食部 ÷ ラウンド', () => {
  assert.equal(yieldRate(30000, 18000).rate, 0.6);
  assert.equal(yieldRate('30', '15').rate, 0.5);
});

test('記録ミスは通さない。推測で直さない', () => {
  assert.ok(yieldRate(0, 100).error);
  assert.ok(yieldRate(100, 0).error);
  assert.ok(yieldRate(100, 120).error.includes('超えて'), '可食部がラウンドを超えたら弾く');
  assert.ok(yieldRate('', 100).error);
  assert.ok(yieldRate(100, null).error);
});

test('isValidLog は歩留まりが出せる記録だけ通す', () => {
  assert.equal(isValidLog({ ラウンド重量: 30000, 可食部重量: 18000 }), true);
  assert.equal(isValidLog({ ラウンド重量: 30000, 可食部重量: '' }), false);
});

const logs = [
  { id: '1', 日付: '2026-09-01', 食材名: '本鮪', 担当者: '山田', ラウンド重量: 30000, 可食部重量: 18000 },
  { id: '2', 日付: '2026-09-05', 食材名: '本鮪', 担当者: '佐藤', ラウンド重量: 28000, 可食部重量: 15400 },
  { id: '3', 日付: '2026-09-07', 食材名: '本鮪', 担当者: '山田', ラウンド重量: 32000, 可食部重量: 20800 },
  { id: '4', 日付: '2026-09-02', 食材名: '真鱈', 担当者: '山田', ラウンド重量: 5000, 可食部重量: 3500 },
  { id: '5', 日付: '2026-09-03', 食材名: '本鮪', 担当者: '山田', ラウンド重量: 0, 可食部重量: 100 }, // 記録ミス
];

test('食材ごとに件数・平均・最小最大・最新を出す', () => {
  const s = summarize(logs);
  const maguro = s.find((x) => x.食材名 === '本鮪');
  assert.equal(maguro.件数, 3, '記録ミスの1件は数えない');
  assert.ok(Math.abs(maguro.平均 - (0.6 + 0.55 + 0.65) / 3) < 1e-9);
  assert.equal(maguro.最小, 0.55);
  assert.equal(maguro.最大, 0.65);
  assert.equal(maguro.最新, 0.65, '日付が一番新しい記録');
});

test('件数の多い順に並ぶ', () => {
  const s = summarize(logs);
  assert.equal(s[0].食材名, '本鮪');
  assert.equal(s[1].食材名, '真鱈');
});

test('担当者ごとに分けて見られる(卸し手で歩留まりが変わるため)', () => {
  const h = byHandler(logs.filter((l) => l.食材名 === '本鮪'));
  const yamada = h.find((x) => x.担当者 === '山田');
  const sato = h.find((x) => x.担当者 === '佐藤');
  assert.equal(yamada.件数, 2);
  assert.ok(Math.abs(yamada.平均 - 0.625) < 1e-9);
  assert.equal(sato.件数, 1);
});

test('担当者が空欄でも記録なしとして残す', () => {
  const h = byHandler([{ 食材名: '本鮪', 担当者: '', ラウンド重量: 100, 可食部重量: 60 }]);
  assert.equal(h[0].担当者, '(記録なし)');
});

// --- 納品書の取り込み ---

test('タブ区切りの 品名/数量/単価 を読む', () => {
  const r = parseReceiptText('真鱈フィーレ\t2\t1400');
  assert.equal(r[0].ok, true);
  assert.equal(r[0].品名, '真鱈フィーレ');
  assert.equal(r[0].数量, 2);
  assert.equal(r[0].単価, 1400);
});

test('カンマ区切りとスペース区切りも読む', () => {
  assert.equal(parseReceiptText('本鮪,1,12000')[0].単価, 12000);
  assert.equal(parseReceiptText('大根 3 128')[0].単価, 128);
});

test('全角数字・カンマ・円記号を吸収する', () => {
  const r = parseReceiptText('宗八カレイ　２　１，４００円');
  assert.equal(r[0].ok, true);
  assert.equal(r[0].数量, 2);
  assert.equal(r[0].単価, 1400);
});

test('数値が3つ以上あるときは 数量×単価≒金額 で確かめる', () => {
  // 品名 数量 単価 金額
  const r = parseReceiptText('真鱈フィーレ\t2\t1400\t2800');
  assert.equal(r[0].ok, true);
  assert.equal(r[0].単価, 1400);
  assert.equal(r[0].金額, 2800);
  assert.ok(r[0].note.includes('確認済み'));
});

test('検算が合わない行は推測せず、確認事項として返す', () => {
  const r = parseReceiptText('謎の品\t3\t500\t9999');
  assert.equal(r[0].ok, false);
  assert.ok(r[0].reason.includes('決められません'));
  assert.equal(r[0].単価, undefined, '単価を勝手に決めない');
});

test('単価しか読めない行は数量をnullのまま残す(0で埋めない)', () => {
  const r = parseReceiptText('本鮪 12000');
  assert.equal(r[0].ok, true);
  assert.equal(r[0].数量, null);
  assert.equal(r[0].単価, 12000);
});

test('見出し行と読めない行は取り込まない', () => {
  const r = parseReceiptText('品名\t数量\t単価\n真鱈\t2\t1400\n\n意味のない行');
  assert.equal(r[0].ok, false);
  assert.equal(r[0].header, true);
  assert.equal(r[1].ok, true);
  assert.equal(r[2].ok, false);
});

test('先頭が数値の行は品名なしとして弾く', () => {
  assert.equal(parseReceiptText('1400 2 真鱈')[0].ok, false);
});

// --- マスターとの突き合わせ ---

const master = [
  { id: 'm1', 食材名称: '真鱈フィーレ', 仕入単価: 1200 },
  { id: 'm2', 食材名称: '宗八カレイ(ヤマヨ)', 仕入単価: 900 },
  { id: 'm3', 食材名称: '宗八カレイ(知床)', 仕入単価: 780 },
];

test('完全一致で当てる', () => {
  const [r] = matchToMaster(parseReceiptText('真鱈フィーレ\t2\t1400'), master);
  assert.equal(r.match.id, 'm1');
  assert.equal(r.matchKind, '完全一致');
});

test('候補が複数あるときは当てない。人に選ばせる', () => {
  const [r] = matchToMaster(parseReceiptText('宗八カレイ\t2\t850'), master);
  assert.equal(r.match, null);
  assert.ok(r.matchNote.includes('候補が2件'));
});

test('マスターに無い品目はそう言う', () => {
  const [r] = matchToMaster(parseReceiptText('存在しない魚\t1\t100'), master);
  assert.equal(r.match, null);
  assert.equal(r.matchNote, 'マスターに無い品目');
});

test('適用は仕入単価と更新日だけ。入り数や歩留まりは触らない', () => {
  const items = [{ id: 'm1', 食材名称: '真鱈フィーレ', 仕入単価: 1200, 入り数: 1000, 歩留まり: 0.7 }];
  const { items: next, applied } = applyReceipt(items, [{ itemId: 'm1', 単価: 1400 }], '2026-09-09');
  assert.equal(applied, 1);
  assert.equal(next[0].仕入単価, 1400);
  assert.equal(next[0].更新日, '2026-09-09');
  assert.equal(next[0].入り数, 1000, '入り数は触らない');
  assert.equal(next[0].歩留まり, 0.7, '歩留まりは触らない');
  assert.equal(items[0].仕入単価, 1200, '入力を破壊していない');
});

test('同じ単価なら適用件数に数えない', () => {
  const items = [{ id: 'm1', 仕入単価: 1400 }];
  assert.equal(applyReceipt(items, [{ itemId: 'm1', 単価: 1400 }]).applied, 0);
});

test('照合できていない行は書き込まない', () => {
  const items = [{ id: 'm1', 仕入単価: 1200 }];
  const { applied } = applyReceipt(items, [{ itemId: null, 単価: 9999 }]);
  assert.equal(applied, 0);
});
