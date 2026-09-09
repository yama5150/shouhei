// インフォマート マイカタログCSV の読み込みと、円/g への換算。
//
// 文字コードは cp932、1行目タイトル・2行目ヘッダ・3行目からデータ。
// 換算できるのは概ね7割。残りは規格欄が空で内容量が判断できないもので、
// 未換算のまま残す。全件を埋めようとしない。

import { nfkc, num, unitPack, isCaseUnit } from './units.js';

// 列インデックス(0始まり)。
export const COL = {
  大分類: 8, 中分類: 9, 小分類: 10, 商品コード: 11,
  商品名: 12, 規格: 13, 入数: 14, 単位: 16, 単価: 17, 取引先名: 23,
};

const W_RE = /(\d+(?:\.\d+)?)\s*(kg|g|グラム|キロ)(?![a-zA-Z])/i;
const V_RE = /(\d+(?:\.\d+)?)\s*(ml|cc|リットル)/i;
// 1.8L のように小数点付きのときだけ容量とみなす。「大根 2L」「軟白ネギ 3L」は等級なので拾わない。
// NFKC で 'ℓ' が 'l' になるため /i を付けて小文字も拾う（小数点の条件は残す）。
const VL_RE = /(\d+\.\d+)\s*L(?![a-zA-Z])/i;
const MULT = /[×xX*]\s*(\d+(?:\.\d+)?)/;
// 「有頭20-30」のようなサイズ等級。内容量ではないので換算には使わないが、警告は出す。
const GRADE_RE = /\d+\s*[-〜~]\s*\d+/;

// U+0085 NEL。インフォマートの書き出しは CRLF と NEL が混在する。
const NEL = String.fromCharCode(0x85);

/**
 * CRLF / LF / CR / NEL 混在の CSV を行×列に分解する。
 * 引用符の中の改行は field の一部として残す。
 */
export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; }
      } else field += c;
      continue;
    }
    if (c === '"') { inQuotes = true; continue; }
    if (c === ',') { row.push(field); field = ''; continue; }
    if (c === '\r' || c === '\n' || c === NEL) {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      rows.push(row); row = [];
      continue;
    }
    field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}

/**
 * 文字列から内容量(g または ml)を1つ読む。重さを先に、無ければ容量を見る。
 * @returns {{amount:number, kind:'weight'|'volume'}|null}
 */
export function findAmount(text) {
  const s = nfkc(text);
  if (!s) return null;
  const w = W_RE.exec(s);
  if (w) {
    const v = Number(w[1]);
    const u = w[2].toLowerCase();
    return { amount: u === 'kg' || u === 'キロ' ? v * 1000 : v, kind: 'weight' };
  }
  const vl = VL_RE.exec(s);
  if (vl) return { amount: Number(vl[1]) * 1000, kind: 'volume' };
  const v = V_RE.exec(s);
  if (v) {
    const u = v[2].toLowerCase();
    return { amount: u === 'リットル' ? Number(v[1]) * 1000 : Number(v[1]), kind: 'volume' };
  }
  return null;
}

/**
 * 1行を単価マスターの1件に変換する。
 * 換算元(単位kg / 規格 / 商品名)を残す。商品名由来は目視確認の対象。
 */
export function convertRow(cells) {
  const get = (i) => nfkc(cells[i] ?? '').trim();
  const 商品名 = get(COL.商品名);
  const 規格 = get(COL.規格);
  const 単位 = get(COL.単位);
  const 単価 = num(get(COL.単価));
  const warnings = [];

  let packCount = null;   // 入り数
  let packUnit = null;    // 入り数の単位 g / ml / 個
  let source = null;      // 換算元

  const pack = unitPack(単位);
  if (pack && pack.kind !== 'piece') {
    // 単位そのものが kg/L/100g/g/ml なら、単価はその単位あたりの値段。
    packCount = pack.count;
    packUnit = pack.kind === 'volume' ? 'ml' : 'g';
    source = '単位' + 単位;
  } else {
    // 規格 → 商品名 の順に内容量を探す。
    for (const [label, text] of [['規格', 規格], ['商品名', 商品名]]) {
      const found = findAmount(text);
      if (!found) continue;
      packCount = found.amount;
      packUnit = found.kind === 'volume' ? 'ml' : 'g';
      source = label;
      // ×N はケース仕様の記述。単位が C/S・箱・ケース・函 のときだけ掛ける。
      // 「本」「個」「枚」で掛けると10倍以上ずれる。
      const m = MULT.exec(nfkc(text));
      if (m) {
        if (isCaseUnit(単位)) packCount *= Number(m[1]);
        else warnings.push('規格の×' + m[1] + 'は単位「' + 単位 + '」では掛けない(ケース仕様の記述)');
      }
      if (label === '商品名') warnings.push('商品名から内容量を読んだ。目視確認の対象');
      break;
    }
    // 内容量が読めず、単位が個数系なら 1個いくらとして扱う。
    if (packCount === null && pack && pack.kind === 'piece') {
      packCount = 1;
      packUnit = '個';
      source = '単位' + 単位;
    }
  }

  if (GRADE_RE.test(規格) || GRADE_RE.test(商品名)) {
    warnings.push('サイズ等級の表記あり。1尾/1個あたりを出すときは入数を要確認');
  }
  if (単価 === 0) warnings.push('単価0。マイカタログの登録漏れの可能性');
  if (単価 === null) warnings.push('単価が空欄。時価品として空欄のまま残す');
  if (packCount === null) warnings.push('内容量が読めず未換算。使う品目だけ手で入れる');

  return {
    分類: [get(COL.大分類), get(COL.中分類), get(COL.小分類)].filter(Boolean).join(' / '),
    食材名称: 商品名,
    仕入先: get(COL.取引先名),
    商品コード: get(COL.商品コード),
    規格,
    仕入単価: 単価,
    単位,
    入り数: packCount,
    入り数単位: packUnit,
    歩留まり: 1.0, // 既定100%。実測が出た品目だけ上書きする
    換算元: source,
    warnings,
  };
}

/** CSV全体を単価マスター行の配列にする。 */
export function importInfomart(text) {
  const rows = parseCsv(text);
  const body = rows.slice(2).filter((r) => r.length > COL.単価 && nfkc(r[COL.商品名] ?? '').trim() !== '');
  const items = body.map(convertRow);
  return {
    items,
    stats: {
      total: items.length,
      converted: items.filter((i) => i.入り数 !== null).length,
      priced: items.filter((i) => i.仕入単価 !== null).length,
    },
  };
}

/** cp932 のバイト列を文字列に戻す。 */
export function decodeCp932(buffer) {
  return new TextDecoder('shift_jis').decode(buffer);
}
