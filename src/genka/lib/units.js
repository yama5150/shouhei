// 単位の正規化とグラム単価の算出。
//
// スキル(susudepa-cost)の単位表に忠実に実装する。
// 表に無い単位は「分からない」を返す。勝手に推定して入り数を埋めない。

/** 全角・互換文字を潰してから比較する。'ｋｇ'→'kg', 'Ｌ'→'L', 'ℓ'→'l' になる。 */
export const nfkc = (s) => (s == null ? '' : String(s).normalize('NFKC'));

/** 比較用のキー。NFKC + 小文字化 + 空白除去。 */
const key = (s) => nfkc(s).toLowerCase().replace(/\s+/g, '');

// 入り数 = その仕入単価が何グラム(ml/個)分の値段か。
// kg → 1000 で円/g、L → 1000 で円/ml、個数系 → 1 で円/個。
const UNIT_TABLE = [
  { match: ['kg', 'キロ'], count: 1000, kind: 'weight' },
  { match: ['100g'], count: 100, kind: 'weight' },
  { match: ['g', 'グラム'], count: 1, kind: 'weight' },
  { match: ['l', 'リットル'], count: 1000, kind: 'volume' },
  { match: ['ml', 'cc'], count: 1, kind: 'volume' },
  // 個数系。1個(本/枚…)いくら、なので入り数は 1。
  {
    match: ['個', '本', '枚', 'pc', '袋', '尾', '丁', '玉', '束', '箱', 'cs', 'c/s', '肩', '杯', '缶', '瓶', 'ケース', '函'],
    count: 1,
    kind: 'piece',
  },
];

/**
 * 単位表記から入り数を引く。
 * @returns {{count:number, kind:'weight'|'volume'|'piece'}|null} 表に無ければ null（未換算）
 */
export function unitPack(unit) {
  const k = key(unit);
  if (!k) return null;
  for (const row of UNIT_TABLE) {
    if (row.match.includes(k)) return { count: row.count, kind: row.kind };
  }
  return null;
}

/** ケース入数の ×N を掛けてよい単位か。C/S・箱・ケース・函 のときだけ true。 */
export function isCaseUnit(unit) {
  const k = key(unit);
  return ['cs', 'c/s', 'ケース', '箱', '函'].includes(k);
}

/** 数値として読めれば数値を、読めなければ null を返す（空欄＝時価品を潰さない）。 */
export function num(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  const s = nfkc(v).replace(/[,\s¥￥円]/g, '');
  if (s === '') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/**
 * グラム単価 = 仕入単価 ÷ 入り数 ÷ 歩留まり
 *
 * 歩留まりは比率(1.0=100%)で持つ。列見出しは「歩留まり(%)」だが、
 * アセット.xlsx の既存式 =D/F/G が G=1.0 前提なので比率で揃える。
 *
 * 仕入単価が空欄の行は時価品。null を返し、呼び出し側は空欄のまま残す。
 * @returns {number|null}
 */
export function gramPrice({ price, unit, packCount, yieldRate }) {
  const p = num(price);
  if (p === null) return null; // 時価品。埋めない
  const count = num(packCount) ?? unitPack(unit)?.count ?? null;
  if (count === null || count <= 0) return null; // 入り数が分からない
  const y = num(yieldRate) ?? 1.0; // 既定は 1.0。実測が出た品目だけ上書きする
  if (y <= 0) return null;
  return p / count / y;
}
