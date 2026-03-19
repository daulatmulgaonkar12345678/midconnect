const CACHE_NAME = 'udyogconnect-v1';
const APP_SHELL = [
  '/',
  '/seller/business-tools',
];

// Install — cache app shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL).catch(() => {
        console.log('[SW] Some app shell routes failed to cache');
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch handler
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests entirely (POST, PUT, DELETE etc.)
  if (request.method !== 'GET') {
    return;
  }

  // Skip API requests — never cache or intercept
  if (url.pathname.startsWith('/api')) {
    return;
  }

  // Skip Next.js RSC data requests — let them go straight to network
  // These are internal React Server Component fetches and should not be cached
  if (url.searchParams.has('_rsc')) {
    return;
  }

  // For navigation requests (HTML pages) — network first, cache fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, clone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then((cached) => {
            if (cached) return cached;
            return caches.match('/seller/business-tools').then((fallback) => {
              if (fallback) return fallback;
              // Ultimate fallback: return a basic offline page
              return new Response(
                '<html><body><h1>Offline</h1><p>Please check your internet connection.</p></body></html>',
                { status: 503, headers: { 'Content-Type': 'text/html' } }
              );
            });
          });
        })
    );
    return;
  }

  // For static assets — cache first, network fallback
  if (
    url.pathname.startsWith('/_next/static') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.jpg') ||
    url.pathname.endsWith('.svg') ||
    url.pathname.endsWith('.woff2')
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, clone);
            });
          }
          return response;
        }).catch(() => {
          // If fetch fails and nothing cached, return empty response
          return new Response('', { status: 503, statusText: 'Offline' });
        });
      })
    );
    return;
  }

  // Default — pass through to network, don't intercept
  // This avoids the "Failed to convert value to Response" error
  return;
});

// Listen for messages from the app
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
