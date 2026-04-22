/* Durham Civic Hub – Service Worker */
'use strict';

const CACHE = 'durhamcivichub-v2';
const PRECACHE = [
  '/',
  '/index.html',
  '/news.html',
  '/meetings.html',
  '/budget.html',
  '/budget-explorer.html',
  '/my-durham.html',
  '/resources.html',
  '/transit.html',
  '/connect.html',
  '/voting.html',
  '/glossary.html',
  '/styles.css',
  '/app.js',
  '/favicon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // Only handle GET requests for same-origin or cdn assets
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isJsonData   = isSameOrigin && url.pathname.endsWith('.json');

  e.respondWith(
    caches.match(e.request).then(cached => {
      const net = fetch(e.request).then(res => {
        if (res.ok && isSameOrigin) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => cached);
      // JSON data files: network-first so news/meetings stay fresh
      if (isJsonData) return net;
      // Everything else: cache-first
      return cached || net;
    })
  );
});
