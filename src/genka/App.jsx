import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Calculator, Database, ListOrdered, Share2, Plus, Trash2, Search, Upload,
  Download, AlertTriangle, Copy, Check, X, ChevronDown, ChevronRight, Pencil,
  ArrowRightLeft, RotateCcw,
} from 'lucide-react';

import { unitPack, num } from './lib/units.js';
import { importInfomart, decodeCp932 } from './lib/infomart.js';
import { calcRecipe, itemUnitPrice, findDuplicates } from './lib/cost.js';
import { lineTextSimple, lineTextDetail, markdownTable, recipesCsv, masterCsv, CSV_BOM } from './lib/share.js';
import { readLossMenu, flattenMenu, autoMatch, applyPlan, LOSS_KEYS, BACKUP_KEY } from './lib/bridge.js';
import { load, save, newId } from './store.js';

// ==========================================
// 表示ヘルパー
// ==========================================
const yen = (n) => (n === null || n === undefined ? '—' : Math.round(n).toLocaleString() + '円');
const yen1 = (n) => (n === null || n === undefined ? '—' : (Math.round(n * 10) / 10).toLocaleString());
const pct = (n) => (n === null || n === undefined ? '—' : Math.round(n * 10) / 10 + '%');

const 区分候補 = ['主材料', '副材料', '衣', '調味料'];
const 区分色 = {
  主材料: 'bg-amber-100 text-amber-900',
  副材料: 'bg-slate-100 text-slate-700',
  衣: 'bg-orange-100 text-orange-800',
  調味料: 'bg-emerald-100 text-emerald-800',
};

// 原価率のしきい値。高いほど赤。看板商品は高くても残す判断があるので、色は警告どまりにする。
const rateColor = (r) =>
  r === null ? 'text-slate-400'
    : r >= 40 ? 'text-rose-600'
      : r >= 32 ? 'text-amber-600'
        : 'text-emerald-700';

const emptyRecipe = () => ({
  id: newId(),
  料理名: '',
  カテゴリ: '',
  仕込み単位: '',
  仕上がり重量: '',
  個数: '',
  売価: '',
  取り分け人数: '',
  メモ: '',
  lines: [],
});

const emptyLine = () => ({
  id: newId(), itemId: null, 食材名: '', 使用量: '', 単位: 'g',
  手入力単価: '', 区分: '副材料', 歩留まり: '', メモ: '',
});

// ==========================================
// 小さめの共通パーツ
// ==========================================
function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-medium text-slate-500 mb-1">{label}</span>
      {children}
      {hint && <span className="block text-[10px] text-slate-400 mt-0.5">{hint}</span>}
    </label>
  );
}

const inputCls =
  'w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm tabular ' +
  'focus:border-[#8C2E1B] focus:ring-1 focus:ring-[#8C2E1B] outline-none';

function CopyButton({ text, label = 'コピー' }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
        } catch {
          // クリップボードが使えない環境では選択してもらう
          const ta = document.createElement('textarea');
          ta.value = text; document.body.appendChild(ta); ta.select();
          try { document.execCommand('copy'); } catch { /* noop */ }
          document.body.removeChild(ta);
        }
        setDone(true); setTimeout(() => setDone(false), 1500);
      }}
      className="inline-flex items-center gap-1 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white active:bg-slate-700"
    >
      {done ? <Check size={13} /> : <Copy size={13} />}
      {done ? 'コピーしました' : label}
    </button>
  );
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ==========================================
// 食材ピッカー（マスターから引く）
// ==========================================
function ItemPicker({ items, onPick, onClose }) {
  const [q, setQ] = useState('');
  const hits = useMemo(() => {
    const s = q.trim();
    if (!s) return items.slice(0, 50);
    const lower = s.toLowerCase();
    return items
      .filter((it) => (it.食材名称 || '').toLowerCase().includes(lower)
        || (it.仕入先 || '').toLowerCase().includes(lower))
      .slice(0, 80);
  }, [q, items]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 p-3">
        <Search size={16} className="text-slate-400" />
        <input
          autoFocus value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="食材名・仕入先で検索"
          className="flex-1 text-sm outline-none"
        />
        <button onClick={onClose} className="rounded p-1 text-slate-400"><X size={18} /></button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {items.length === 0 && (
          <p className="p-6 text-center text-sm text-slate-400">
            単価マスターが空です。<br />「単価マスター」タブでCSVを取り込むか、手で登録してください。
          </p>
        )}
        {hits.map((it) => {
          const up = itemUnitPrice(it);
          return (
            <button
              key={it.id} onClick={() => onPick(it)}
              className="flex w-full items-center gap-2 border-b border-slate-100 px-3 py-2.5 text-left active:bg-amber-50"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-slate-800">{it.食材名称}</p>
                <p className="truncate text-[10px] text-slate-400">
                  {it.仕入先 || '仕入先なし'}
                  {it.規格 ? ' / ' + it.規格 : ''}
                  {it.単位 ? ' / ' + it.単位 : ''}
                </p>
              </div>
              <span className={'shrink-0 text-xs tabular ' + (up === null ? 'text-rose-500' : 'text-slate-700')}>
                {up === null ? '未確定' : yen1(up) + '円/' + (it.入り数単位 || 'g')}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ==========================================
// 原価計算タブ
// ==========================================
function CalcTab({ recipe, setRecipe, items, itemsById }) {
  const [picking, setPicking] = useState(null); // 行id
  const calc = useMemo(() => calcRecipe(recipe, itemsById), [recipe, itemsById]);

  const patch = (p) => setRecipe({ ...recipe, ...p });
  const patchLine = (id, p) =>
    setRecipe({ ...recipe, lines: recipe.lines.map((l) => (l.id === id ? { ...l, ...p } : l)) });
  const addLine = () => setRecipe({ ...recipe, lines: [...recipe.lines, emptyLine()] });
  const delLine = (id) => setRecipe({ ...recipe, lines: recipe.lines.filter((l) => l.id !== id) });

  return (
    <div className="space-y-4 p-3 pb-28">
      {/* 料理の枠 */}
      <section className="rounded-xl border border-slate-200 bg-white p-3">
        <input
          value={recipe.料理名} onChange={(e) => patch({ 料理名: e.target.value })}
          placeholder="料理名"
          className="w-full border-b border-slate-200 pb-2 text-lg font-semibold outline-none placeholder:text-slate-300 focus:border-[#8C2E1B]"
        />
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field label="カテゴリー">
            <input className={inputCls} value={recipe.カテゴリ}
              onChange={(e) => patch({ カテゴリ: e.target.value })} placeholder="浜焼き海鮮 など" />
          </Field>
          <Field label="仕込み単位" hint="1皿ではなく仕込み単位で">
            <input className={inputCls} value={recipe.仕込み単位}
              onChange={(e) => patch({ 仕込み単位: e.target.value })} placeholder="2kg仕込み" />
          </Field>
          <Field label="仕上がり重量 (g)"
            hint={calc.仕上がり目安 ? '主材料×歩留まりの目安 ' + Math.round(calc.仕上がり目安) + 'g' : '実測を入れる'}>
            <input className={inputCls} inputMode="decimal" value={recipe.仕上がり重量}
              onChange={(e) => patch({ 仕上がり重量: e.target.value })} placeholder="実測" />
          </Field>
          <Field label="個数 / 盛付数">
            <input className={inputCls} inputMode="decimal" value={recipe.個数}
              onChange={(e) => patch({ 個数: e.target.value })} placeholder="30" />
          </Field>
          <Field label="売価 (円)">
            <input className={inputCls} inputMode="decimal" value={recipe.売価}
              onChange={(e) => patch({ 売価: e.target.value })} placeholder="380" />
          </Field>
          <Field label="取り分け人数" hint="バイキングの大皿はここを入れる">
            <input className={inputCls} inputMode="decimal" value={recipe.取り分け人数}
              onChange={(e) => patch({ 取り分け人数: e.target.value })} placeholder="10" />
          </Field>
        </div>
      </section>

      {/* 材料 */}
      <section className="rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
          <h2 className="text-sm font-semibold text-slate-700">材料</h2>
          <button onClick={addLine}
            className="inline-flex items-center gap-1 rounded-lg bg-[#8C2E1B] px-2.5 py-1.5 text-xs font-medium text-white active:opacity-80">
            <Plus size={13} />行を足す
          </button>
        </div>

        {recipe.lines.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-slate-400">
            「行を足す」から材料を入れてください
          </p>
        )}

        {recipe.lines.map((line) => {
          const row = calc.rows.find((r) => r.line.id === line.id);
          const item = line.itemId ? itemsById.get(line.itemId) : null;
          return (
            <div key={line.id} className="border-b border-slate-100 px-3 py-2.5 last:border-0">
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <input
                      value={line.食材名} onChange={(e) => patchLine(line.id, { 食材名: e.target.value })}
                      placeholder="食材名"
                      className="min-w-0 flex-1 border-b border-transparent py-0.5 text-sm outline-none placeholder:text-slate-300 focus:border-slate-300"
                    />
                    <button onClick={() => setPicking(line.id)}
                      className="shrink-0 rounded border border-slate-200 px-1.5 py-1 text-[10px] text-slate-500 active:bg-slate-50">
                      マスターから
                    </button>
                  </div>
                  <p className="mt-0.5 text-[10px] text-slate-400">
                    {item
                      ? item.仕入先 + ' / ' + yen1(itemUnitPrice(item)) + '円/' + (item.入り数単位 || 'g')
                      : row?.照合 === '手入力' ? '手入力単価で計算中'
                        : <span className="text-rose-500">マスター未登録</span>}
                  </p>
                </div>
                <button onClick={() => delLine(line.id)} className="shrink-0 p-1 text-slate-300 active:text-rose-500">
                  <Trash2 size={15} />
                </button>
              </div>

              <div className="mt-2 grid grid-cols-4 gap-1.5">
                <input className={inputCls + ' text-right'} inputMode="decimal" value={line.使用量}
                  onChange={(e) => patchLine(line.id, { 使用量: e.target.value })} placeholder="使用量" />
                <select className={inputCls} value={line.単位}
                  onChange={(e) => patchLine(line.id, { 単位: e.target.value })}>
                  {['g', 'ml', '個', '本', '枚', '尾'].map((u) => <option key={u}>{u}</option>)}
                </select>
                <input className={inputCls + ' text-right'} inputMode="decimal" value={line.手入力単価}
                  onChange={(e) => patchLine(line.id, { 手入力単価: e.target.value })} placeholder="単価手入力" />
                <select className={inputCls} value={line.区分}
                  onChange={(e) => patchLine(line.id, { 区分: e.target.value })}>
                  {区分候補.map((k) => <option key={k}>{k}</option>)}
                </select>
              </div>

              <div className="mt-1.5 flex items-center justify-between">
                <span className={'rounded px-1.5 py-0.5 text-[10px] ' + (区分色[line.区分] || '')}>{line.区分}</span>
                <span className={'text-sm tabular ' + (row?.cost === null ? 'text-rose-500' : 'font-medium text-slate-800')}>
                  {row?.cost === null ? '単価未確定' : yen(row?.cost)}
                </span>
              </div>
            </div>
          );
        })}
      </section>

      {/* 結果 */}
      <section className="rounded-xl border border-[#8C2E1B]/25 bg-[#8C2E1B]/5 p-3">
        <div className="flex items-baseline justify-between">
          <span className="text-xs text-slate-600">1仕込みの原価</span>
          <span className="text-2xl font-bold tabular text-[#8C2E1B]">{yen(calc.仕込み原価)}</span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 text-center">
          {[
            ['1個あたり', calc['1個原価']],
            ['100gあたり', calc['100g原価']],
            ['1人あたり', calc.一人あたり],
          ].map(([label, v]) => (
            <div key={label} className="rounded-lg bg-white p-2">
              <p className="text-[10px] text-slate-500">{label}</p>
              <p className="text-sm font-semibold tabular text-slate-800">{yen(v)}</p>
            </div>
          ))}
        </div>
        {calc.原価率 !== null && (
          <div className="mt-2 flex items-baseline justify-between rounded-lg bg-white px-3 py-2">
            <span className="text-xs text-slate-500">原価率</span>
            <span className={'text-lg font-bold tabular ' + rateColor(calc.原価率)}>{pct(calc.原価率)}</span>
          </div>
        )}

        {calc.未確定件数 > 0 && (
          <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-50 p-2 text-[11px] text-amber-800">
            <AlertTriangle size={13} className="mt-px shrink-0" />
            単価が確定していない材料が{calc.未確定件数}件あります。時価品は「単価手入力」に当日単価を入れてください。0では埋めていません。
          </p>
        )}

        {calc.衣試算.length > 0 && (
          <div className="mt-3 rounded-lg bg-white p-2.5">
            <p className="mb-1.5 text-[11px] font-medium text-slate-600">衣の実付着量ちがい</p>
            <p className="mb-2 text-[10px] text-slate-400">まぶし粉は全量が製品に残らない。3〜7割で並べる。</p>
            <div className="space-y-1">
              {calc.衣試算.map((t) => (
                <div key={t.付着率} className="flex items-center justify-between text-xs tabular">
                  <span className="text-slate-500">付着 {Math.round(t.付着率 * 100)}%</span>
                  <span className="text-slate-800">
                    {yen(t.仕込み原価)}
                    {t['1個原価'] !== null && <span className="ml-2 text-slate-400">1個 {yen(t['1個原価'])}</span>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {picking && (
        <ItemPicker
          items={items}
          onClose={() => setPicking(null)}
          onPick={(it) => {
            patchLine(picking, {
              itemId: it.id,
              食材名: recipe.lines.find((l) => l.id === picking)?.食材名 || it.食材名称,
              単位: it.入り数単位 || 'g',
            });
            setPicking(null);
          }}
        />
      )}
    </div>
  );
}

// ==========================================
// 単価マスタータブ
// ==========================================
function MasterTab({ items, setItems }) {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState(null);
  const [showWarn, setShowWarn] = useState(false);
  const [editing, setEditing] = useState(null);
  const fileRef = useRef(null);

  const dups = useMemo(() => findDuplicates(items), [items]);
  const unconverted = useMemo(() => items.filter((i) => i.入り数 === null || i.入り数 === ''), [items]);
  const 時価 = useMemo(() => items.filter((i) => i.仕入単価 === null || i.仕入単価 === ''), [items]);

  const hits = useMemo(() => {
    const s = q.trim().toLowerCase();
    const base = s
      ? items.filter((it) => (it.食材名称 || '').toLowerCase().includes(s) || (it.仕入先 || '').toLowerCase().includes(s))
      : items;
    return base.slice(0, 200);
  }, [q, items]);

  const onFile = async (file) => {
    if (!file) return;
    try {
      const buf = await file.arrayBuffer();
      const text = decodeCp932(buf);
      const { items: parsed, stats } = importInfomart(text);
      // 商品コード＋仕入先で既存と突き合わせ、歩留まりの実測値は上書きしない。
      const prev = new Map(items.map((i) => [(i.商品コード || i.食材名称) + '|' + (i.仕入先 || ''), i]));
      const merged = parsed.map((p) => {
        const old = prev.get((p.商品コード || p.食材名称) + '|' + (p.仕入先 || ''));
        return {
          ...p,
          id: old?.id ?? newId(),
          歩留まり: old && old.歩留まり !== 1.0 ? old.歩留まり : p.歩留まり,
        };
      });
      setItems(merged);
      setStatus({
        ok: true,
        text: stats.total + '件を読み込み。単価あり ' + stats.priced + '件 / 内容量が換算できたもの ' + stats.converted + '件。'
          + '残りは規格欄が空で内容量が判断できないもの。使う品目だけ手で入れれば足ります。',
      });
    } catch (e) {
      setStatus({ ok: false, text: 'CSVを読めませんでした（' + (e?.message || e) + '）。インフォマートのマイカタログCSVをそのまま入れてください。' });
    }
  };

  const patchItem = (id, p) => setItems(items.map((i) => (i.id === id ? { ...i, ...p } : i)));

  return (
    <div className="space-y-3 p-3 pb-28">
      <section className="rounded-xl border border-slate-200 bg-white p-3">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">インフォマート マイカタログCSV</h2>
        <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])} />
        <button onClick={() => fileRef.current?.click()}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#8C2E1B] px-3 py-2.5 text-sm font-medium text-white active:opacity-80">
          <Upload size={15} />CSVを選ぶ
        </button>
        <p className="mt-1.5 text-[10px] leading-relaxed text-slate-400">
          cp932のまま入れて構いません。規格・商品名から内容量を読んでグラム単価に換算します。
          読めなかったものは未換算のまま残します（0では埋めません）。
        </p>
        {status && (
          <p className={'mt-2 rounded-lg p-2 text-[11px] ' + (status.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-700')}>
            {status.text}
          </p>
        )}
      </section>

      {items.length > 0 && (
        <section className="grid grid-cols-3 gap-2">
          {[
            ['登録', items.length, 'text-slate-800'],
            ['未換算', unconverted.length, 'text-amber-600'],
            ['時価品', 時価.length, 'text-sky-600'],
          ].map(([l, v, c]) => (
            <div key={l} className="rounded-xl border border-slate-200 bg-white p-2 text-center">
              <p className="text-[10px] text-slate-500">{l}</p>
              <p className={'text-lg font-bold tabular ' + c}>{v}</p>
            </div>
          ))}
        </section>
      )}

      {dups.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <button onClick={() => setShowWarn(!showWarn)} className="flex w-full items-center gap-1.5 text-left">
            {showWarn ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <AlertTriangle size={14} className="text-amber-600" />
            <span className="text-xs font-medium text-amber-900">同名の重複が{dups.length}件</span>
          </button>
          {showWarn && (
            <>
              <p className="mt-1.5 text-[10px] leading-relaxed text-amber-800">
                VLOOKUPは最初の一致行しか拾いません。下の行は永久に使われないので、
                食材名称に仕入先を足して分けてください（例：宗八カレイ(ヤマヨ) / 宗八カレイ(知床)）。
                レシピで実際に呼ぶ食材だけ直せば実害はありません。
              </p>
              <ul className="mt-2 space-y-1">
                {dups.slice(0, 40).map((d) => (
                  <li key={d.name} className="text-[11px] text-amber-900">
                    ・{d.name}（{d.count}件{d.仕入先.length ? '：' + d.仕入先.join(' / ') : ''}）
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2">
          <Search size={15} className="text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="食材名・仕入先で検索"
            className="flex-1 text-sm outline-none" />
          <button
            onClick={() => setItems([...items, {
              id: newId(), 分類: '', 食材名称: '', 仕入先: '', 仕入単価: null,
              単位: 'kg', 入り数: 1000, 入り数単位: 'g', 歩留まり: 1.0, 換算元: '手入力', warnings: [],
            }])}
            className="shrink-0 rounded-lg bg-slate-800 px-2 py-1.5 text-[11px] text-white active:bg-slate-700">
            <Plus size={12} className="inline" />手で追加
          </button>
        </div>

        {items.length === 0 && (
          <p className="px-3 py-8 text-center text-xs text-slate-400">
            まだ空です。CSVを取り込むか「手で追加」から登録してください。
          </p>
        )}

        {hits.map((it) => {
          const up = itemUnitPrice(it);
          const open = editing === it.id;
          return (
            <div key={it.id} className="border-b border-slate-100 last:border-0">
              <button onClick={() => setEditing(open ? null : it.id)}
                className="flex w-full items-center gap-2 px-3 py-2.5 text-left active:bg-slate-50">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-slate-800">{it.食材名称 || '(名称なし)'}</p>
                  <p className="truncate text-[10px] text-slate-400">
                    {it.仕入先 || '仕入先なし'}
                    {it.規格 ? ' / ' + it.規格 : ''}
                    {/* 同名で単位違い(本 と C/S など)を見分けられるよう単位と入り数を出す */}
                    {it.単位 ? ' / ' + it.単位 : ''}
                    {it.入り数 ? ' ' + it.入り数 + (it.入り数単位 || 'g') : ''}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className={'text-xs tabular ' + (up === null ? 'text-rose-500' : 'text-slate-700')}>
                    {up === null ? '未確定' : yen1(up) + '円/' + (it.入り数単位 || 'g')}
                  </p>
                  {it.歩留まり !== 1.0 && (
                    <p className="text-[10px] text-emerald-600">歩留{Math.round(it.歩留まり * 100)}%</p>
                  )}
                </div>
                <Pencil size={13} className="shrink-0 text-slate-300" />
              </button>

              {open && (
                <div className="space-y-2 bg-slate-50 px-3 py-3">
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="食材名称">
                      <input className={inputCls} value={it.食材名称 || ''}
                        onChange={(e) => patchItem(it.id, { 食材名称: e.target.value })} />
                    </Field>
                    <Field label="仕入先" hint="同名があるならここを名称に足す">
                      <input className={inputCls} value={it.仕入先 || ''}
                        onChange={(e) => patchItem(it.id, { 仕入先: e.target.value })} />
                    </Field>
                    <Field label="仕入単価 (円)" hint="空欄＝時価品。埋めなくてよい">
                      <input className={inputCls} inputMode="decimal"
                        value={it.仕入単価 ?? ''}
                        onChange={(e) => patchItem(it.id, { 仕入単価: e.target.value === '' ? null : num(e.target.value) })} />
                    </Field>
                    <Field label="単位">
                      <input className={inputCls} value={it.単位 || ''}
                        onChange={(e) => {
                          const u = e.target.value;
                          const p = unitPack(u);
                          patchItem(it.id, {
                            単位: u,
                            ...(p ? { 入り数: p.count, 入り数単位: p.kind === 'volume' ? 'ml' : p.kind === 'piece' ? '個' : 'g', 換算元: '単位' + u } : {}),
                          });
                        }} />
                    </Field>
                    <Field label="入り数" hint="この単価が何g(ml/個)分か">
                      <input className={inputCls} inputMode="decimal" value={it.入り数 ?? ''}
                        onChange={(e) => patchItem(it.id, { 入り数: e.target.value === '' ? null : num(e.target.value) })} />
                    </Field>
                    <Field label="歩留まり (%)" hint="実測が出たものだけ変える">
                      <input className={inputCls} inputMode="decimal"
                        value={Math.round((it.歩留まり ?? 1) * 100)}
                        onChange={(e) => {
                          const v = num(e.target.value);
                          patchItem(it.id, { 歩留まり: v === null || v <= 0 ? 1.0 : v / 100 });
                        }} />
                    </Field>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs text-slate-500">
                      グラム単価 <span className="tabular font-medium text-slate-800">
                        {up === null ? '未確定' : yen1(up) + '円/' + (it.入り数単位 || 'g')}
                      </span>
                    </span>
                    <button onClick={() => { setItems(items.filter((x) => x.id !== it.id)); setEditing(null); }}
                      className="inline-flex items-center gap-1 text-xs text-rose-600"><Trash2 size={13} />削除</button>
                  </div>
                  {it.warnings?.length > 0 && (
                    <ul className="rounded-lg bg-amber-50 p-2">
                      {it.warnings.map((w, i) => (
                        <li key={i} className="text-[10px] text-amber-800">・{w}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {items.length > hits.length && (
          <p className="px-3 py-2 text-center text-[10px] text-slate-400">
            {items.length}件中{hits.length}件を表示。検索で絞ってください。
          </p>
        )}
      </section>

      {items.length > 0 && (
        <button onClick={() => downloadText('単価マスター.csv', CSV_BOM + masterCsv(items))}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 active:bg-slate-50">
          <Download size={15} />単価マスターをCSVで書き出す
        </button>
      )}
    </div>
  );
}

// ==========================================
// 一覧タブ（原価率の比較）
// ==========================================
function ListTab({ recipes, itemsById, onOpen, onAdd, onDelete }) {
  const rows = useMemo(
    () => recipes.map((r) => ({ recipe: r, calc: calcRecipe(r, itemsById) })),
    [recipes, itemsById],
  );
  const [sort, setSort] = useState('rate');
  const sorted = useMemo(() => {
    const c = [...rows];
    if (sort === 'rate') c.sort((a, b) => (b.calc.原価率 ?? -1) - (a.calc.原価率 ?? -1));
    if (sort === 'cost') c.sort((a, b) => (b.calc['1個原価'] ?? -1) - (a.calc['1個原価'] ?? -1));
    return c;
  }, [rows, sort]);

  return (
    <div className="space-y-3 p-3 pb-28">
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {[['rate', '原価率順'], ['cost', '1個原価順']].map(([k, l]) => (
            <button key={k} onClick={() => setSort(k)}
              className={'rounded-lg px-2.5 py-1.5 text-xs ' + (sort === k ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 border border-slate-200')}>
              {l}
            </button>
          ))}
        </div>
        <button onClick={onAdd}
          className="inline-flex items-center gap-1 rounded-lg bg-[#8C2E1B] px-2.5 py-1.5 text-xs font-medium text-white active:opacity-80">
          <Plus size={13} />料理を足す
        </button>
      </div>

      {rows.length === 0 && (
        <p className="rounded-xl border border-slate-200 bg-white px-3 py-8 text-center text-xs text-slate-400">
          まだ料理がありません。「料理を足す」から始めてください。
        </p>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {sorted.map(({ recipe, calc }) => (
          <div key={recipe.id} className="flex items-center gap-2 border-b border-slate-100 px-3 py-2.5 last:border-0">
            <button onClick={() => onOpen(recipe.id)} className="min-w-0 flex-1 text-left active:opacity-60">
              <p className="truncate text-sm font-medium text-slate-800">{recipe.料理名 || '(名称未設定)'}</p>
              <p className="truncate text-[10px] text-slate-400">
                {recipe.カテゴリ || '未分類'}
                {recipe.仕込み単位 ? ' / ' + recipe.仕込み単位 : ''}
                {calc.未確定件数 > 0 ? ' / 未確定' + calc.未確定件数 + '件' : ''}
              </p>
            </button>
            <div className="shrink-0 text-right">
              <p className={'text-sm font-bold tabular ' + rateColor(calc.原価率)}>{pct(calc.原価率)}</p>
              <p className="text-[10px] tabular text-slate-500">
                1個 {yen(calc['1個原価'])}
              </p>
            </div>
            <button onClick={() => onDelete(recipe.id)} className="shrink-0 p-1 text-slate-300 active:text-rose-500">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {rows.length > 0 && (
        <>
          <p className="px-1 text-[10px] leading-relaxed text-slate-400">
            高原価でも看板になっている品は残す判断があります。見直しの最優先は
            「原価が高くて看板にもなっていない品」です。数字だけで削る判断はしないでください。
          </p>
          <button onClick={() => downloadText('原価一覧.csv', CSV_BOM + recipesCsv(sorted))}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 active:bg-slate-50">
            <Download size={15} />原価一覧をCSVで書き出す
          </button>
        </>
      )}
    </div>
  );
}

// ==========================================
// 共有タブ
// ==========================================
function ShareTab({ recipe, itemsById }) {
  const calc = useMemo(() => calcRecipe(recipe, itemsById), [recipe, itemsById]);
  const [mode, setMode] = useState('simple');
  const text = mode === 'simple' ? lineTextSimple(recipe, calc)
    : mode === 'detail' ? lineTextDetail(recipe, calc)
      : markdownTable(recipe, calc);

  return (
    <div className="space-y-3 p-3 pb-28">
      <div className="flex gap-1">
        {[['simple', 'LINE 簡潔版'], ['detail', 'LINE 詳細版'], ['md', 'markdown']].map(([k, l]) => (
          <button key={k} onClick={() => setMode(k)}
            className={'flex-1 rounded-lg px-2 py-2 text-xs ' + (mode === k ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 border border-slate-200')}>
            {l}
          </button>
        ))}
      </div>
      <p className="px-1 text-[10px] text-slate-400">
        {mode === 'simple' && 'キッチンのグループに投げるだけなら簡潔版。'}
        {mode === 'detail' && '新人に渡すなら詳細版。原価表と注意点つき。'}
        {mode === 'md' && '会話の中で確認するとき用。'}
      </p>
      <pre className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-800">
        {text}
      </pre>
      <CopyButton text={text} />
    </div>
  );
}

// ==========================================
// ロス管理アプリへの反映タブ
// ==========================================
function BridgeTab({ recipes, itemsById }) {
  const [loss, setLoss] = useState(() => readLossMenu());
  const [plan, setPlan] = useState({});      // recipeId -> 'cat|item' | 'new:catId' | ''
  const [force, setForce] = useState({});    // recipeId -> 未確定でも反映する
  const [result, setResult] = useState(null);
  const [hasBackup, setHasBackup] = useState(() => !!localStorage.getItem(BACKUP_KEY));

  const rows = useMemo(() => recipes.map((r) => {
    const calc = calcRecipe(r, itemsById);
    return { recipe: r, calc, cost: calc['1個原価'] };
  }).filter((x) => x.recipe.料理名), [recipes, itemsById]);

  const flat = useMemo(() => (loss.menu ? flattenMenu(loss.menu) : []), [loss]);

  // 初回に自動で当てておく。曖昧なものは当てない。
  useEffect(() => {
    if (!loss.menu) return;
    setPlan((prev) => {
      const next = { ...prev };
      for (const { recipe } of rows) {
        if (next[recipe.id] !== undefined) continue;
        const m = autoMatch(recipe.料理名, loss.menu);
        next[recipe.id] = m ? m.categoryId + '|' + m.item.id : '';
      }
      return next;
    });
  }, [loss, rows]);

  if (loss.error) {
    return (
      <div className="space-y-3 p-3 pb-28">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="flex items-start gap-1.5 text-xs text-amber-900">
            <AlertTriangle size={14} className="mt-px shrink-0" />
            {loss.error}
          </p>
          <p className="mt-2 text-[10px] leading-relaxed text-amber-800">
            ロス管理アプリと原価出しツールは、同じドメインから開いたときだけデータを共有できます。
            片方を raw.githack、もう片方をローカルのファイルで開いていると繋がりません。
          </p>
          <button onClick={() => setLoss(readLossMenu())}
            className="mt-2 rounded-lg bg-amber-700 px-3 py-1.5 text-xs text-white active:opacity-80">
            もう一度さがす
          </button>
        </div>
      </div>
    );
  }

  const decide = (row) => {
    const sel = plan[row.recipe.id] ?? '';
    const blocked = row.calc.未確定件数 > 0 && !force[row.recipe.id];
    if (!sel || row.cost === null || blocked) return null;
    if (sel.startsWith('new:')) return { target: { categoryId: sel.slice(4), newName: row.recipe.料理名 }, cost: row.cost };
    const [categoryId, itemId] = sel.split('|');
    return { target: { categoryId, itemId }, cost: row.cost };
  };

  const entries = rows.map((r) => ({ row: r, entry: decide(r) })).filter((x) => x.entry);

  const apply = () => {
    const { menu: next, updated, added } = applyPlan(loss.menu, entries.map((e) => e.entry));
    try {
      // 直前の状態を残す。取り消せるようにしておく。
      localStorage.setItem(BACKUP_KEY, JSON.stringify({ at: new Date().toISOString(), menu: loss.menu }));
      localStorage.setItem(LOSS_KEYS.menu, JSON.stringify(next));
      // bl_menu_ver には触らない。触るとロス管理側がメニューを初期化する。
      setLoss({ menu: next, ver: loss.ver });
      setHasBackup(true);
      setResult({ ok: true, text: '原価を書き換えました（更新 ' + updated + '件 / 新規 ' + added + '件）。ロス管理アプリを開き直すと反映されています。' });
    } catch (e) {
      setResult({ ok: false, text: '書き込めませんでした（' + (e?.message || e) + '）' });
    }
  };

  const undo = () => {
    try {
      const b = JSON.parse(localStorage.getItem(BACKUP_KEY));
      if (!b?.menu) return;
      localStorage.setItem(LOSS_KEYS.menu, JSON.stringify(b.menu));
      localStorage.removeItem(BACKUP_KEY);
      setLoss({ menu: b.menu, ver: loss.ver });
      setHasBackup(false);
      setResult({ ok: true, text: '反映前の状態に戻しました。' });
    } catch {
      setResult({ ok: false, text: '戻せませんでした' });
    }
  };

  return (
    <div className="space-y-3 p-3 pb-28">
      <section className="rounded-xl border border-slate-200 bg-white p-3">
        <h2 className="text-sm font-semibold text-slate-700">焼肉ロス管理アプリへ原価を送る</h2>
        <p className="mt-1 text-[10px] leading-relaxed text-slate-400">
          ここで出した<strong className="text-slate-600">1個(1皿)あたり原価</strong>を、ロス管理アプリの「原価¥」に書き込みます。
          あちらのメニュー{flat.length}品目を読み込み済み。書き込む前の状態は自動で控えるので、あとから戻せます。
        </p>
      </section>

      {rows.length === 0 && (
        <p className="rounded-xl border border-slate-200 bg-white px-3 py-8 text-center text-xs text-slate-400">
          料理名の付いた料理がまだありません。
        </p>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {rows.map(({ recipe, calc, cost }) => {
          const sel = plan[recipe.id] ?? '';
          const blocked = calc.未確定件数 > 0 && !force[recipe.id];
          const current = sel && !sel.startsWith('new:')
            ? flat.find((f) => f.item.id === sel.split('|')[1])?.item.cost
            : null;
          const willWrite = !!decide({ recipe, calc, cost });
          return (
            <div key={recipe.id} className="border-b border-slate-100 p-3 last:border-0">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">{recipe.料理名}</p>
                  <p className="text-[10px] text-slate-400">
                    {recipe.カテゴリ || '未分類'}{recipe.仕込み単位 ? ' / ' + recipe.仕込み単位 : ''}
                  </p>
                </div>
                {/* 未確定を含む金額を確定値のように見せない。合計が0なら金額を出さない。 */}
                <span className="shrink-0 text-right">
                  {cost === null || (calc.未確定件数 > 0 && calc.仕込み原価 === 0) ? (
                    <span className="text-sm font-semibold text-amber-600">未確定</span>
                  ) : (
                    <>
                      <span className={'text-sm font-semibold tabular ' + (calc.未確定件数 > 0 ? 'text-amber-600' : 'text-slate-800')}>
                        {yen(cost)}
                      </span>
                      {calc.未確定件数 > 0 && (
                        <span className="block text-[10px] text-amber-600">＋未確定{calc.未確定件数}件</span>
                      )}
                    </>
                  )}
                </span>
              </div>

              <select
                value={sel} onChange={(e) => setPlan({ ...plan, [recipe.id]: e.target.value })}
                className={inputCls + ' mt-2'}
              >
                <option value="">反映しない</option>
                {loss.menu.map((c) => (
                  <optgroup key={c.id} label={c.category}>
                    {(c.items ?? []).map((it) => (
                      <option key={it.id} value={c.id + '|' + it.id}>
                        {it.name}（現在 {it.cost}円）
                      </option>
                    ))}
                    <option value={'new:' + c.id}>＋ {c.category} に新規追加</option>
                  </optgroup>
                ))}
              </select>

              {calc.未確定件数 > 0 && (
                <label className="mt-2 flex items-start gap-2 rounded-lg bg-amber-50 p-2">
                  <input type="checkbox" checked={!!force[recipe.id]} className="mt-0.5"
                    onChange={(e) => setForce({ ...force, [recipe.id]: e.target.checked })} />
                  <span className="text-[10px] leading-relaxed text-amber-800">
                    単価が確定していない材料が{calc.未確定件数}件あります。いま出ている金額は
                    <strong>その分を含んでいません</strong>。既定では送りません。
                    時価品なら「原価計算」で当日単価を入れてから戻ってきてください。
                  </span>
                </label>
              )}

              {willWrite && (
                <p className="mt-1.5 text-[10px] text-emerald-700">
                  {sel.startsWith('new:')
                    ? '新しい品目として追加します'
                    : current === Math.round(cost)
                      ? '同じ金額なので変わりません'
                      : '原価 ' + current + '円 → ' + Math.round(cost) + '円 に書き換えます'}
                </p>
              )}
            </div>
          );
        })}
      </div>

      {result && (
        <p className={'rounded-lg p-2.5 text-[11px] ' + (result.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-700')}>
          {result.text}
        </p>
      )}

      <button
        onClick={apply} disabled={entries.length === 0}
        className={'inline-flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-3 text-sm font-medium text-white '
          + (entries.length === 0 ? 'bg-slate-300' : 'bg-[#8C2E1B] active:opacity-80')}
      >
        <ArrowRightLeft size={15} />
        {entries.length === 0 ? '送る料理を選んでください' : entries.length + '品をロス管理アプリに反映'}
      </button>

      {hasBackup && (
        <button onClick={undo}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 active:bg-slate-50">
          <RotateCcw size={15} />反映前に戻す
        </button>
      )}

      <p className="px-1 text-[10px] leading-relaxed text-slate-400">
        ロス管理アプリを開いたままここで反映すると、あちらの画面は古いままです。
        向こうを開き直してから確認してください。
      </p>
    </div>
  );
}

// ==========================================
// ルート
// ==========================================
const TABS = [
  { k: 'calc', label: '原価計算', Icon: Calculator },
  { k: 'list', label: '一覧', Icon: ListOrdered },
  { k: 'master', label: '単価マスター', Icon: Database },
  { k: 'share', label: '共有', Icon: Share2 },
  { k: 'bridge', label: 'ロス連携', Icon: ArrowRightLeft },
];

export default function App() {
  const [items, setItems] = useState(() => load('items', []));
  const [recipes, setRecipes] = useState(() => {
    const r = load('recipes', []);
    return r.length ? r : [emptyRecipe()];
  });
  const [activeId, setActiveId] = useState(() => load('active', null));
  const [tab, setTab] = useState('calc');

  useEffect(() => { save('items', items); }, [items]);
  useEffect(() => { save('recipes', recipes); }, [recipes]);
  useEffect(() => { save('active', activeId); }, [activeId]);

  const itemsById = useMemo(() => new Map(items.map((i) => [i.id, i])), [items]);
  const active = recipes.find((r) => r.id === activeId) ?? recipes[0];

  useEffect(() => {
    if (active && active.id !== activeId) setActiveId(active.id);
  }, [active, activeId]);

  const setActive = (next) => setRecipes(recipes.map((r) => (r.id === next.id ? next : r)));
  const addRecipe = () => {
    const r = emptyRecipe();
    setRecipes([...recipes, r]); setActiveId(r.id); setTab('calc');
  };
  const deleteRecipe = (id) => {
    const rest = recipes.filter((r) => r.id !== id);
    setRecipes(rest.length ? rest : [emptyRecipe()]);
  };

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <header className="shrink-0 bg-[#8C2E1B] px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] text-white">
        <h1 className="text-base font-semibold">ススデパ 原価出し</h1>
        <p className="text-[11px] opacity-70">
          {tab === 'master'
            ? '単価マスター ' + items.length + '件'
            : (active?.料理名 || '料理名未設定') + (active?.仕込み単位 ? ' / ' + active.仕込み単位 : '')}
        </p>
      </header>

      <main className="flex-1 overflow-y-auto">
        {tab === 'calc' && active && (
          <CalcTab recipe={active} setRecipe={setActive} items={items} itemsById={itemsById} />
        )}
        {tab === 'list' && (
          <ListTab recipes={recipes} itemsById={itemsById}
            onOpen={(id) => { setActiveId(id); setTab('calc'); }}
            onAdd={addRecipe} onDelete={deleteRecipe} />
        )}
        {tab === 'master' && <MasterTab items={items} setItems={setItems} />}
        {tab === 'share' && active && <ShareTab recipe={active} itemsById={itemsById} />}
        {tab === 'bridge' && <BridgeTab recipes={recipes} itemsById={itemsById} />}
      </main>

      <nav className="shrink-0 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]">
        <div className="flex">
          {TABS.map(({ k, label, Icon }) => (
            <button key={k} onClick={() => setTab(k)}
              className={'flex flex-1 flex-col items-center gap-0.5 py-2 ' + (tab === k ? 'text-[#8C2E1B]' : 'text-slate-400')}>
              <Icon size={19} />
              <span className="text-[10px]">{label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}
