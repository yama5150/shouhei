// Cyber Rose Crimson — Service Worker (軽量版)
// 巨大なindex.htmlはキャッシュしない(iOSの容量制限で破損するため)
const CACHE = 'crc-icons-v2';
const SMALL = ['./manifest.json','./icon-192.png','./icon-512.png',
               './icon-maskable-192.png','./icon-maskable-512.png','./icon-180.png'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SMALL).catch(()=>{})));
});

self.addEventListener('activate', e => {
  // 旧キャッシュ(壊れたHTMLを含む)を全部消す
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => k===CACHE ? null : caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;
  // HTMLは常にネットワークから取る(キャッシュしない)
  if (e.request.mode === 'navigate' || url.endsWith('.html') || url.endsWith('/')) return;
  // アイコン等の小物だけキャッシュを使う
  if (SMALL.some(s => url.endsWith(s.replace('./','')))) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
  }
});
