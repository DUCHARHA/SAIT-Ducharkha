
// Service Worker для обработки push уведомлений
const CACHE_NAME = 'ducharha-v1';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/script.js'
];

// Установка Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Обработка push уведомлений
self.addEventListener('push', event => {
  console.log('Push уведомление получено:', event);
  
  if (event.data) {
    const data = event.data.json();
    console.log('Данные уведомления:', data);
    
    const options = {
      body: data.body,
      icon: data.icon || '/static/icon-192x192.png',
      badge: '/static/badge-72x72.png',
      image: data.image,
      data: {
        order_number: data.order_number,
        url: data.url || '/'
      },
      actions: data.actions || [],
      requireInteraction: data.requireInteraction || false,
      silent: false,
      vibrate: [200, 100, 200],
      tag: data.tag || 'ducharha-notification'
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', event => {
  console.log('Клик по уведомлению:', event);
  
  event.notification.close();
  
  const data = event.notification.data;
  let url = data.url || '/';
  
  // Обработка кнопок действий
  if (event.action) {
    switch (event.action) {
      case 'view_order':
        url = `/my_orders?phone=${data.phone}`;
        break;
      case 'track_courier':
        url = `/track_order/${data.order_number}`;
        break;
      case 'repeat_order':
        url = `/repeat_order/${data.order_number}`;
        break;
      case 'cancel_order':
        url = `/cancel_order/${data.order_number}`;
        break;
      default:
        url = data.url || '/';
    }
  }
  
  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then(clientList => {
        // Проверяем, открыт ли уже сайт
        for (const client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Открываем новое окно
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// Обработка закрытия уведомления
self.addEventListener('notificationclose', event => {
  console.log('Уведомление закрыто:', event);
});

// Обработка сообщений от основного потока
self.addEventListener('message', event => {
  console.log('Сообщение от главного потока:', event.data);
  
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Активация Service Worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
