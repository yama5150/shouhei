// localStorage への保存。壊れていたら握りつぶして空で返す(現場で白画面にしない)。
const K = { items: 'gk_items', recipes: 'gk_recipes', active: 'gk_active' };

export const load = (key, fallback) => {
  try {
    const v = JSON.parse(localStorage.getItem(K[key] ?? key));
    return v ?? fallback;
  } catch { return fallback; }
};

export const save = (key, value) => {
  try { localStorage.setItem(K[key] ?? key, JSON.stringify(value)); } catch { /* 容量超過は無視 */ }
};

export const newId = () => 'g-' + Math.random().toString(36).slice(2, 9) + '-' + Date.now().toString(36);
