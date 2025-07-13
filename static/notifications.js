
// Система управления push уведомлениями
class NotificationManager {
  constructor() {
    this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
    this.isSubscribed = false;
    this.swRegistration = null;
    this.applicationServerKey = this.urlB64ToUint8Array(
      'BEl62iUYgUivxIkv69yViEuiBIa40HcCWLrmaQoJb8BtN8v8IXhPPL7DhEJvkzNWGfHVCjO_pMjApJFOmMqGHbI'
    );
  }

  // Инициализация системы уведомлений
  async init() {
    if (!this.isSupported) {
      console.warn('Push уведомления не поддерживаются');
      return false;
    }

    try {
      // Регистрируем Service Worker
      this.swRegistration = await navigator.serviceWorker.register('/static/sw.js');
      console.log('Service Worker зарегистрирован:', this.swRegistration);

      // Проверяем текущую подписку
      await this.checkSubscription();
      
      return true;
    } catch (error) {
      console.error('Ошибка при инициализации:', error);
      return false;
    }
  }

  // Проверка текущей подписки
  async checkSubscription() {
    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      this.isSubscribed = !(subscription === null);
      
      if (this.isSubscribed) {
        console.log('Пользователь подписан на уведомления');
      } else {
        console.log('Пользователь не подписан на уведомления');
      }
      
      return this.isSubscribed;
    } catch (error) {
      console.error('Ошибка при проверке подписки:', error);
      return false;
    }
  }

  // Запрос разрешения на уведомления
  async requestPermission() {
    if (!this.isSupported) {
      throw new Error('Push уведомления не поддерживаются');
    }

    const permission = await Notification.requestPermission();
    
    if (permission === 'granted') {
      console.log('Разрешение на уведомления получено');
      return true;
    } else {
      console.log('Разрешение на уведомления отклонено');
      return false;
    }
  }

  // Подписка на уведомления
  async subscribe(phone) {
    try {
      const hasPermission = await this.requestPermission();
      if (!hasPermission) {
        throw new Error('Нет разрешения на уведомления');
      }

      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.applicationServerKey
      });

      console.log('Подписка создана:', subscription);

      // Отправляем подписку на сервер
      const response = await fetch('/api/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subscription: subscription,
          phone: phone
        })
      });

      if (response.ok) {
        this.isSubscribed = true;
        console.log('Подписка сохранена на сервере');
        return true;
      } else {
        throw new Error('Ошибка при сохранении подписки');
      }
    } catch (error) {
      console.error('Ошибка при подписке:', error);
      return false;
    }
  }

  // Отписка от уведомлений
  async unsubscribe() {
    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      
      if (subscription) {
        await subscription.unsubscribe();
        
        // Удаляем подписку с сервера
        await fetch('/api/unsubscribe', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            endpoint: subscription.endpoint
          })
        });
        
        this.isSubscribed = false;
        console.log('Подписка отменена');
        return true;
      }
    } catch (error) {
      console.error('Ошибка при отписке:', error);
      return false;
    }
  }

  // Показать уведомление для тестирования
  async showTestNotification() {
    if (!this.isSupported) {
      alert('Push уведомления не поддерживаются');
      return;
    }

    const hasPermission = await this.requestPermission();
    if (!hasPermission) {
      alert('Нет разрешения на уведомления');
      return;
    }

    const notification = new Notification('🛒 Тестовое уведомление от Дучарха', {
      body: 'Это тестовое уведомление для проверки работы системы',
      icon: '/static/icon-192x192.png',
      badge: '/static/badge-72x72.png',
      tag: 'test-notification'
    });

    setTimeout(() => {
      notification.close();
    }, 5000);
  }

  // Вспомогательная функция для конвертации ключа
  urlB64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
}

// Создаем глобальный экземпляр
const notificationManager = new NotificationManager();

// Инициализируем при загрузке страницы
document.addEventListener('DOMContentLoaded', async () => {
  const initialized = await notificationManager.init();
  
  if (initialized) {
    console.log('Система уведомлений инициализирована');
    
    // Показываем кнопку для подписки/отписки
    updateNotificationButton();
  }
});

// Обновляем кнопку уведомлений
function updateNotificationButton() {
  const button = document.getElementById('notification-toggle');
  if (!button) return;

  if (notificationManager.isSubscribed) {
    button.textContent = '🔕 Отключить уведомления';
    button.onclick = async () => {
      const success = await notificationManager.unsubscribe();
      if (success) {
        updateNotificationButton();
      }
    };
  } else {
    button.textContent = '🔔 Включить уведомления';
    button.onclick = async () => {
      const phone = prompt('Введите ваш номер телефона:');
      if (phone) {
        const success = await notificationManager.subscribe(phone);
        if (success) {
          updateNotificationButton();
        }
      }
    };
  }
}

// Автоматическая подписка при оформлении заказа
function subscribeOnOrder(phone) {
  if (notificationManager.isSupported && !notificationManager.isSubscribed) {
    notificationManager.subscribe(phone);
  }
}

// Экспортируем для использования в других файлах
window.notificationManager = notificationManager;
window.subscribeOnOrder = subscribeOnOrder;
