
// Service Worker для обработки push уведомлений
const CACHE_NAME = 'ducharha-v1';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/script.js',
  '/static/notifications.js'
];

// Установка Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker: Установка...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Кэширование файлов');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('Service Worker: Ошибка при кэшировании:', error);
      })
  );
  self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', event => {
  console.log('Service Worker: Активация...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Удаление старого кэша:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Обработка запросов (базовое кэширование)
self.addEventListener('fetch', event => {
  // Игнорируем запросы к API и POST запросы
  if (event.request.method !== 'GET' || 
      event.request.url.includes('/api/') ||
      event.request.url.includes('/search') ||
      event.request.url.includes('/update_cart')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Возвращаем из кэша если есть, иначе загружаем из сети
        return response || fetch(event.request);
      })
      .catch(error => {
        console.error('Service Worker: Ошибка при обработке запроса:', error);
        return fetch(event.request);
      })
  );
});

// Обработка push уведомлений
self.addEventListener('push', event => {
  console.log('Service Worker: Push уведомление получено');
  
  if (!event.data) {
    console.log('Service Worker: Нет данных в push уведомлении');
    return;
  }

  try {
    const data = event.data.json();
    console.log('Service Worker: Данные уведомления:', data);
    
    const options = {
      body: data.body || 'Новое уведомление от Дучарха',
      icon: data.icon || '/static/icon-192x192.png',
      badge: '/static/icon-192x192.png',
      image: data.image,
      data: {
        order_number: data.order_number,
        phone: data.phone,
        url: data.url || '/'
      },
      actions: data.actions || [],
      requireInteraction: data.requireInteraction || false,
      silent: false,
      vibrate: [200, 100, 200],
      tag: data.tag || 'ducharha-notification'
    };
    
    const title = data.title || '🛒 Дучарха';
    
    event.waitUntil(
      self.registration.showNotification(title, options)
    );
  } catch (error) {
    console.error('Service Worker: Ошибка при обработке push:', error);
    
    // Показываем базовое уведомление в случае ошибки
    event.waitUntil(
      self.registration.showNotification('🛒 Дучарха', {
        body: 'У вас новое уведомление',
        icon: '/static/icon-192x192.png'
      })
    );
  }
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', event => {
  console.log('Service Worker: Клик по уведомлению');
  
  event.notification.close();
  
  const data = event.notification.data || {};
  let url = data.url || '/';
  
  // Обработка кнопок действий
  if (event.action) {
    console.log('Service Worker: Действие:', event.action);
    
    switch (event.action) {
      case 'view_order':
        url = `/my_orders?phone=${data.phone || ''}`;
        break;
      case 'track_courier':
        url = `/track_order/${data.order_number || ''}`;
        break;
      case 'repeat_order':
        url = `/repeat_order/${data.order_number || ''}`;
        break;
      case 'cancel_order':
        url = `/cancel_order/${data.order_number || ''}`;
        break;
      default:
        url = data.url || '/';
    }
  }
  
  console.log('Service Worker: Открываем URL:', url);
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        // Проверяем, открыт ли уже сайт
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            console.log('Service Worker: Фокусируем существующее окно');
            client.navigate(url);
            return client.focus();
          }
        }
        
        // Открываем новое окно
        if (clients.openWindow) {
          console.log('Service Worker: Открываем новое окно');
          return clients.openWindow(url);
        }
      })
      .catch(error => {
        console.error('Service Worker: Ошибка при обработке клика:', error);
      })
  );
});

// Обработка закрытия уведомления
self.addEventListener('notificationclose', event => {
  console.log('Service Worker: Уведомление закрыто');
});

// Обработка сообщений от основного потока
self.addEventListener('message', event => {
  console.log('Service Worker: Сообщение от главного потока:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('Service Worker: Принудительное обновление');
    self.skipWaiting();
  }
});

// Обработка ошибок
self.addEventListener('error', event => {
  console.error('Service Worker: Глобальная ошибка:', event.error);
});

self.addEventListener('unhandledrejection', event => {
  console.error('Service Worker: Необработанное отклонение Promise:', event.reason);
});

console.log('Service Worker: Скрипт загружен успешно');
