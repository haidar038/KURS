const CACHE_NAME = 'krs-cache-1';
const urlsToCache = ['/'];

self.addEventListener('install', function (event) {
    console.log('[Service Worker] Installing Service Worker ...', event);
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then((cache) => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
            .catch((err) => {
                console.error('Error caching assets:', err);
            })
    );
});
self.addEventListener('activate', function (event) {
    console.log('[Service Worker] Activating Service Worker ...', event);
});
self.addEventListener('fetch', function (event) {
    console.log('[Service Worker] Fetching something ...', event);
    event.respondWith(
        caches.match(event.request).then((response) => {
            // Cache hit - return response from cache
            if (response) {
                return response;
            }

            // Clone the request for fetching from the network
            const fetchRequest = event.request.clone();

            return fetch(fetchRequest)
                .then((response) => {
                    // Check if we received a valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // Clone the response to store in the cache
                    const responseToCache = response.clone();

                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });

                    // Return the original response
                    return response;
                })
                .catch((err) => {
                    console.error('Fetch error:', err);
                    // TODO: Handle fetch error, maybe show offline page
                });
        })
    );
});
