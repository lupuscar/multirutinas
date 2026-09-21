const CACHE_NAME = 'optifit-pwa-v2';
const STATIC_ASSETS = [
  '/static/img/logo.png',
  '/static/img/logo_icon.png',
  '/static/img/pwa-icon-192.png',
  '/static/img/pwa-icon-512.png',
  '/static/img/apple-touch-icon.png',
  '/static/img/favicon-32.png',
  '/static/js/offline-sync.js',
  '/offline/',
  '/rutinas/',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('Pre-cache partial notice:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // No interceptar peticiones que no sean GET (como formularios POST de series o login)
  if (request.method !== 'GET') {
    return;
  }

  // 1. Navegación (Páginas HTML): Network First con fallback a caché y pantalla offline
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            return caches.match('/offline/');
          });
        })
    );
    return;
  }

  // 2. Recursos estáticos (Imágenes, Fuentes, CSS, CDN JS): Cache First con fallback a Network
  if (
    request.url.includes('/static/') ||
    request.url.includes('cdn.tailwindcss.com') ||
    request.url.includes('cdnjs.cloudflare.com') ||
    request.url.includes('cdn.jsdelivr.net')
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) {
          return cached;
        }
        return fetch(request).then((response) => {
          if (response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        });
      })
    );
    return;
  }

  // 3. Resto de peticiones: Red primero con fallback a caché
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
