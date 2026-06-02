import React, { useState, useEffect, useMemo } from 'react';
import {
  Plus, Minus, ClipboardList, BarChart3, ChevronRight, ChevronDown,
  Trash2, Search, Utensils, Beef, Drumstick, Flame,
  Download, AlertTriangle, Save, Edit, X, Lock, Unlock, RefreshCw, Sparkles, Check,
} from 'lucide-react';

// ==========================================
// 設定・定数
// ==========================================
const MENU_VERSION = 4; // メニュー構造を変えたら +1 して初期化を促す
const ADMIN_PW = '1234'; // 管理者パスワード（あとで変更可）
const FLAVOR_PRESETS = ['塩', '味噌', 'バジル']; // 本日の味メモ候補

// 単位ごとの入力設定（step=±ボタンの刻み, chips=クイック加算, wheel=ロール選択の最大値/刻み）
const UNIT_CONFIG = {
  g: { step: 50, chips: [100, 250, 500], wheelMax: 3000, wheelStep: 50 },
  kg: { step: 0.5, chips: [1, 2, 5], wheelMax: 20, wheelStep: 0.5 },
};
const DEFAULT_UNIT_CFG = { step: 1, chips: [1, 5, 10], wheelMax: 50, wheelStep: 1 };
const cfgFor = (unit) => UNIT_CONFIG[unit] || DEFAULT_UNIT_CFG;

// 単位のワンタップ候補
const UNIT_PRESETS = ['皿', 'g', 'kg', '枚', '本', '個', '尾', '杯', '丁', '鍋', '袋'];

// ロール選択用の数値リストを生成（浮動小数の誤差を丸める）
const wheelValues = (unit) => {
  const { wheelMax, wheelStep } = cfgFor(unit);
  const arr = [];
  for (let v = 0; v <= wheelMax + 1e-9; v += wheelStep) arr.push(Math.round(v * 100) / 100);
  return arr;
};

const generateId = () => 'id-' + Math.random().toString(36).slice(2, 9) + '-' + Date.now().toString(36);
const todayStr = () => new Date().toISOString().split('T')[0];
const yen = (n) => '¥' + Math.round(n || 0).toLocaleString();

// メニュー項目を作るヘルパー（cost=原価, defaultQty=入力時の初期値）
function mk(name, unit = '皿', cost = 0, defaultQty = 1) {
  return { id: 'i-' + name, name, unit, cost, defaultQty };
}

// ==========================================
// 初期データ（焼肉メニュー）
// ==========================================
const INITIAL_MENU_DATA = [
  {
    id: 'c-gyu', category: '牛', iconType: 'Beef', defaultUnit: '皿',
    items: [
      mk('牛カルビ'), mk('牛タン'), mk('サーロイン'), mk('牛サガリ'), mk('牛ロース'),
      mk('ミノ'), mk('ハチノス'), mk('センマイ'), mk('ギアラ'), mk('マルチョウ'), mk('インジェクションビーフ'),
    ],
  },
  {
    id: 'c-buta', category: '豚', iconType: 'Beef', defaultUnit: '皿',
    items: [mk('豚カルビ'), mk('トントロ'), mk('豚セセリ'), mk('ホルモン'), mk('ガツ')],
  },
  {
    id: 'c-hitsuji', category: '羊', iconType: 'Beef', defaultUnit: '皿',
    items: [
      mk('アイオブラック'), mk('味付きサガリ（マトン）'), mk('塩ジンギスカン（ラム）'),
      mk('味付き肩ロース（マトン）'), mk('ウインナー（スモーク・チョリソー）'),
    ],
  },
  {
    id: 'c-tori', category: '鶏', iconType: 'Drumstick', defaultUnit: '皿',
    items: [mk('鶏もも'), mk('鶏セセリ'), mk('ヤゲンナンコツ'), mk('砂肝')],
  },
];

const getIcon = (type, size = 18) => {
  switch (type) {
    case 'Beef': return <Beef size={size} />;
    case 'Drumstick': return <Drumstick size={size} />;
    case 'Flame': return <Flame size={size} />;
    default: return <Utensils size={size} />;
  }
};

// ==========================================
// アプリ本体
// ==========================================
const App = () => {
  const today = todayStr();

  const [view, setView] = useState('input');
  const [menuData, setMenuData] = useState(INITIAL_MENU_DATA);
  const [records, setRecords] = useState({}); // { [itemId]: { supply, remained } }
  const [dailyItems, setDailyItems] = useState([]); // 本日だけの品 [{id,name,unit,cost}]
  const [dailyPool, setDailyPool] = useState([]); // 使い回し用の引き出し
  const [flavors, setFlavors] = useState([]); // 本日の味メモ
  const [expanded, setExpanded] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isInitialized, setIsInitialized] = useState(false);
  const [showUpdateNotice, setShowUpdateNotice] = useState(false);

  // 管理者・編集
  const [isAdmin, setIsAdmin] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [editingItem, setEditingItem] = useState(null); // { catId, itemId, name, unit, cost }
  const [editingCategory, setEditingCategory] = useState(null); // { catId, name }
  const [newItemInputs, setNewItemInputs] = useState({});

  // モーダル
  const [keypad, setKeypad] = useState(null); // { id, name, unit, field, value }
  const [dailyModal, setDailyModal] = useState(false);
  const [newDaily, setNewDaily] = useState({ name: '', unit: '皿', cost: '' });

  // ---- 起動時ロード ----
  useEffect(() => {
    // メニュー構造
    const savedVer = localStorage.getItem('bl_menu_ver');
    let savedMenu = null;
    try { savedMenu = JSON.parse(localStorage.getItem('bl_menu')); } catch { /* ignore */ }

    if (savedMenu && savedVer && parseInt(savedVer, 10) === MENU_VERSION) {
      setMenuData(savedMenu);
      setExpanded(savedMenu.map((c) => c.id));
    } else {
      setMenuData(INITIAL_MENU_DATA);
      setExpanded(INITIAL_MENU_DATA.map((c) => c.id));
      localStorage.setItem('bl_menu', JSON.stringify(INITIAL_MENU_DATA));
      localStorage.setItem('bl_menu_ver', String(MENU_VERSION));
      if (savedMenu) {
        setShowUpdateNotice(true);
        setTimeout(() => setShowUpdateNotice(false), 3000);
      }
    }

    // 当日データ
    try { setRecords(JSON.parse(localStorage.getItem(`bl_rec_${today}`)) || {}); } catch { setRecords({}); }
    try { setDailyItems(JSON.parse(localStorage.getItem(`bl_daily_${today}`)) || []); } catch { setDailyItems([]); }
    try { setFlavors(JSON.parse(localStorage.getItem(`bl_flavors_${today}`)) || []); } catch { setFlavors([]); }
    try { setDailyPool(JSON.parse(localStorage.getItem('bl_pool')) || []); } catch { setDailyPool([]); }

    setIsInitialized(true);
  }, [today]);

  // ---- 保存 ----
  useEffect(() => { if (isInitialized) localStorage.setItem(`bl_rec_${today}`, JSON.stringify(records)); }, [records, isInitialized, today]);
  useEffect(() => { if (isInitialized) localStorage.setItem(`bl_daily_${today}`, JSON.stringify(dailyItems)); }, [dailyItems, isInitialized, today]);
  useEffect(() => { if (isInitialized) localStorage.setItem(`bl_flavors_${today}`, JSON.stringify(flavors)); }, [flavors, isInitialized, today]);
  useEffect(() => { if (isInitialized) localStorage.setItem('bl_pool', JSON.stringify(dailyPool)); }, [dailyPool, isInitialized]);
  useEffect(() => {
    if (!isInitialized) return;
    localStorage.setItem('bl_menu', JSON.stringify(menuData));
    localStorage.setItem('bl_menu_ver', String(MENU_VERSION));
  }, [menuData, isInitialized]);

  // ---- 操作 ----
  const toggleAdmin = () => {
    if (isAdmin) {
      setIsAdmin(false); setEditingCategory(null); setEditingItem(null);
    } else {
      const pw = window.prompt('管理者パスワードを入力してください');
      if (pw === ADMIN_PW) setIsAdmin(true);
      else if (pw !== null) alert('パスワードが違います');
    }
  };

  const toggleCategory = (catId) =>
    setExpanded((prev) => (prev.includes(catId) ? prev.filter((id) => id !== catId) : [...prev, catId]));

  const updateValue = (itemId, field, delta) =>
    setRecords((prev) => {
      const cur = prev[itemId] || { supply: 0, remained: 0 };
      const next = Math.max(0, (cur[field] || 0) + delta);
      return { ...prev, [itemId]: { ...cur, [field]: next } };
    });

  const setExactValue = (itemId, field, value) =>
    setRecords((prev) => {
      const cur = prev[itemId] || { supply: 0, remained: 0 };
      // 小数2桁まで許可（kg などの 0.5 刻みに対応）
      const next = Math.max(0, Math.round((Number(value) || 0) * 100) / 100);
      return { ...prev, [itemId]: { ...cur, [field]: next } };
    });

  // ---- メニュー編集 ----
  const handleAddCategory = () => {
    if (!newCategoryName.trim()) return;
    const id = generateId();
    setMenuData((prev) => [...prev, { id, category: newCategoryName.trim(), iconType: 'Utensils', defaultUnit: '皿', items: [] }]);
    setNewCategoryName('');
    setExpanded((prev) => [...prev, id]);
  };
  const deleteCategory = (catId) => {
    if (!window.confirm('このカテゴリを削除しますか？\n（含まれるメニューも消えます）')) return;
    setMenuData((prev) => prev.filter((c) => c.id !== catId));
  };
  const saveCategoryEdit = () => {
    if (!editingCategory?.name.trim()) return;
    setMenuData((prev) => prev.map((c) => (c.id === editingCategory.catId ? { ...c, category: editingCategory.name.trim() } : c)));
    setEditingCategory(null);
  };
  const saveItemEdit = () => {
    if (!editingItem?.name.trim()) { alert('品名を入力してください'); return; }
    const { catId, itemId, name, unit, cost } = editingItem;
    setMenuData((prev) => prev.map((c) => (c.id === catId ? {
      ...c,
      items: c.items.map((it) => (it.id === itemId ? { ...it, name: name.trim(), unit: unit.trim() || '皿', cost: Math.max(0, Number(cost) || 0) } : it)),
    } : c)));
    setEditingItem(null);
  };
  const deleteItem = (catId, itemId) => {
    if (!window.confirm('このメニューを削除しますか？')) return;
    setMenuData((prev) => prev.map((c) => (c.id === catId ? { ...c, items: c.items.filter((it) => it.id !== itemId) } : c)));
  };
  const addItemToCategory = (catId, name) => {
    if (!name.trim()) return;
    setMenuData((prev) => prev.map((c) => (c.id === catId
      ? { ...c, items: [...c.items, { id: generateId(), name: name.trim(), unit: c.defaultUnit || '皿', cost: 0, defaultQty: 1 }] }
      : c)));
  };

  // ---- 本日だけメニュー ----
  const addDailyItem = (name, unit, cost) => {
    if (!name.trim()) return;
    const item = { id: 'd-' + generateId(), name: name.trim(), unit: unit.trim() || '皿', cost: Math.max(0, Number(cost) || 0) };
    setDailyItems((prev) => [...prev, item]);
    // 引き出しにも保存（同名があれば更新）
    setDailyPool((prev) => {
      const without = prev.filter((p) => p.name !== item.name);
      return [{ name: item.name, unit: item.unit, cost: item.cost }, ...without].slice(0, 50);
    });
  };
  const reuseFromPool = (p) => {
    if (dailyItems.some((d) => d.name === p.name)) return; // 重複追加しない
    setDailyItems((prev) => [...prev, { id: 'd-' + generateId(), name: p.name, unit: p.unit, cost: p.cost }]);
  };
  const removeDailyItem = (id) => setDailyItems((prev) => prev.filter((d) => d.id !== id));

  // ---- 味メモ ----
  const toggleFlavor = (f) => setFlavors((prev) => (prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]));

  // ---- データリセット ----
  const clearData = () => {
    if (!window.confirm('本日の記録（数量・味メモ）をリセットしますか？\n（メニュー表は消えません）')) return;
    setRecords({}); setFlavors([]);
    localStorage.removeItem(`bl_rec_${today}`);
    localStorage.removeItem(`bl_flavors_${today}`);
  };
  const resetMenuStructure = () => {
    if (!window.confirm('メニュー表を初期状態（焼肉メニュー）に戻しますか？\n（編集内容は消えます）')) return;
    setMenuData(INITIAL_MENU_DATA);
    setExpanded(INITIAL_MENU_DATA.map((c) => c.id));
    localStorage.setItem('bl_menu', JSON.stringify(INITIAL_MENU_DATA));
    localStorage.setItem('bl_menu_ver', String(MENU_VERSION));
    setShowUpdateNotice(true);
    setTimeout(() => setShowUpdateNotice(false), 3000);
  };

  // ---- 集計（原価で金額化） ----
  // 全品（定番＋本日だけ）をフラットに
  const allItems = useMemo(() => {
    const list = [];
    menuData.forEach((c) => c.items.forEach((it) => list.push({ ...it, category: c.category })));
    dailyItems.forEach((d) => list.push({ ...d, defaultQty: 1, category: '本日だけ' }));
    return list;
  }, [menuData, dailyItems]);

  const stats = useMemo(() => {
    const report = [];
    allItems.forEach((it) => {
      const rec = records[it.id];
      if (rec && (rec.supply > 0 || rec.remained > 0)) {
        const consumed = Math.max(0, (rec.supply || 0) - (rec.remained || 0));
        const cost = it.cost || 0;
        const wasteYen = (rec.remained || 0) * cost;
        const consumedYen = consumed * cost;
        const lossRate = rec.supply > 0 ? ((rec.remained / rec.supply) * 100) : 0;
        report.push({
          ...it, supply: rec.supply || 0, remained: rec.remained || 0,
          consumed, wasteYen, consumedYen, lossRate: parseFloat(lossRate.toFixed(1)),
        });
      }
    });
    return report;
  }, [allItems, records]);

  const totalWasteYen = stats.reduce((a, s) => a + s.wasteYen, 0);
  const totalConsumedYen = stats.reduce((a, s) => a + s.consumedYen, 0);
  const totalRemained = stats.reduce((a, s) => a + s.remained, 0);
  const wasteRanking = [...stats].sort((a, b) => b.wasteYen - a.wasteYen || b.remained - a.remained);
  const popularRanking = [...stats].sort((a, b) => b.consumed - a.consumed);

  // ---- CSV出力 ----
  const downloadCSV = () => {
    if (stats.length === 0) { alert('出力するデータがありません'); return; }
    const header = 'カテゴリ,品名,単位,原価,提供数,残数,消費数,廃棄ロス金額,提供原価,ロス率%';
    const esc = (s) => { const v = String(s ?? ''); return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; };
    const rows = stats.map((s) => [s.category, s.name, s.unit, s.cost, s.supply, s.remained, s.consumed, Math.round(s.wasteYen), Math.round(s.consumedYen), s.lossRate].map(esc).join(','));
    const flavorLine = flavors.length ? `\n本日の味,${flavors.join(' / ')}` : '';
    const csv = '﻿' + [header, ...rows].join('\n') + flavorLine;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `buffet_report_${today}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  };

  // パーツは「コンポーネント」ではなく描画関数として呼ぶ。
  // （<ItemCard/> と書くと毎回再マウントされ、編集中に入力欄のフォーカスが外れて操作しづらくなるため）
  const renderItemCard = ({ item, catId, isDaily }) => {
    const rec = records[item.id] || { supply: 0, remained: 0 };
    const editing = !isDaily && editingItem?.itemId === item.id;

    if (editing) {
      return (
        <div key={item.id} className="p-3 bg-amber-50">
          <div className="space-y-2">
            <input
              value={editingItem.name}
              onChange={(e) => setEditingItem({ ...editingItem, name: e.target.value })}
              placeholder="品名"
              className="w-full border border-amber-300 rounded-lg px-3 py-2 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-amber-400"
              autoFocus
            />
            <div className="flex gap-2">
              <input
                value={editingItem.unit}
                onChange={(e) => setEditingItem({ ...editingItem, unit: e.target.value })}
                placeholder="単位"
                className="w-20 border border-amber-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
              <div className="flex-1 flex items-center border border-amber-300 rounded-lg px-3 bg-white">
                <span className="text-slate-400 text-sm mr-1">原価¥</span>
                <input
                  type="number" inputMode="numeric"
                  value={editingItem.cost}
                  onChange={(e) => setEditingItem({ ...editingItem, cost: e.target.value })}
                  placeholder="0"
                  className="w-full py-2 text-sm focus:outline-none tabular"
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {UNIT_PRESETS.map((u) => (
                <button key={u} onClick={() => setEditingItem({ ...editingItem, unit: u })}
                  className={`px-2.5 py-1 rounded-full text-xs font-bold border ${editingItem.unit === u ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-slate-500 border-slate-200'}`}>{u}</button>
              ))}
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setEditingItem(null)} className="px-3 py-2 text-slate-500 text-sm font-bold">キャンセル</button>
              <button onClick={saveItemEdit} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-bold flex items-center gap-1"><Save size={16} />保存</button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div key={item.id} className="p-3 bg-white">
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-2 flex-1 min-w-0 border-l-4 border-indigo-500 pl-2">
            <span className="text-sm font-bold text-slate-800 truncate">{item.name.replace(/　?未確定.*$/, '')}</span>
            {item.name.includes('未確定') && (
              <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-medium border border-amber-200">未確定</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {item.cost > 0 && <span className="text-[10px] text-slate-400 tabular">原価{yen(item.cost)}</span>}
            <span className="text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-500 font-bold">{item.unit}</span>
            {isAdmin && !isDaily && (
              <>
                <button onClick={() => setEditingItem({ catId, itemId: item.id, name: item.name, unit: item.unit, cost: item.cost || 0 })} className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"><Edit size={15} /></button>
                <button onClick={() => deleteItem(catId, item.id)} className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded"><Trash2 size={15} /></button>
              </>
            )}
            {isDaily && (
              <button onClick={() => removeDailyItem(item.id)} className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded"><Trash2 size={15} /></button>
            )}
          </div>
        </div>

        <div className="flex gap-3">
          {renderCountBox({ label: '補充・提供', color: 'indigo', value: rec.supply || 0, item, field: 'supply' })}
          {renderCountBox({ label: '残数・廃棄', color: 'rose', value: rec.remained || 0, item, field: 'remained' })}
        </div>
      </div>
    );
  };

  // 数量入力ボックス（−／数字タップで直接入力／＋／クイックチップ）
  const renderCountBox = ({ label, color, value, item, field }) => {
    const cfg = cfgFor(item.unit);
    const c = color === 'indigo'
      ? { bg: 'bg-indigo-50/60', bd: 'border-indigo-100', tx: 'text-indigo-600', num: 'text-indigo-700', plus: 'bg-indigo-600 active:bg-indigo-700', chip: 'text-indigo-600 border-indigo-200' }
      : { bg: 'bg-rose-50/60', bd: 'border-rose-100', tx: 'text-rose-600', num: 'text-rose-700', plus: 'bg-rose-500 active:bg-rose-600', chip: 'text-rose-600 border-rose-200' };
    return (
      <div className={`flex-1 rounded-xl p-2 border ${c.bg} ${c.bd}`}>
        <div className={`text-[10px] font-bold text-center mb-1 ${c.tx}`}>{label}</div>
        <div className="flex items-center justify-between gap-1 mb-1.5">
          <button onClick={() => updateValue(item.id, field, -cfg.step)} className="w-10 h-10 flex items-center justify-center rounded-lg bg-white text-slate-700 shadow-sm border active:scale-95 transition-transform"><Minus size={18} /></button>
          <button
            onClick={() => setKeypad({ id: item.id, name: item.name, unit: item.unit, field, value: String(value || '') })}
            className={`flex flex-col items-center ${c.num} active:opacity-60`}
          >
            <span className="font-bold text-2xl tabular leading-none">{value}</span>
            <span className="text-[9px] opacity-60 font-bold">{item.unit}</span>
          </button>
          <button onClick={() => updateValue(item.id, field, cfg.step)} className={`w-10 h-10 flex items-center justify-center rounded-lg text-white shadow-md active:scale-95 transition-transform ${c.plus}`}><Plus size={20} /></button>
        </div>
        <div className="flex gap-1 justify-center">
          {cfg.chips.map((n) => (
            <button key={n} onClick={() => updateValue(item.id, field, n)} className={`text-[11px] font-bold px-2 py-0.5 rounded-full bg-white border ${c.chip} active:scale-95`}>+{n}</button>
          ))}
        </div>
      </div>
    );
  };

  // ==========================================
  // 描画
  // ==========================================
  return (
    <div className={`min-h-screen pb-28 font-sans text-slate-900 select-none ${isAdmin ? 'bg-indigo-50/50' : 'bg-slate-100'}`}>

      {showUpdateNotice && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[90%] max-w-sm bg-indigo-600 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center justify-center gap-3">
          <RefreshCw className="animate-spin shrink-0" size={22} />
          <span className="font-bold text-sm text-center">メニューを初期化しました (v{MENU_VERSION})</span>
        </div>
      )}

      {/* ヘッダー */}
      <header className={`sticky top-0 z-30 px-4 py-3 shadow-lg ${isAdmin ? 'bg-slate-800' : 'bg-indigo-900'} text-white`}>
        <div className="flex justify-between items-center mb-2">
          <div>
            <h1 className="text-lg font-bold tracking-tight flex items-center gap-2">
              <Flame size={20} /> 焼肉ロス管理
              {isAdmin && <span className="text-[10px] bg-amber-500 text-black px-1.5 py-0.5 rounded font-bold">編集モード</span>}
            </h1>
            <p className="text-[10px] opacity-70">{isAdmin ? 'メニュー・原価の編集中' : `${today} の記録`}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={toggleAdmin} className={`p-2 rounded-lg ${isAdmin ? 'bg-amber-500 text-black' : 'bg-white/10 hover:bg-white/20'}`}>{isAdmin ? <Unlock size={18} /> : <Lock size={18} />}</button>
            <button onClick={clearData} className="p-2 bg-white/10 hover:bg-rose-500/50 rounded-lg"><Trash2 size={18} /></button>
          </div>
        </div>
        {view === 'input' && !isAdmin && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/60" size={16} />
            <input
              type="text" placeholder="メニュー名で検索..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/20 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/40 focus:ring-2 focus:ring-white/50 focus:outline-none"
            />
          </div>
        )}
      </header>

      <main className="p-3 max-w-2xl mx-auto">
        {view === 'input' ? (
          <div className="space-y-4">

            {/* 本日の味メモ */}
            {!isAdmin && !searchQuery && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-3">
                <div className="text-[11px] font-bold text-slate-500 mb-2 flex items-center gap-1"><Sparkles size={13} className="text-amber-500" /> 本日の味（メモ）</div>
                <div className="flex flex-wrap gap-2">
                  {FLAVOR_PRESETS.map((f) => (
                    <button key={f} onClick={() => toggleFlavor(f)}
                      className={`px-3 py-1.5 rounded-full text-sm font-bold border transition-colors ${flavors.includes(f) ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-slate-500 border-slate-200'}`}>
                      {flavors.includes(f) && <Check size={13} className="inline mr-1" />}{f}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 本日だけメニュー */}
            {!searchQuery && (
              <div className="bg-white rounded-xl shadow-sm border-2 border-amber-200 overflow-hidden">
                <div className="px-4 py-3 bg-amber-50 flex items-center justify-between">
                  <span className="font-bold text-amber-800 text-sm flex items-center gap-1.5"><Sparkles size={16} /> 本日だけ（日替わり）</span>
                  <button onClick={() => { setNewDaily({ name: '', unit: '皿', cost: '' }); setDailyModal(true); }} className="bg-amber-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg flex items-center gap-1 active:scale-95"><Plus size={14} />追加</button>
                </div>
                {dailyItems.length === 0 ? (
                  <div className="px-4 py-4 text-center text-slate-400 text-xs">日替わりの品があれば「追加」から登録（翌日ボタンは自動で消えますが記録は残ります）</div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {dailyItems.map((it) => renderItemCard({ item: it, isDaily: true }))}
                  </div>
                )}
              </div>
            )}

            {/* 定番カテゴリ */}
            {menuData.map((cat) => {
              const filtered = isAdmin ? cat.items : cat.items.filter((i) => i.name.includes(searchQuery));
              if (!isAdmin && searchQuery && filtered.length === 0) return null;
              const isEditCat = editingCategory?.catId === cat.id;
              const open = expanded.includes(cat.id) || (searchQuery && filtered.length > 0);

              return (
                <div key={cat.id} className={`bg-white rounded-xl shadow-sm border overflow-hidden ${isAdmin ? 'border-indigo-200' : 'border-slate-200'}`}>
                  <div className={`w-full flex items-center justify-between p-4 border-b border-slate-50 ${isEditCat ? 'bg-amber-50' : 'bg-gradient-to-r from-slate-50 to-white'}`}>
                    {isEditCat ? (
                      <div className="flex-1 flex gap-2 items-center">
                        <input value={editingCategory.name} onChange={(e) => setEditingCategory({ ...editingCategory, name: e.target.value })} autoFocus
                          className="flex-1 border border-amber-300 rounded px-3 py-2 text-base font-bold bg-white focus:outline-none focus:ring-2 focus:ring-amber-400" />
                        <button onClick={saveCategoryEdit} className="p-2 text-green-600 bg-green-50 rounded-lg"><Save size={20} /></button>
                        <button onClick={() => setEditingCategory(null)} className="p-2 text-slate-400"><X size={20} /></button>
                      </div>
                    ) : (
                      <div className="flex-1 flex items-center justify-between cursor-pointer" onClick={() => toggleCategory(cat.id)}>
                        <div className="flex items-center gap-2">
                          <span className={`p-1 rounded ${isAdmin ? 'text-slate-400' : 'text-indigo-600 bg-indigo-50'}`}>{getIcon(cat.iconType)}</span>
                          <span className="font-bold text-slate-700 text-sm">{cat.category}</span>
                        </div>
                        {!isAdmin && (
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{filtered.length}</span>
                            {open ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
                          </div>
                        )}
                      </div>
                    )}
                    {isAdmin && !isEditCat && (
                      <div className="flex items-center gap-1 ml-2">
                        <button onClick={() => setEditingCategory({ catId: cat.id, name: cat.category })} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"><Edit size={18} /></button>
                        <button onClick={() => deleteCategory(cat.id)} className="p-2 text-red-400 hover:bg-red-50 hover:text-red-600 rounded-lg"><Trash2 size={18} /></button>
                        <button onClick={() => toggleCategory(cat.id)} className="p-2 text-slate-400 hover:bg-slate-100 rounded-lg ml-1 border-l">{open ? <ChevronDown size={20} /> : <ChevronRight size={20} />}</button>
                      </div>
                    )}
                  </div>

                  {open && (
                    <div className="divide-y divide-slate-100">
                      {filtered.map((item) => renderItemCard({ item, catId: cat.id }))}

                      {isAdmin && (
                        <div className="p-3 bg-slate-50 border-t border-dashed border-slate-300">
                          <div className="flex gap-2">
                            <input
                              type="text" placeholder="新しいメニューを追加..." value={newItemInputs[cat.id] || ''}
                              onChange={(e) => setNewItemInputs((p) => ({ ...p, [cat.id]: e.target.value }))}
                              onKeyDown={(e) => { if (e.key === 'Enter' && (newItemInputs[cat.id] || '').trim()) { addItemToCategory(cat.id, newItemInputs[cat.id]); setNewItemInputs((p) => ({ ...p, [cat.id]: '' })); } }}
                              className="flex-1 border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                            />
                            <button
                              onClick={() => { const v = (newItemInputs[cat.id] || '').trim(); if (v) { addItemToCategory(cat.id, v); setNewItemInputs((p) => ({ ...p, [cat.id]: '' })); } }}
                              disabled={!(newItemInputs[cat.id] || '').trim()}
                              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-500 text-sm font-bold flex items-center gap-1 disabled:opacity-50"
                            ><Plus size={16} />追加</button>
                          </div>
                          <p className="text-[10px] text-slate-400 mt-2">追加後、品名タップ（鉛筆）で原価を設定できます</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* 新規カテゴリ追加 */}
            {isAdmin && (
              <div className="bg-white p-5 rounded-xl shadow-sm border border-indigo-200 mt-6">
                <h3 className="font-bold text-indigo-800 text-sm mb-3 flex items-center gap-2"><Edit size={16} /> 新しいカテゴリを追加</h3>
                <div className="flex gap-3">
                  <input type="text" value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} placeholder="例: 海鮮・サイドメニュー"
                    onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
                    className="flex-1 border border-slate-300 rounded px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-indigo-400" />
                  <button onClick={handleAddCategory} disabled={!newCategoryName.trim()} className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-500 font-bold disabled:opacity-50">追加</button>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <button onClick={resetMenuStructure} className="text-xs text-slate-400 hover:text-red-500 flex items-center gap-1 font-bold"><AlertTriangle size={12} /> 初期メニュー（焼肉）に強制リセット</button>
                </div>
              </div>
            )}
          </div>
        ) : (
          // レポート
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-indigo-900 to-indigo-800 rounded-2xl p-5 text-white shadow-xl">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xs font-bold opacity-70 uppercase tracking-widest flex items-center gap-1"><BarChart3 size={14} /> 本日のレポート</h2>
                <button onClick={downloadCSV} className="flex items-center gap-1 bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg text-xs font-bold"><Download size={14} /> CSV保存</button>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="bg-black/20 rounded-xl p-3">
                  <p className="text-[10px] opacity-70 mb-1">廃棄ロス金額</p>
                  <p className="text-2xl font-bold text-rose-300 tabular">{yen(totalWasteYen)}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <p className="text-[10px] opacity-70 mb-1">提供分の原価</p>
                  <p className="text-2xl font-bold tabular">{yen(totalConsumedYen)}</p>
                </div>
              </div>
              <div className="flex gap-3 text-[11px] opacity-80">
                <span>記録品目: <b className="tabular">{stats.length}</b></span>
                <span>総廃棄数: <b className="tabular text-rose-300">{totalRemained}</b></span>
                {flavors.length > 0 && <span>味: <b>{flavors.join(' / ')}</b></span>}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="font-bold text-slate-700 flex items-center gap-2 px-1"><AlertTriangle size={18} className="text-rose-500" /> 廃棄ロス・ランキング（金額順）</h3>
              {wasteRanking.length === 0 ? (
                <div className="text-center py-10 bg-white rounded-xl border border-dashed border-slate-300 text-slate-400 text-sm">まだ廃棄データがありません</div>
              ) : wasteRanking.slice(0, 10).map((item, idx) => (
                <div key={`w-${item.id}`} className="bg-white p-3 rounded-xl shadow-sm border border-slate-100 flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${idx < 3 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-500'}`}>{idx + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-slate-800 truncate">{item.name.replace(/　?未確定.*$/, '')}</div>
                    <div className="text-[10px] text-slate-400">提供 {item.supply} / 残 {item.remained}{item.unit}・ロス率 {item.lossRate}%</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-rose-600 tabular">{item.cost > 0 ? yen(item.wasteYen) : `${item.remained}${item.unit}`}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-3 mt-8">
              <h3 className="font-bold text-slate-700 flex items-center gap-2 px-1"><Utensils size={18} className="text-indigo-500" /> 消費数ランキング（実食順）</h3>
              {popularRanking.slice(0, 5).map((item, idx) => (
                <div key={`p-${item.id}`} className="bg-white p-3 rounded-xl shadow-sm border border-slate-100 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm">{idx + 1}</div>
                  <div className="flex-1 min-w-0"><div className="text-sm font-bold text-slate-800 truncate">{item.name.replace(/　?未確定.*$/, '')}</div></div>
                  <div className="text-right"><div className="text-base font-bold text-indigo-600 tabular">{item.consumed}<span className="text-xs ml-0.5">{item.unit}</span></div></div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* 数量キーパッド モーダル */}
      {keypad && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-3" onClick={() => setKeypad(null)}>
          <div className="bg-white w-full max-w-sm rounded-2xl shadow-2xl p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{keypad.field === 'supply' ? '補充・提供' : '残数・廃棄'}</span>
              <button onClick={() => setKeypad(null)} className="text-slate-300 text-2xl leading-none">×</button>
            </div>
            <p className="font-bold text-lg text-slate-800 mb-3 truncate">{keypad.name}</p>
            <div className="flex items-center gap-2 bg-slate-50 rounded-xl p-4 mb-3 border">
              <input
                type="number" inputMode="numeric" autoFocus value={keypad.value}
                onChange={(e) => setKeypad({ ...keypad, value: e.target.value })}
                onFocus={(e) => e.target.select()}
                className="flex-1 text-center text-4xl font-bold bg-transparent outline-none tabular text-slate-800"
              />
              <span className="text-slate-400 font-bold">{keypad.unit}</span>
            </div>
            {/* ロール式ピッカー（iPhone/iPadではクルクル回るホイールで表示） */}
            <div className="mb-3">
              <div className="relative">
                <select
                  value=""
                  onChange={(e) => { if (e.target.value !== '') setKeypad({ ...keypad, value: e.target.value }); }}
                  className="w-full appearance-none bg-white border-2 border-indigo-200 rounded-xl py-3 pl-4 pr-10 text-base font-bold text-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                >
                  <option value="">🎡 ロールで数を選ぶ…</option>
                  {wheelValues(keypad.unit).map((v) => (
                    <option key={v} value={v}>{v}{keypad.unit}</option>
                  ))}
                </select>
                <ChevronDown size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-indigo-400 pointer-events-none" />
              </div>
            </div>

            {/* 単位に合わせたクイック加算 */}
            <div className="grid grid-cols-3 gap-2 mb-4">
              {cfgFor(keypad.unit).chips.map((n) => (
                <button key={n} onClick={() => setKeypad({ ...keypad, value: String(Math.round(((Number(keypad.value) || 0) + n) * 100) / 100) })} className="py-2.5 bg-slate-100 rounded-xl font-bold text-slate-700 active:bg-indigo-100">+{n}</button>
              ))}
            </div>
            <div className="flex gap-2">
              <button onClick={() => setKeypad({ ...keypad, value: '0' })} className="px-4 py-3 bg-slate-100 rounded-xl font-bold text-slate-500">クリア</button>
              <button onClick={() => { setExactValue(keypad.id, keypad.field, keypad.value); setKeypad(null); }} className="flex-1 py-3 bg-indigo-600 text-white rounded-xl font-bold active:bg-indigo-700">確定</button>
            </div>
          </div>
        </div>
      )}

      {/* 本日だけ追加 モーダル */}
      {dailyModal && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-3" onClick={() => setDailyModal(false)}>
          <div className="bg-white w-full max-w-sm rounded-2xl shadow-2xl p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <span className="font-bold text-amber-700 flex items-center gap-1.5"><Sparkles size={18} /> 本日だけメニューを追加</span>
              <button onClick={() => setDailyModal(false)} className="text-slate-300 text-2xl leading-none">×</button>
            </div>
            <input value={newDaily.name} onChange={(e) => setNewDaily({ ...newDaily, name: e.target.value })} placeholder="品名（例: 本日限定 上ハラミ）" autoFocus
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm font-bold mb-2 focus:outline-none focus:ring-2 focus:ring-amber-400" />
            <div className="flex gap-2 mb-2">
              <input value={newDaily.unit} onChange={(e) => setNewDaily({ ...newDaily, unit: e.target.value })} placeholder="単位"
                className="w-20 border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
              <div className="flex-1 flex items-center border border-slate-300 rounded-lg px-3">
                <span className="text-slate-400 text-sm mr-1">原価¥</span>
                <input type="number" inputMode="numeric" value={newDaily.cost} onChange={(e) => setNewDaily({ ...newDaily, cost: e.target.value })} placeholder="0"
                  className="w-full py-2.5 text-sm focus:outline-none tabular" />
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {UNIT_PRESETS.map((u) => (
                <button key={u} onClick={() => setNewDaily({ ...newDaily, unit: u })}
                  className={`px-2.5 py-1 rounded-full text-xs font-bold border ${newDaily.unit === u ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-slate-500 border-slate-200'}`}>{u}</button>
              ))}
            </div>
            <button
              onClick={() => { if (newDaily.name.trim()) { addDailyItem(newDaily.name, newDaily.unit, newDaily.cost); setDailyModal(false); } }}
              disabled={!newDaily.name.trim()}
              className="w-full py-3 bg-amber-500 text-white rounded-xl font-bold active:bg-amber-600 disabled:opacity-50 mb-4"
            >今日のメニューに追加</button>

            {dailyPool.length > 0 && (
              <div>
                <p className="text-[11px] font-bold text-slate-400 mb-2">引き出し（過去に使った日替わり・タップで再利用）</p>
                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                  {dailyPool.map((p) => (
                    <button key={p.name} onClick={() => { reuseFromPool(p); setDailyModal(false); }}
                      className="px-3 py-1.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200 active:bg-amber-100">
                      {p.name}{p.cost > 0 ? `（${yen(p.cost)}）` : ''}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 下部ナビ */}
      <nav className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-[340px] bg-white/90 backdrop-blur-md border border-slate-200 rounded-full p-2 shadow-2xl z-40 flex justify-between">
        <button onClick={() => setView('input')} className={`flex-1 flex flex-col items-center justify-center py-2 rounded-full transition-all ${view === 'input' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400'}`}>
          <ClipboardList size={22} className="mb-0.5" /><span className="text-[10px] font-bold">入力・管理</span>
        </button>
        <button onClick={() => setView('report')} className={`flex-1 flex flex-col items-center justify-center py-2 rounded-full transition-all ${view === 'report' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400'}`}>
          <BarChart3 size={22} className="mb-0.5" /><span className="text-[10px] font-bold">集計/出力</span>
        </button>
      </nav>
    </div>
  );
};

export default App;
