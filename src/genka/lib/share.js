// 出力の使い分け。
//  - 社内LINE共有 → プレーンテキスト。表組みは使わない。■で節、・で項目
//  - 会話での確認   → markdown表
//  - 全商品の比較   → CSV
// 現場向け簡潔版と、原価表つき詳細版の2パターンを出す。

const r0 = (n) => (n === null || n === undefined ? null : Math.round(n));
const yen = (n) => (n === null || n === undefined ? '—' : Math.round(n).toLocaleString() + '円');
const yen1 = (n) => (n === null || n === undefined ? '—' : (Math.round(n * 10) / 10).toLocaleString() + '円');
const pct = (n) => (n === null || n === undefined ? '—' : (Math.round(n * 10) / 10) + '%');

/** 「1個 約71円 ／ 100g 約197円」形式のサマリー行。 */
function summaryLine(calc) {
  const parts = [];
  if (calc['1個原価'] !== null) parts.push('1個 約' + r0(calc['1個原価']) + '円');
  if (calc['100g原価'] !== null) parts.push('100g 約' + r0(calc['100g原価']) + '円');
  if (calc.一人あたり !== null) parts.push('1人あたり 約' + r0(calc.一人あたり) + '円');
  return parts.join(' ／ ');
}

/** 現場向け簡潔版。キッチンのグループに投げるだけならこちら。 */
export function lineTextSimple(recipe, calc) {
  const L = [];
  L.push('■ ' + (recipe.料理名 || '(名称未設定)'));
  if (recipe.仕込み単位) L.push('・仕込み ' + recipe.仕込み単位);
  L.push('・1仕込み原価 ' + yen(calc.仕込み原価));
  const s = summaryLine(calc);
  if (s) L.push('・' + s);
  if (calc.原価率 !== null) L.push('・原価率 ' + pct(calc.原価率) + '（売価 ' + yen(recipe.売価) + '）');
  if (calc.未確定件数 > 0) L.push('※ 時価品・未登録が' + calc.未確定件数 + '件。当日単価を入れると確定します');
  return L.join('\n');
}

/** 新人に渡す詳細版。原価表つき。 */
export function lineTextDetail(recipe, calc) {
  const L = [];
  L.push('■ ' + (recipe.料理名 || '(名称未設定)') + ' 原価');
  if (recipe.仕込み単位) L.push('仕込み単位：' + recipe.仕込み単位);
  if (recipe.仕上がり重量) L.push('仕上がり：' + recipe.仕上がり重量 + 'g / ' + (recipe.個数 || '—') + '個');
  L.push('');
  L.push('■ 内訳');
  for (const row of calc.rows) {
    const name = row.line.食材名 || '(名称なし)';
    const qty = row.line.使用量 ? row.line.使用量 + (row.line.単位 || 'g') : '—';
    if (row.cost === null) {
      L.push('・' + name + '　' + qty + '　→ 単価未確定');
    } else {
      L.push('・' + name + '　' + qty + '　' + yen1(row.unitPrice) + '/' + (row.line.単位 || 'g') + '　= ' + yen(row.cost));
    }
  }
  L.push('');
  L.push('■ まとめ');
  L.push('・1仕込み ' + yen(calc.仕込み原価));
  const s = summaryLine(calc);
  if (s) L.push('・' + s);
  if (calc.原価率 !== null) L.push('・原価率 ' + pct(calc.原価率));
  if (calc.衣試算.length) {
    L.push('');
    L.push('■ 衣の付着率ちがい');
    for (const t of calc.衣試算) {
      L.push('・付着' + Math.round(t.付着率 * 100) + '%　1仕込み ' + yen(t.仕込み原価)
        + (t['1個原価'] !== null ? '　1個 約' + r0(t['1個原価']) + '円' : ''));
    }
  }
  if (calc.未登録.length) {
    L.push('');
    L.push('■ 要確認');
    for (const n of calc.未登録) L.push('・' + n + ' がマスター未登録');
  }
  L.push('');
  L.push('※ 仕入単価が変わった場合は原価表を更新すること');
  return L.join('\n');
}

/** 会話での確認用。markdown表。 */
export function markdownTable(recipe, calc) {
  const L = [];
  L.push('**' + (recipe.料理名 || '(名称未設定)') + '**'
    + (recipe.仕込み単位 ? '（' + recipe.仕込み単位 + '）' : ''));
  L.push('');
  L.push('| 材料 | 使用量 | 単価 | 原価 |');
  L.push('|---|---:|---:|---:|');
  for (const row of calc.rows) {
    L.push('| ' + (row.line.食材名 || '(名称なし)')
      + ' | ' + (row.line.使用量 ?? '') + (row.line.単位 || 'g')
      + ' | ' + (row.unitPrice === null ? '未確定' : yen1(row.unitPrice))
      + ' | ' + (row.cost === null ? '—' : yen(row.cost)) + ' |');
  }
  L.push('| **合計** | | | **' + yen(calc.仕込み原価) + '** |');
  L.push('');
  const s = summaryLine(calc);
  if (s) L.push(s + (calc.原価率 !== null ? ' ／ 原価率 ' + pct(calc.原価率) : ''));
  return L.join('\n');
}

const csvCell = (v) => {
  const s = v === null || v === undefined ? '' : String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
};
const csvRows = (rows) => rows.map((r) => r.map(csvCell).join(',')).join('\r\n');

/** 全商品の原価一覧。Excelで開く前提なのでBOM付きUTF-8。 */
export function recipesCsv(list) {
  const head = ['料理名', 'カテゴリ', '仕込み単位', '1仕込み原価', '1個原価', '100g原価', '売価', '原価率%', '1人あたり', '未確定件数'];
  const body = list.map(({ recipe, calc }) => [
    recipe.料理名, recipe.カテゴリ, recipe.仕込み単位,
    r0(calc.仕込み原価), r0(calc['1個原価']), r0(calc['100g原価']),
    recipe.売価, calc.原価率 === null ? '' : Math.round(calc.原価率 * 10) / 10,
    r0(calc.一人あたり), calc.未確定件数,
  ]);
  return csvRows([head, ...body]);
}

/** 単価マスターのCSV。列はスキルの固定順。 */
export function masterCsv(items) {
  const head = ['分類', '食材名称', '仕入先', '仕入単価', '単位', '入り数(gor個)', '歩留まり(%)', 'グラム単価(円)', '換算元'];
  const body = items.map((it) => {
    const p = it.仕入単価, c = it.入り数, y = it.歩留まり ?? 1.0;
    const g = p === null || p === undefined || !c || !y ? '' : Math.round((p / c / y) * 1000) / 1000;
    return [it.分類, it.食材名称, it.仕入先, it.仕入単価 ?? '', it.単位, it.入り数 ?? '', y, g, it.換算元 ?? ''];
  });
  return csvRows([head, ...body]);
}

export const CSV_BOM = '\uFEFF';
