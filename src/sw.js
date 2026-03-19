const CACHE_NAME = 'ea-inflation-app-v1';

// The "App Shell" - files we want to download immediately and cache
const PRECACHE_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './assets/last_update.txt',
    './assets/maps/geo.csv',
    './assets/maps/coicop18.csv',
    './assets/maps/unit.csv'
];

// 1. Install Event: Cache the App Shell
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[Service Worker] Pre-caching offline pages');
                return cache.addAll(PRECACHE_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// 2. Activate Event: Clean up old caches if we update CACHE_NAME
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// 3. Fetch Event: Intercept network requests
self.addEventListener('fetch', event => {
    // CRITICAL: DuckDB uses HTTP Range requests to read chunks of the Parquet file.
    // Service Workers do not support 206 Partial Content responses well.
    // We MUST bypass the Service Worker completely for Range requests!
    if (event.request.headers.has('range') || event.request.url.endsWith('.parquet')) {
        return; // Let the browser handle this natively
    }

    // For all other requests (HTML, JS, CSS, CSVs), use a "Cache First, fallback to Network" strategy
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            if (cachedResponse) {
                return cachedResponse;
            }
            
            // If not in cache, fetch from network and dynamically cache it
            return fetch(event.request).then(networkResponse => {
                // Don't cache bad responses or 3rd party opaque responses
                if(!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }
                
                // Clone the response because it can only be consumed once
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            }).catch(err => {
                console.error('[Service Worker] Fetch failed:', err);
                // Optional: You could return a custom offline page here if needed
            });
        })
    );
});