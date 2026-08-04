const CACHE_NAME = 'ea-inflation-app-v3';

// The "App Shell" — files to pre-cache for offline fallback
const PRECACHE_ASSETS = [
    './',
    './index.html',
    './ppi.html',
    './weights.html',
    './styles.css',
    './common.js',
    './index.js',
    './ppi.js',
    './weights.js',
    './manifest.json',
    './assets/maps/geo.csv',
    './assets/maps/coicop18.csv',
    './assets/maps/unit.csv',
    './assets/maps/nace_r2.csv',
    './assets/maps/geo_ppi.csv',
    './assets/maps/unit_ppi.csv'
];

// 1. Install Event: Pre-cache the App Shell for offline fallback
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[Service Worker] Pre-caching offline fallback');
                return cache.addAll(PRECACHE_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// 2. Activate Event: Clean up old caches
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

    // Network-Only with no-store for last_update indicators — always fresh
    if (event.request.url.endsWith('last_update.txt') ||
        event.request.url.endsWith('ppi_last_update.txt') ||
        event.request.url.endsWith('weights_last_update.txt')) {
        const noCacheRequest = new Request(event.request, { cache: 'no-store' });
        event.respondWith(
            fetch(noCacheRequest).catch(() => caches.match(event.request))
        );
        return;
    }

    // Network First, Cache Fallback for all app assets (HTML, JS, CSS, CSVs)
    // When online: always serve the latest version from the server
    // When offline: fall back to the pre-cached version
    event.respondWith(
        fetch(event.request)
            .then(networkResponse => {
                // Don't cache bad responses or 3rd party opaque responses
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }

                // Update cache with the fresh response
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            })
            .catch(() => {
                // Network failed — fall back to cache (offline support)
                return caches.match(event.request);
            })
    );
});
