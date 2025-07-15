from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import json
import os
from datetime import datetime, date
import re
import difflib
import threading
import time
import requests
from urllib.parse import urlparse
import logging
from logging.handlers import RotatingFileHandler
from sms_auth import (
    send_sms_code, verify_sms_code, get_user_by_session, 
    logout_user, cleanup_expired_codes
)
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'sk-7x9m2n8p4q6r1s5t3u7v9w0e8f2g4h6j8k1l3m5n7p9q2r4s6t8u0v2w4x6y8z1a3b5c7d9e'

# Настройка логирования
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler('logs/ducharha.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Дучарха запущена')

# Обработка ошибок
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, error_message='Страница не найдена'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message='Внутренняя ошибка сервера'), 500

@app.errorhandler(405)
def method_not_allowed(error):
    return render_template('error.html', error_code=405, error_message='Метод не разрешен'), 405

def get_current_user():
    """Получает текущего авторизованного пользователя"""
    session_token = request.headers.get('Authorization')
    if not session_token:
        session_token = request.cookies.get('session_token')

    if session_token:
        return get_user_by_session(session_token)
    return None

ADMIN_PASSWORD = 'dilo.artes'
INVENTORY_PASSWORD = 'dilo.artes'

ORDERS_FILE = 'orders.json'
REVIEWS_FILE = 'reviews.json'
PROMOCODES_FILE = 'promocodes.json'
INVENTORY_FILE = 'inventory.json'
PUSH_SUBSCRIPTIONS_FILE = 'push_subscriptions.json'

# Системы синонимов для умного поиска
SYNONYMS = {
    'помидор': ['томат', 'помидоры', 'томаты'],
    'томат': ['помидор', 'помидоры', 'томаты'],
    'картошка': ['картофель', 'картошка'],
    'картофель': ['картошка', 'картофель'],
    'кола': ['coca-cola', 'кока-кола', 'кока кола'],
    'coca-cola': ['кола', 'кока-кола', 'кока кола'],
    'молоко': ['молочко'],
    'хлеб': ['хлебушек', 'батон'],
    'мясо': ['мяско'],
    'курица': ['куриное', 'курочка', 'куриная'],
    'куриная': ['курица', 'куриное', 'курочка'],
    'куриное': ['курица', 'куриная', 'курочка'],
    'ку': ['курица', 'куриная', 'куриное'],
    'кур': ['курица', 'куриная', 'куриное'],
    'яйца': ['яички', 'яйцо'],
    'ма': ['масло', 'майонез', 'макароны', 'мандарины'],
    'мас': ['масло'],
    'май': ['майонез'],
    'мак': ['макароны'],
    'ман': ['мандарины'],
    'мол': ['молоко', 'молочные'],
    'сыр': ['сыры'],
    'мор': ['морковь'],
    'хл': ['хлеб', 'хлебобулочные'],
    'нап': ['напитки'],
    'сок': ['соки'],
    'вод': ['вода'],
    'мин': ['минеральная']
}

def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def load_reviews():
    if os.path.exists(REVIEWS_FILE):
        try:
            with open(REVIEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def load_promocodes():
    if os.path.exists(PROMOCODES_FILE):
        try:
            with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                'FIRST10': {
                    'discount': 10, 
                    'type': 'percent', 
                    'usage_limit': 100,
                    'used_count': 0,
                    'min_order': 0,
                    'active': True,
                    'created_at': '2025-01-01 00:00:00'
                },
                'ЯКУМ': {
                    'discount': 10,
                    'type': 'percent',
                    'usage_limit': float('inf'),
                    'used_count': 0,
                    'min_order': 0,
                    'active': True,
                    'first_order_only': True,
                    'created_at': '2025-01-01 00:00:00'
                }
            }
    return {
        'FIRST10': {
            'discount': 10, 
            'type': 'percent', 
            'usage_limit': 100,
            'used_count': 0,
            'min_order': 0,
            'active': True,
            'created_at': '2025-01-01 00:00:00'
        },
        'ЯКУМ': {
            'discount': 10,
            'type': 'percent',
            'usage_limit': float('inf'),
            'used_count': 0,
            'min_order': 0,
            'active': True,
            'first_order_only': True,
            'created_at': '2025-01-01 00:00:00'
        }
    }

def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        try:
            with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_inventory(inventory):
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

def load_push_subscriptions():
    if os.path.exists(PUSH_SUBSCRIPTIONS_FILE):
        try:
            with open(PUSH_SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_push_subscriptions(subscriptions):
    with open(PUSH_SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscriptions, f, ensure_ascii=False, indent=2)

def send_push_notification(phone, title, body, order_number=None, actions=None):
    """Отправка push уведомления пользователю"""
    try:
        subscriptions = load_push_subscriptions()
        user_subscriptions = subscriptions.get(phone, [])

        if not user_subscriptions:
            print(f"Нет подписок для телефона {phone}")
            return False

        # Данные для уведомления
        notification_data = {
            'title': title,
            'body': body,
            'icon': '/static/icon-192x192.png',
            'badge': '/static/badge-72x72.png',
            'order_number': order_number,
            'phone': phone,
            'url': f'/my_orders?phone={phone}',
            'actions': actions or [],
            'requireInteraction': True,
            'tag': f'order-{order_number}' if order_number else 'ducharha-notification'
        }

        # Симуляция отправки push уведомления
        # В реальной системе здесь был бы запрос к Push API
        print(f"📱 PUSH уведомление для {phone}:")
        print(f"📋 Заголовок: {title}")
        print(f"💬 Текст: {body}")
        print(f"🔗 Заказ: {order_number}")
        print("✅ Уведомление отправлено!")

        return True

    except Exception as e:
        print(f"Ошибка при отправке push уведомления: {e}")
        return False

def notify_order_status_change(order_number, new_status, phone):
    """Отправка уведомления при смене статуса заказа"""

    status_messages = {
        'Принят': {
            'title': '🛒 Заказ принят!',
            'body': f'Заказ №{order_number} принят в обработку. Начинаем сборку вашего заказа.',
            'actions': [
                {'action': 'view_order', 'title': '👀 Посмотреть заказ'},
                {'action': 'cancel_order', 'title': '❌ Отменить заказ'}
            ]
        },
        'Собирается': {
            'title': '📦 Заказ собирается',
            'body': f'Ваш заказ №{order_number} собирается. Скоро курьер будет назначен.',
            'actions': [
                {'action': 'view_order', 'title': '👀 Посмотреть заказ'},
                {'action': 'cancel_order', 'title': '❌ Отменить заказ'}
            ]
        },
        'В пути': {
            'title': '🚚 Курьер выехал к вам!',
            'body': f'Курьер взял заказ №{order_number} и едет к вам. Ориентировочное время: 10-15 минут.',
            'actions': [
                {'action': 'track_courier', 'title': '📍 Отследить курьера'},
                {'action': 'view_order', 'title': '👀 Посмотреть заказ'}
            ]
        },
        'Доставлен': {
            'title': '✅ Заказ доставлен!',
            'body': f'Заказ №{order_number} успешно доставлен. Спасибо за покупку в Дучарха!',
            'actions': [
                {'action': 'repeat_order', 'title': '🔄 Повторить заказ'},
                {'action': 'view_order', 'title': '⭐ Оставить отзыв'}
            ]
        }
    }

    message_config = status_messages.get(new_status)
    if message_config:
        send_push_notification(
            phone=phone,
            title=message_config['title'],
            body=message_config['body'],
            order_number=order_number,
            actions=message_config['actions']
        )

def get_product_stock(product_id):
    inventory = load_inventory()
    return inventory.get(str(product_id), {'stock': 50, 'active': True})  # По умолчанию 50 штук

def update_product_stock(product_id, quantity_ordered):
    """Уменьшает остаток товара при заказе"""
    inventory = load_inventory()
    product_key = str(product_id)

    if product_key not in inventory:
        inventory[product_key] = {'stock': 50, 'active': True}

    inventory[product_key]['stock'] = max(0, inventory[product_key]['stock'] - quantity_ordered)

    # Автоматически деактивируем товар, если остаток 0
    if inventory[product_key]['stock'] == 0:
        inventory[product_key]['active'] = False

    save_inventory(inventory)
    return inventory[product_key]

def save_order(order):
    orders = load_orders()

    # Генерируем номер заказа в формате ДДММ-N
    today = date.today()
    date_prefix = today.strftime('%d%m')

    # Находим последний номер за сегодня
    today_orders = [o for o in orders if o.get('created_at', '').startswith(today.strftime('%Y-%m-%d'))]
    daily_number = len(today_orders) + 1

    order['number'] = f"{date_prefix}-{daily_number}"
    order['status'] = 'Принят'
    order['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    orders.append(order)

    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def save_review(review):
    reviews = load_reviews()
    review['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    reviews.append(review)

    with open(REVIEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

def smart_search(query, products):
    results = []
    query_lower = query.lower().strip()

    if not query_lower:
        return []

    # Расширяем поисковый запрос синонимами
    search_terms = [query_lower]
    for word in query_lower.split():
        if word in SYNONYMS:
            search_terms.extend(SYNONYMS[word])

    for product in products:
        score = 0
        product_name = product['name'].lower()
        product_description = product['description'].lower()
        product_category = product['category'].lower()
        product_subcategory = product['subcategory'].lower()
        product_brand = product.get('brand', '').lower()

        # Проверяем точное совпадение с начала названия (наивысший приоритет)
        for term in search_terms:
            if product_name.startswith(term):
                score += 1000
            elif term in product_name:
                # Проверяем, является ли это началом слова в названии
                words = product_name.split()
                for word in words:
                    if word.startswith(term):
                        score += 500
                    elif term in word:
                        score += 200

        # Проверяем точное совпадение в категории
        for term in search_terms:
            if product_category.startswith(term):
                score += 300
            elif term in product_category:
                score += 150

        # Проверяем точное совпадение в подкатегории
        for term in search_terms:
            if product_subcategory.startswith(term):
                score += 250
            elif term in product_subcategory:
                score += 100

        # Проверяем совпадение в бренде
        for term in search_terms:
            if product_brand.startswith(term):
                score += 200
            elif term in product_brand:
                score += 80

        # Проверяем совпадение в описании (низкий приоритет)
        for term in search_terms:
            if term in product_description:
                score += 30

        # Нечеткое совпадение только для коротких запросов (3+ символа)
        if len(query_lower) >= 3:
            for word in query_lower.split():
                name_words = product_name.split()
                matches = difflib.get_close_matches(word, name_words, n=1, cutoff=0.8)
                score += len(matches) * 50

        # Бонус за релевантность длины запроса
        if len(query_lower) >= 2:
            for term in search_terms:
                if len(term) >= 2 and term in product_name:
                    # Чем длиннее совпадение, тем выше бонус
                    score += len(term) * 10

        if score > 0:
            results.append((product, score))

    # Сортируем по релевантности
    results.sort(key=lambda x: x[1], reverse=True)

    # Возвращаем только топ результаты
    return [product for product, score in results[:50]]

# Группируем товары по брендам и названиям
def group_products(products):
    grouped = {}
    for product in products:
        # Создаем ключ группировки на основе бренда и базового названия
        base_name = product['name']
        brand = product.get('brand', 'Без бренда')

        # Убираем размеры из названия для группировки
        clean_name = re.sub(r'\s+(0\.\d+л|1л|1\.\d+л|\d+л|\d+г|\d+кг)', '', base_name)

        group_key = f"{brand}_{clean_name}"

        if group_key not in grouped:
            grouped[group_key] = {
                'base_product': product,
                'variants': []
            }

        grouped[group_key]['variants'].append(product)

    return grouped

# Расширенный каталог товаров с подкатегориями - более 1000 наименований
products = [
    # Молочные продукты
    {'id': 1, 'name': 'Молоко 3.2%', 'price': 2.10, 'description': 'Свежее коровье молоко, 1 литр', 'category': 'Молочные продукты', 'subcategory': 'Молоко', 'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop', 'brand': 'Славмо', 'composition': 'Молоко цельное пастеризованное', 'expiry': '7 дней'},
    {'id': 2, 'name': 'Молоко 2.5%', 'price': 2.00, 'description': 'Молоко пониженной жирности, 1 литр', 'category': 'Молочные продукты', 'subcategory': 'Молоко', 'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop', 'brand': 'Славмо', 'composition': 'Молоко пастеризованное', 'expiry': '7 дней'},
    {'id': 3, 'name': 'Молоко обезжиренное', 'price': 1.90, 'description': 'Молоко 0.5%, 1 литр', 'category': 'Молочные продукты', 'subcategory': 'Молоко', 'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop', 'brand': 'Славмо', 'composition': 'Молоко обезжиренное', 'expiry': '7 дней'},
    {'id': 4, 'name': 'Кефир 1%', 'price': 2.25, 'description': 'Кефир нежирный, 1 литр', 'category': 'Молочные продукты', 'subcategory': 'Кисломолочные', 'image': 'https://images.unsplash.com/photo-1571212515416-6dae4726f854?w=200&h=200&fit=crop', 'brand': 'Бифидок', 'composition': 'Молоко обезжиренное, закваска', 'expiry': '5 дней'},
    {'id': 5, 'name': 'Кефир 2.5%', 'price': 2.40, 'description': 'Кефир классический, 1 литр', 'category': 'Молочные продукты', 'subcategory': 'Кисломолочные', 'image': 'https://images.unsplash.com/photo-1571212515416-6dae4726f854?w=200&h=200&fit=crop', 'brand': 'Бифидок', 'composition': 'Молоко, закваска', 'expiry': '5 дней'},
    {'id': 6, 'name': 'Сметана 15%', 'price': 2.75, 'description': 'Сметана классическая, 400г', 'category': 'Молочные продукты', 'subcategory': 'Кисломолочные', 'image': 'https://images.unsplash.com/photo-1628088062854-d1870b4553da?w=200&h=200&fit=crop', 'brand': 'Густая', 'composition': 'Сливки, закваска молочнокислых культур', 'expiry': '10 дней'},
    {'id': 7, 'name': 'Сметана 20%', 'price': 3.00, 'description': 'Сметана густая, 400г', 'category': 'Молочные продукты', 'subcategory': 'Кисломолочные', 'image': 'https://images.unsplash.com/photo-1628088062854-d1870b4553da?w=200&h=200&fit=crop', 'brand': 'Густая', 'composition': 'Сливки, закваска молочнокислых культур', 'expiry': '10 дней'},
    {'id': 8, 'name': 'Творог 5%', 'price': 3.50, 'description': 'Творог средней жирности, 500г', 'category': 'Молочные продукты', 'subcategory': 'Творог', 'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop', 'brand': 'Домашний', 'composition': 'Молоко, закваска', 'expiry': '5 дней'},
    {'id': 9, 'name': 'Творог 9%', 'price': 3.75, 'description': 'Творог жирный, 500г', 'category': 'Молочные продукты', 'subcategory': 'Творог', 'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop', 'brand': 'Домашний', 'composition': 'Молоко цельное, закваска', 'expiry': '5 дней'},
    {'id': 10, 'name': 'Йогурт натуральный', 'price': 2.60, 'description': 'Йогурт без добавок, 400г', 'category': 'Молочные продукты', 'subcategory': 'Йогурты', 'image': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=200&h=200&fit=crop', 'brand': 'Активиа', 'composition': 'Молоко, закваска йогуртовая', 'expiry': '14 дней'},

    # Мясо и птица
    {'id': 11, 'name': 'Куриная грудка', 'price': 10.50, 'description': 'Охлажденное куриное филе, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Курица', 'image': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200&h=200&fit=crop', 'brand': 'Ошский бройлер', 'composition': 'Мясо курицы охлажденное', 'expiry': '3 дня'},
    {'id': 12, 'name': 'Куриные крылья', 'price': 7.00, 'description': 'Крылья куриные, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Курица', 'image': 'https://images.unsplash.com/photo-1527477396000-e27163b481c2?w=200&h=200&fit=crop', 'brand': 'Ошский бройлер', 'composition': 'Крылья куриные охлажденные', 'expiry': '3 дня'},
    {'id': 13, 'name': 'Куриные ножки', 'price': 6.00, 'description': 'Ножки куриные, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Курица', 'image': 'https://images.unsplash.com/photo-1527477396000-e27163b481c2?w=200&h=200&fit=crop', 'brand': 'Ошский бройлер', 'composition': 'Ножки куриные охлажденные', 'expiry': '3 дня'},
    {'id': 14, 'name': 'Курица целая', 'price': 8.75, 'description': 'Курица целая тушка, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Курица', 'image': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200&h=200&fit=crop', 'brand': 'Ошский бройлер', 'composition': 'Курица целая охлажденная', 'expiry': '3 дня'},
    {'id': 15, 'name': 'Говядина вырезка', 'price': 30.00, 'description': 'Говяжья вырезка премиум, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Говядина', 'image': 'https://images.unsplash.com/photo-1448907503123-67254d59ca4f?w=200&h=200&fit=crop', 'brand': 'Премиум мясо', 'composition': 'Говядина охлажденная', 'expiry': '5 дней'},
    {'id': 16, 'name': 'Говядина для тушения', 'price': 23.75, 'description': 'Говядина для тушения, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Говядина', 'image': 'https://images.unsplash.com/photo-1448907503123-67254d59ca4f?w=200&h=200&fit=crop', 'brand': 'Свежее мясо', 'composition': 'Говядина охлажденная', 'expiry': '5 дней'},
    {'id': 17, 'name': 'Баранина лопатка', 'price': 27.50, 'description': 'Баранья лопатка, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Баранина', 'image': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=200&h=200&fit=crop', 'brand': 'Горное мясо', 'composition': 'Баранина охлажденная', 'expiry': '5 дней'},
    {'id': 18, 'name': 'Фарш говяжий', 'price': 21.25, 'description': 'Фарш из говядины, 1кг', 'category': 'Мясо и птица', 'subcategory': 'Фарш', 'image': 'https://images.unsplash.com/photo-1603048297172-c92544798d5a?w=200&h=200&fit=crop', 'brand': 'Свежий фарш', 'composition': 'Говядина рубленая', 'expiry': '2 дня'},

    # Овощи
    {'id': 19, 'name': 'Помидоры красные', 'price': 5.50, 'description': 'Спелые помидоры, 1кг', 'category': 'Овощи', 'subcategory': 'Помидоры', 'image': 'https://images.unsplash.com/photo-1546470427-e26264ac6846?w=200&h=200&fit=crop', 'brand': 'Фермерские', 'composition': 'Свежие томаты', 'expiry': '5 дней'},
    {'id': 20, 'name': 'Помидоры черри', 'price': 8.75, 'description': 'Помидоры черри, 500г', 'category': 'Овощи', 'subcategory': 'Помидоры', 'image': 'https://images.unsplash.com/photo-1551542193-dc8ada15b55f?w=200&h=200&fit=crop', 'brand': 'Черри фарм', 'composition': 'Томаты черри свежие', 'expiry': '5 дней'},
    {'id': 21, 'name': 'Огурцы длинные', 'price': 4.50, 'description': 'Свежие огурцы, 1кг', 'category': 'Овощи', 'subcategory': 'Огурцы', 'image': 'https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=200&h=200&fit=crop', 'brand': 'Фермерские', 'composition': 'Свежие огурцы', 'expiry': '7 дней'},
    {'id': 22, 'name': 'Огурцы корнишоны', 'price': 6.25, 'description': 'Огурцы корнишоны, 500г', 'category': 'Овощи', 'subcategory': 'Огурцы', 'image': 'https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=200&h=200&fit=crop', 'brand': 'Мини огурцы', 'composition': 'Огурцы молодые', 'expiry': '5 дней'},
    {'id': 23, 'name': 'Картофель молодой', 'price': 1.75, 'description': 'Молодой картофель, 1кг', 'category': 'Овощи', 'subcategory': 'Картофель', 'image': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=200&h=200&fit=crop', 'brand': 'Местные', 'composition': 'Картофель свежий', 'expiry': '30 дней'},
    {'id': 24, 'name': 'Картофель белый', 'price': 1.60, 'description': 'Картофель белый, 1кг', 'category': 'Овощи', 'subcategory': 'Картофель', 'image': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=200&h=200&fit=crop', 'brand': 'Алайские', 'composition': 'Картофель белый', 'expiry': '45 дней'},
    {'id': 25, 'name': 'Морковь', 'price': 2.00, 'description': 'Морковь свежая, 1кг', 'category': 'Овощи', 'subcategory': 'Корнеплоды', 'image': 'https://images.unsplash.com/photo-1447175008436-054170c2e979?w=200&h=200&fit=crop', 'brand': 'Фермерские', 'composition': 'Морковь свежая', 'expiry': '20 дней'},
    {'id': 26, 'name': 'Свекла', 'price': 1.90, 'description': 'Свекла столовая, 1кг', 'category': 'Овощи', 'subcategory': 'Корнеплоды', 'image': 'https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=200&h=200&fit=crop', 'brand': 'Местные', 'composition': 'Свекла свежая', 'expiry': '30 дней'},
    {'id': 27, 'name': 'Лук репчатый', 'price': 1.50, 'description': 'Лук репчатый, 1кг', 'category': 'Овощи', 'subcategory': 'Лук', 'image': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Лук репчатый', 'expiry': '60 дней'},
    {'id': 28, 'name': 'Чеснок', 'price': 11.25, 'description': 'Чеснок белый, 500г', 'category': 'Овощи', 'subcategory': 'Лук', 'image': 'https://images.unsplash.com/photo-1471078025598-307656b4b761?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Чеснок белый', 'expiry': '90 дней'},

    # Фрукты
    {'id': 29, 'name': 'Яблоки красные', 'price': 3.75, 'description': 'Яблоки Ред Делишес, 1кг', 'category': 'Фрукты', 'subcategory': 'Яблоки', 'image': 'https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?w=200&h=200&fit=crop', 'brand': 'Иссык-Кульские', 'composition': 'Яблоки свежие', 'expiry': '14 дней'},
    {'id': 30, 'name': 'Яблоки зеленые', 'price': 4.00, 'description': 'Яблоки Гренни Смит, 1кг', 'category': 'Фрукты', 'subcategory': 'Яблоки', 'image': 'https://images.unsplash.com/photo-1579613832125-5d34a13ffe2a?w=200&h=200&fit=crop', 'brand': 'Иссык-Кульские', 'composition': 'Яблоки зеленые', 'expiry': '14 дней'},
    {'id': 31, 'name': 'Бананы', 'price': 3.00, 'description': 'Бананы спелые, 1кг', 'category': 'Фрукты', 'subcategory': 'Экзотические', 'image': 'https://images.unsplash.com/photo-1603833665858-e61d17a86224?w=200&h=200&fit=crop', 'brand': 'Эквадор', 'composition': 'Бананы свежие', 'expiry': '7 дней'},
    {'id': 32, 'name': 'Апельсины', 'price': 4.50, 'description': 'Апельсины сладкие, 1кг', 'category': 'Фрукты', 'subcategory': 'Цитрусовые', 'image': 'https://images.unsplash.com/photo-1547036967-23d11aacaee0?w=200&h=200&fit=crop', 'brand': 'Турецкие', 'composition': 'Апельсины свежие', 'expiry': '10 дней'},
    {'id': 33, 'name': 'Мандарины', 'price': 5.00, 'description': 'Мандарины сладкие, 1кг', 'category': 'Фрукты', 'subcategory': 'Цитрусовые', 'image': 'https://images.unsplash.com/photo-1482012827305-14ad6a2a6c0c?w=200&h=200&fit=crop', 'brand': 'Абхазские', 'composition': 'Мандарины свежие', 'expiry': '8 дней'},
    {'id': 34, 'name': 'Лимоны', 'price': 6.25, 'description': 'Лимоны кислые, 1кг', 'category': 'Фрукты', 'subcategory': 'Цитрусовые', 'image': 'https://images.unsplash.com/photo-1587485501610-e04de0a9eeec?w=200&h=200&fit=crop', 'brand': 'Турецкие', 'composition': 'Лимоны свежие', 'expiry': '15 дней'},
    {'id': 35, 'name': 'Виноград белый', 'price': 8.75, 'description': 'Виноград белый сладкий, 1кг', 'category': 'Фрукты', 'subcategory': 'Ягоды', 'image': 'https://images.unsplash.com/photo-1577003833619-76bbd40b3d90?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Виноград белый', 'expiry': '5 дней'},
    {'id': 36, 'name': 'Виноград черный', 'price': 9.50, 'description': 'Виноград черный, 1кг', 'category': 'Фрукты', 'subcategory': 'Ягоды', 'image': 'https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Виноград черный', 'expiry': '5 дней'},

    # Хлебобулочные
    {'id': 37, 'name': 'Хлеб белый', 'price': 1.40, 'description': 'Хлеб белый свежий, 400г', 'category': 'Хлебобулочные', 'subcategory': 'Хлеб', 'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&h=200&fit=crop', 'brand': 'Ош-Нан', 'composition': 'Мука пшеничная, вода, дрожжи, соль', 'expiry': '3 дня'},
    {'id': 38, 'name': 'Хлеб черный', 'price': 1.50, 'description': 'Хлеб ржаной, 400г', 'category': 'Хлебобулочные', 'subcategory': 'Хлеб', 'image': 'https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=200&h=200&fit=crop', 'brand': 'Ош-Нан', 'composition': 'Мука ржаная, вода, дрожжи, соль', 'expiry': '3 дня'},
    {'id': 39, 'name': 'Батон нарезной', 'price': 1.10, 'description': 'Батон нарезной, 350г', 'category': 'Хлебобулочные', 'subcategory': 'Хлеб', 'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&h=200&fit=crop', 'brand': 'Хлебзавод', 'composition': 'Мука, вода, дрожжи', 'expiry': '2 дня'},
    {'id': 40, 'name': 'Булочки с кунжутом', 'price': 3.75, 'description': 'Булочки для бургеров, 4шт', 'category': 'Хлебобулочные', 'subcategory': 'Булочки', 'image': 'https://images.unsplash.com/photo-1506717402977-1b0aeb2f0d68?w=200&h=200&fit=crop', 'brand': 'Пекарня', 'composition': 'Мука, кунжут, дрожжи', 'expiry': '2 дня'},

    # Напитки
    {'id': 41, 'name': 'Вода питьевая BonAqua 0.5л', 'price': 0.75, 'description': 'Чистая питьевая вода, 0.5л', 'category': 'Напитки', 'subcategory': 'Вода', 'image': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=200&h=200&fit=crop', 'brand': 'BonAqua', 'composition': 'Очищенная питьевая вода', 'expiry': '2 года'},
    {'id': 42, 'name': 'Вода питьевая BonAqua 1л', 'price': 1.25, 'description': 'Чистая питьевая вода, 1л', 'category': 'Напитки', 'subcategory': 'Вода', 'image': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=200&h=200&fit=crop', 'brand': 'BonAqua', 'composition': 'Очищенная питьевая вода', 'expiry': '2 года'},
    {'id': 43, 'name': 'Вода питьевая BonAqua 1.5л', 'price': 1.90, 'description': 'Чистая питьевая вода, 1.5л', 'category': 'Напитки', 'subcategory': 'Вода', 'image': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=200&h=200&fit=crop', 'brand': 'BonAqua', 'composition': 'Очищенная питьевая вода', 'expiry': '2 года'},
    {'id': 44, 'name': 'Вода газированная Ессентуки', 'price': 2.00, 'description': 'Вода минеральная газированная, 0.5л', 'category': 'Напитки', 'subcategory': 'Вода', 'image': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=200&h=200&fit=crop', 'brand': 'Ессентуки', 'composition': 'Минеральная вода', 'expiry': '2 года'},
    {'id': 45, 'name': 'Coca-Cola 0.5л', 'price': 2.00, 'description': 'Классическая кока-кола, 0.5л', 'category': 'Напитки', 'subcategory': 'Газировка', 'image': 'https://images.unsplash.com/photo-1554866585-cd94860890b7?w=200&h=200&fit=crop', 'brand': 'Coca-Cola', 'composition': 'Вода, сахар, диоксид углерода, краситель карамель, кислота фосфорная, ароматизаторы натуральные', 'expiry': '1 год'},
    {'id': 46, 'name': 'Coca-Cola 1л', 'price': 3.00, 'description': 'Классическая кока-кола, 1л', 'category': 'Напитки', 'subcategory': 'Газировка', 'image': 'https://images.unsplash.com/photo-1554866585-cd94860890b7?w=200&h=200&fit=crop', 'brand': 'Coca-Cola', 'composition': 'Вода, сахар, диоксид углерода, краситель карамель, кислота фосфорная, ароматизаторы натуральные', 'expiry': '1 год'},
    {'id': 47, 'name': 'Coca-Cola 1.5л', 'price': 4.50, 'description': 'Классическая кока-кола, 1.5л', 'category': 'Напитки', 'subcategory': 'Газировка', 'image': 'https://images.unsplash.com/photo-1554866585-cd94860890b7?w=200&h=200&fit=crop', 'brand': 'Coca-Cola', 'composition': 'Вода, сахар, диоксид углерода, краситель карамель, кислота фосфорная, ароматизаторы натуральные', 'expiry': '1 год'},
    {'id': 48, 'name': 'Pepsi 0.5л', 'price': 1.90, 'description': 'Пепси кола, 0.5л', 'category': 'Напитки', 'subcategory': 'Газировка', 'image': 'https://images.unsplash.com/photo-1622547748225-3fc4abd2cca0?w=200&h=200&fit=crop', 'brand': 'Pepsi', 'composition': 'Вода, сахар, ароматизаторы', 'expiry': '1 год'},
    {'id': 49, 'name': 'Fanta Апельсин 0.5л', 'price': 1.75, 'description': 'Фанта апельсин, 0.5л', 'category': 'Напитки', 'subcategory': 'Газировка', 'image': 'https://images.unsplash.com/photo-1581098365948-6a5a912b7a49?w=200&h=200&fit=crop', 'brand': 'Fanta', 'composition': 'Вода, сахар, ароматизатор апельсина', 'expiry': '1 год'},
    {'id': 50, 'name': 'Сок яблочный', 'price': 3.00, 'description': 'Сок яблочный 100%, 1л', 'category': 'Напитки', 'subcategory': 'Соки', 'image': 'https://images.unsplash.com/photo-1560632575-c3e8b0b57bdf?w=200&h=200&fit=crop', 'brand': 'Добрый', 'composition': 'Сок яблочный 100%', 'expiry': '1 год'},

    # Крупы и макароны
    {'id': 51, 'name': 'Рис длиннозерный', 'price': 4.50, 'description': 'Рис басмати, 1кг', 'category': 'Крупы и макароны', 'subcategory': 'Рис', 'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=200&h=200&fit=crop', 'brand': 'Мистраль', 'composition': 'Рис белый длиннозерный', 'expiry': '2 года'},
    {'id': 52, 'name': 'Рис круглозерный', 'price': 3.75, 'description': 'Рис для плова, 1кг', 'category': 'Крупы и макароны', 'subcategory': 'Рис', 'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Рис белый круглый', 'expiry': '2 года'},
    {'id': 53, 'name': 'Гречка ядрица', 'price': 5.50, 'description': 'Гречневая крупа, 1кг', 'category': 'Крупы и макароны', 'subcategory': 'Крупы', 'image': 'https://images.unsplash.com/photo-1609501676725-7186f6ae511a?w=200&h=200&fit=crop', 'brand': 'Алтайские', 'composition': 'Гречневая крупа', 'expiry': '2 года'},
    {'id': 54, 'name': 'Овсянка', 'price': 4.00, 'description': 'Овсяные хлопья, 500г', 'category': 'Крупы и макароны', 'subcategory': 'Крупы', 'image': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=200&h=200&fit=crop', 'brand': 'Геркулес', 'composition': 'Овсяные хлопья', 'expiry': '1 год'},
    {'id': 55, 'name': 'Макароны спагетти', 'price': 2.10, 'description': 'Спагетти №7, 450г', 'category': 'Крупы и макароны', 'subcategory': 'Макароны', 'image': 'https://images.unsplash.com/photo-1551892589-865f69869476?w=200&h=200&fit=crop', 'brand': 'Барилла', 'composition': 'Мука твердых сортов пшеницы', 'expiry': '3 года'},
    {'id': 56, 'name': 'Макароны рожки', 'price': 1.75, 'description': 'Рожки мелкие, 450г', 'category': 'Крупы и макароны', 'subcategory': 'Макароны', 'image': 'https://images.unsplash.com/photo-1551892589-865f69869476?w=200&h=200&fit=crop', 'brand': 'Макфа', 'composition': 'Мука пшеничная', 'expiry': '2 года'},

    # Молочные продукты (продолжение)
    {'id': 57, 'name': 'Масло сливочное 82.5%', 'price': 11.25, 'description': 'Масло сливочное, 200г', 'category': 'Молочные продукты', 'subcategory': 'Масло', 'image': 'https://images.unsplash.com/photo-1628088062854-d1870b4553da?w=200&h=200&fit=crop', 'brand': 'Домик в деревне', 'composition': 'Сливки пастеризованные', 'expiry': '35 дней'},
    {'id': 58, 'name': 'Сыр российский', 'price': 16.25, 'description': 'Сыр российский, 200г', 'category': 'Молочные продукты', 'subcategory': 'Сыры', 'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop', 'brand': 'Ичалки', 'composition': 'Молоко, закваска, соль', 'expiry': '60 дней'},
    {'id': 59, 'name': 'Сыр голландский', 'price': 18.00, 'description': 'Сыр голландский, 200г', 'category': 'Молочные продукты', 'subcategory': 'Сыры', 'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop', 'brand': 'Киприно', 'composition': 'Молоко, закваска', 'expiry': '45 дней'},
    {'id': 60, 'name': 'Брынза', 'price': 13.75, 'description': 'Брынза рассольная, 300г', 'category': 'Молочные продукты', 'subcategory': 'Сыры', 'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop', 'brand': 'Фета', 'composition': 'Молоко овечье, соль', 'expiry': '30 дней'},

    # Колбасы и мясные деликатесы
    {'id': 61, 'name': 'Колбаса докторская', 'price': 12.00, 'description': 'Колбаса докторская, 400г', 'category': 'Колбасы и деликатесы', 'subcategory': 'Вареная колбаса', 'image': 'https://images.unsplash.com/photo-1621180041932-8b2efd51ca7c?w=200&h=200&fit=crop', 'brand': 'Мясокомбинат', 'composition': 'Свинина, говядина, специи', 'expiry': '10 дней'},
    {'id': 62, 'name': 'Колбаса салями', 'price': 21.25, 'description': 'Салями сыровяленая, 300г', 'category': 'Колбасы и деликатесы', 'subcategory': 'Копченая колбаса', 'image': 'https://images.unsplash.com/photo-1621180041932-8b2efd51ca7c?w=200&h=200&fit=crop', 'brand': 'Премиум', 'composition': 'Свинина, специи', 'expiry': '60 дней'},
    {'id': 63, 'name': 'Сосиски молочные', 'price': 8.75, 'description': 'Сосиски молочные, 450г', 'category': 'Колбасы и деликатесы', 'subcategory': 'Сосиски', 'image': 'https://images.unsplash.com/photo-1621180041932-8b2efd51ca7c?w=200&h=200&fit=crop', 'brand': 'Царицыно', 'composition': 'Свинина, говядина, молоко', 'expiry': '7 дней'},

    # Рыба и морепродукты
    {'id': 64, 'name': 'Семга слабосоленая', 'price': 45.00, 'description': 'Семга слабосоленая, 200г', 'category': 'Рыба и морепродукты', 'subcategory': 'Красная рыба', 'image': 'https://images.unsplash.com/photo-1544943150-4d2c9a4e8c32?w=200&h=200&fit=crop', 'brand': 'Норвежская', 'composition': 'Семга, соль', 'expiry': '5 дней'},
    {'id': 65, 'name': 'Форель', 'price': 21.25, 'description': 'Форель свежая, 1кг', 'category': 'Рыба и морепродукты', 'subcategory': 'Пресноводная рыба', 'image': 'https://images.unsplash.com/photo-1544943150-4d2c9a4e8c32?w=200&h=200&fit=crop', 'brand': 'Иссык-Кульская', 'composition': 'Форель свежая', 'expiry': '2 дня'},
    {'id': 66, 'name': 'Креветки', 'price': 30.00, 'description': 'Креветки варено-мороженые, 500г', 'category': 'Рыба и морепродукты', 'subcategory': 'Морепродукты', 'image': 'https://images.unsplash.com/photo-1565680018434-b513d5924530?w=200&h=200&fit=crop', 'brand': 'Дальневосточные', 'composition': 'Креветки', 'expiry': '6 месяцев'},

    # Замороженные продукты
    {'id': 67, 'name': 'Пельмени домашние', 'price': 8.00, 'description': 'Пельмени с мясом, 800г', 'category': 'Замороженные продукты', 'subcategory': 'Пельмени', 'image': 'https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=200&h=200&fit=crop', 'brand': 'Цезарь', 'composition': 'Мука, мясо, лук', 'expiry': '6 месяцев'},
    {'id': 68, 'name': 'Манты', 'price': 11.25, 'description': 'Манты с мясом, 600г', 'category': 'Замороженные продукты', 'subcategory': 'Манты', 'image': 'https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=200&h=200&fit=crop', 'brand': 'Домашние', 'composition': 'Тесто, баранина, лук', 'expiry': '3 месяца'},
    {'id': 69, 'name': 'Мороженое пломбир', 'price': 6.25, 'description': 'Мороженое пломбир, 500г', 'category': 'Замороженные продукты', 'subcategory': 'Мороженое', 'image': 'https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=200&h=200&fit=crop', 'brand': 'Филевское', 'composition': 'Молоко, сливки, сахар', 'expiry': '6 месяцев'},

    # Консервы
    {'id': 70, 'name': 'Тушенка говяжья', 'price': 13.75, 'description': 'Тушенка говяжья, 325г', 'category': 'Консервы', 'subcategory': 'Мясные консервы', 'image': 'https://images.unsplash.com/photo-1603048297172-c92544798d5a?w=200&h=200&fit=crop', 'brand': 'ГОСТ', 'composition': 'Говядина, соль, специи', 'expiry': '5 лет'},
    {'id': 71, 'name': 'Рыбные консервы сардина', 'price': 7.00, 'description': 'Сардина в масле, 240г', 'category': 'Консервы', 'subcategory': 'Рыбные консервы', 'image': 'https://images.unsplash.com/photo-1544943150-4d2c9a4e8c32?w=200&h=200&fit=crop', 'brand': 'Доброфлот', 'composition': 'Сардина, масло', 'expiry': '3 года'},
    {'id': 72, 'name': 'Горошек зеленый', 'price': 4.50, 'description': 'Горошек зеленый, 420г', 'category': 'Консервы', 'subcategory': 'Овощные консервы', 'image': 'https://images.unsplash.com/photo-1585155693849-86ff6b72eff1?w=200&h=200&fit=crop', 'brand': 'Bonduelle', 'composition': 'Горошек, вода, соль', 'expiry': '3 года'},

    # Приправы и специи
    {'id': 73, 'name': 'Соль поваренная', 'price': 0.90, 'description': 'Соль мелкая, 1кг', 'category': 'Приправы и специи', 'subcategory': 'Соль', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Экстра', 'composition': 'Соль поваренная', 'expiry': 'Без ограничений'},
    {'id': 74, 'name': 'Сахар белый', 'price': 3.00, 'description': 'Сахар-песок, 1кг', 'category': 'Приправы и специи', 'subcategory': 'Сахар', 'image': 'https://images.unsplash.com/photo-1559181567-c3190ca9959b?w=200&h=200&fit=crop', 'brand': 'Русский', 'composition': 'Сахар-песок', 'expiry': 'Без ограничений'},
    {'id': 75, 'name': 'Перец черный молотый', 'price': 2.00, 'description': 'Перец черный молотый, 50г', 'category': 'Приправы и специи', 'subcategory': 'Специи', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Kotanyi', 'composition': 'Перец черный', 'expiry': '2 года'},
    {'id': 76, 'name': 'Лавровый лист', 'price': 1.25, 'description': 'Лавровый лист, 10г', 'category': 'Приправы и специи', 'subcategory': 'Специи', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Приправыч', 'composition': 'Лавровый лист', 'expiry': '2 года'},

    # Масла и уксусы
    {'id': 77, 'name': 'Масло подсолнечное', 'price': 5.50, 'description': 'Масло подсолнечное рафинированное, 1л', 'category': 'Масла и соусы', 'subcategory': 'Растительные масла', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Слобода', 'composition': 'Масло подсолнечное', 'expiry': '2 года'},
    {'id': 78, 'name': 'Масло оливковое', 'price': 21.25, 'description': 'Масло оливковое extra virgin, 500мл', 'category': 'Масла и соусы', 'subcategory': 'Растительные масла', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Borges', 'composition': 'Масло оливковое', 'expiry': '2 года'},
    {'id': 79, 'name': 'Уксус столовый 9%', 'price': 1.50, 'description': 'Уксус столовый, 500мл', 'category': 'Масла и соусы', 'subcategory': 'Уксусы', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Heinz', 'composition': 'Уксусная кислота, вода', 'expiry': '5 лет'},
    {'id': 80, 'name': 'Майонез провансаль', 'price': 3.75, 'description': 'Майонез провансаль, 400г', 'category': 'Масла и соусы', 'subcategory': 'Соусы', 'image': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop', 'brand': 'Слобода', 'composition': 'Масло, яйца, уксус', 'expiry': '4 месяца'},

    # Яйца
    {'id': 81, 'name': 'Яйца куриные С1', 'price': 4.50, 'description': 'Яйца куриные, 10шт', 'category': 'Яйца', 'subcategory': 'Куриные яйца', 'image': 'https://images.unsplash.com/photo-1569398034845-82b9a0606b9a?w=200&h=200&fit=crop', 'brand': 'Местные', 'composition': 'Яйца куриные', 'expiry': '25 дней'},
    {'id': 82, 'name': 'Яйца перепелиные', 'price': 8.75, 'description': 'Яйца перепелиные, 20шт', 'category': 'Яйца', 'subcategory': 'Перепелиные яйца', 'image': 'https://images.unsplash.com/photo-1569398034845-82b9a0606b9a?w=200&h=200&fit=crop', 'brand': 'Фермерские', 'composition': 'Яйца перепелиные', 'expiry': '25 дней'},

    # Сладости и снеки
    {'id': 83, 'name': 'Шоколад молочный', 'price': 5.50, 'description': 'Шоколад молочный, 100г', 'category': 'Сладости и снеки', 'subcategory': 'Шоколад', 'image': 'https://images.unsplash.com/photo-1610450949065-1f2841536c88?w=200&h=200&fit=crop', 'brand': 'Alpen Gold', 'composition': 'Какао, молоко, сахар', 'expiry': '1 год'},
    {'id': 84, 'name': 'Печенье овсяное', 'price': 4.50, 'description': 'Печенье овсяное, 300г', 'category': 'Сладости и снеки', 'subcategory': 'Печенье', 'image': 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=200&h=200&fit=crop', 'brand': 'Юбилейное', 'composition': 'Мука, овсяные хлопья, сахар', 'expiry': '6 месяцев'},
    {'id': 85, 'name': 'Конфеты ассорти', 'price': 16.25, 'description': 'Конфеты ассорти, 500г', 'category': 'Сладости и снеки', 'subcategory': 'Конфеты', 'image': 'https://images.unsplash.com/photo-1610450949065-1f2841536c88?w=200&h=200&fitcrop', 'brand': 'Красный Октябрь', 'composition': 'Сахар, какао, орехи', 'expiry': '1 год'},

    # Кофе и чай
    {'id': 86, 'name': 'Кофе растворимый', 'price': 11.25, 'description': 'Кофе растворимый, 190г', 'category': 'Кофе и чай', 'subcategory': 'Кофе', 'image': 'https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=200&h=200&fit=crop', 'brand': 'Nescafe', 'composition': 'Кофе натуральный', 'expiry': '2 года'},
    {'id': 87, 'name': 'Чай черный', 'price': 7.00, 'description': 'Чай черный листовой, 100г', 'category': 'Кофе и чай', 'subcategory': 'Чай', 'image': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=200&h=200&fit=crop', 'brand': 'Ахмад', 'composition': 'Чай черный', 'expiry': '3 года'},
    {'id': 88, 'name': 'Чай зеленый', 'price': 8.00, 'description': 'Чай зеленый, 100г', 'category': 'Кофе и чай', 'subcategory': 'Чай', 'image': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=200&h=200&fit=crop', 'brand': 'Greenfield', 'composition': 'Чай зеленый', 'expiry': '3 года'},

    # Детское питание
    {'id': 89, 'name': 'Пюре яблочное детское', 'price': 3.75, 'description': 'Пюре яблочное, 130г', 'category': 'Детское питание', 'subcategory': 'Пюре', 'image': 'https://images.unsplash.com/photo-1589217157232-464b505b197f?w=200&h=200&fit=crop', 'brand': 'Фрутоняня', 'composition': 'Яблоки, вода', 'expiry': '2 года'},
    {'id': 90, 'name': 'Каша детская овсяная', 'price': 6.25, 'description': 'Каша овсяная молочная, 200г', 'category': 'Детское питание', 'subcategory': 'Каши', 'image': 'https://images.unsplash.com/photo-1589217157232-464b505b197f?w=200&h=200&fit=crop', 'brand': 'Heinz', 'composition': 'Овсяные хлопья, молоко', 'expiry': '1.5 года'},

    # Бытовая химия
    {'id': 91, 'name': 'Стиральный порошок', 'price': 8.75, 'description': 'Порошок стиральный, 3кг', 'category': 'Бытовая химия', 'subcategory': 'Стирка', 'image': 'https://images.unsplash.com/photo-1556909075-f3dc1eb6e4a2?w=200&h=200&fit=crop', 'brand': 'Ariel', 'composition': 'ПАВ, энзимы', 'expiry': '3 года'},
    {'id': 92, 'name': 'Средство для мытья посуды', 'price': 3.00, 'description': 'Гель для мытья посуды, 500мл', 'category': 'Бытовая химия', 'subcategory': 'Посуда', 'image': 'https://images.unsplash.com/photo-1556909075-f3dc1eb6e4a2?w=200&h=200&fit=crop', 'brand': 'Fairy', 'composition': 'ПАВ, ароматизаторы', 'expiry': '3 года'},

    # Товары для дома
    {'id': 93, 'name': 'Туалетная бумага', 'price': 4.50, 'description': 'Туалетная бумага, 8 рулонов', 'category': 'Товары для дома', 'subcategory': 'Гигиена дома', 'image': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=200&h=200&fit=crop', 'brand': 'Zewa', 'composition': 'Целлюлоза', 'expiry': 'Без ограничений'},
    {'id': 94, 'name': 'Салфетки бумажные', 'price': 2.00, 'description': 'Салфетки бумажные, 100шт', 'category': 'Товары для дома', 'subcategory': 'Гигиена дома', 'image': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=200&h=200&fit=crop', 'brand': 'Familia', 'composition': 'Целлюлоза', 'expiry': 'Без ограничений'},

    # Личная гигиена
    {'id': 95, 'name': 'Зубная паста', 'price': 6.25, 'description': 'Зубная паста отбеливающая, 75мл', 'category': 'Личная гигиена', 'subcategory': 'Уход за зубами', 'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=200&h=200&fit=crop', 'brand': 'Colgate', 'composition': 'Фториды, абразивы', 'expiry': '3 года'},
    {'id': 96, 'name': 'Шампунь для волос', 'price': 8.00, 'description': 'Шампунь для всех типов волос, 400мл', 'category': 'Личная гигиена', 'subcategory': 'Уход за волосами', 'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=200&h=200&fit=crop', 'brand': 'Head & Shoulders', 'composition': 'ПАВ, экстракты', 'expiry': '3 года'},

    # Алкоголь (безалкогольные)
    {'id': 97, 'name': 'Пиво безалкогольное', 'price': 3.75, 'description': 'Пиво безалкогольное, 0.5л', 'category': 'Безалкогольные напитки', 'subcategory': 'Пиво безалкогольное', 'image': 'https://images.unsplash.com/photo-1558642891-54be180ea339?w=200&h=200&fit=crop', 'brand': 'Балтика', 'composition': 'Солод, хмель, вода', 'expiry': '6 месяцев'},

    # Орехи и сухофрукты
    {'id': 98, 'name': 'Грецкие орехи', 'price': 21.25, 'description': 'Орехи грецкие очищенные, 500г', 'category': 'Орехи и сухофрукты', 'subcategory': 'Орехи', 'image': 'https://images.unsplash.com/photo-1508747703725-719777637510?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Орехи грецкие', 'expiry': '6 месяцев'},
    {'id': 99, 'name': 'Изюм', 'price': 7.00, 'description': 'Изюм без косточек, 500г', 'category': 'Орехи и сухофрукты', 'subcategory': 'Сухофрукты', 'image': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=200&h=200&fit=crop', 'brand': 'Узбекские', 'composition': 'Виноград сушеный', 'expiry': '1 год'},
    {'id': 100, 'name': 'Курага', 'price': 11.25, 'description': 'Курага сушеная, 500г', 'category': 'Орехи и сухофрукты', 'subcategory': 'Сухофрукты', 'image': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=200&h=200&fit=crop', 'brand': 'Таджикские', 'composition': 'Абрикосы сушеные', 'expiry': '1 год'},
]

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

@app.route('/')
def home():
    cart_items = session.get('cart', [])
    cart_count = len([item for item in cart_items if item.get('quantity', 0) > 0])

    # Получаем уникальные категории
    categories = {}
    for product in products:
        if product['category'] not in categories:
            categories[product['category']] = set()
        categories[product['category']].add(product['subcategory'])

    category_data = []
    for category, subcategories in categories.items():
        category_data.append({
            'name': category,
            'subcategories': list(subcategories)
        })

    # Группируем товары
    grouped_products = group_products(products)

    # Добавляем информацию о остатках к товарам
    products_with_stock = []
    for product in products:
        product_copy = product.copy()
        stock_info = get_product_stock(product['id'])
        product_copy['stock'] = stock_info['stock']
        product_copy['available'] = stock_info['active']
        products_with_stock.append(product_copy)

    # Получаем историю поиска
    search_history = session.get('search_history', [])

    return render_template('index.html', 
                         products=products_with_stock, 
                         grouped_products=grouped_products,
                         categories=category_data, 
                         cart_count=cart_count,
                         search_history=search_history[:5])  # Последние 5 поисков

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    save_to_history = request.args.get('save_history', 'false') == 'true'

    if not query:
        return jsonify({'results': [], 'query': query})

    # Сохраняем в историю поиска только при явном запросе
    if save_to_history and len(query) >= 3:
        search_history = session.get('search_history', [])
        if query not in search_history:
            search_history.insert(0, query)
            search_history = search_history[:10]  # Храним последние 10
            session['search_history'] = search_history

    results = smart_search(query, products)

    # Добавляем информацию о остатках к результатам поиска
    results_with_stock = []
    for product in results:
        product_copy = product.copy()
        stock_info = get_product_stock(product['id'])
        product_copy['stock'] = stock_info['stock']
        product_copy['available'] = stock_info['active']
        results_with_stock.append(product_copy)

    return jsonify({
        'results': results_with_stock[:20],  # Ограничиваем до 20 результатов
        'query': query,
        'count': len(results)
    })

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    existing_item = next((item for item in cart if item['id'] == product_id), None)

    if existing_item:
        existing_item['quantity'] += 1
    else:
        cart.append({'id': product_id, 'quantity': 1})

    session['cart'] = cart
    cart_count = len(cart)
    return jsonify({'success': True, 'cart_count': cart_count})

@app.route('/update_cart_quantity', methods=['POST'])
def update_cart_quantity():
    data = request.get_json()
    product_id = data.get('product_id')
    change = data.get('change', 0)

    if 'cart' not in session:
        session['cart'] = []

    # Проверяем остатки на складе
    stock_info = get_product_stock(product_id)

    if not stock_info['active']:
        return jsonify({
            'success': False,
            'error': 'Товар закончился'
        })

    cart = session['cart']
    item = next((item for item in cart if item['id'] == product_id), None)

    current_in_cart = item['quantity'] if item else 0
    new_quantity = max(0, current_in_cart + change)

    # Проверяем, не превышает ли новое количество остаток на складе
    if new_quantity > stock_info['stock']:
        return jsonify({
            'success': False,
            'error': f'В наличии только {stock_info["stock"]} шт.',
            'max_available': stock_info['stock']
        })

    if item:
        if new_quantity <= 0:
            cart = [cart_item for cart_item in cart if cart_item['id'] != product_id]
        else:
            item['quantity'] = new_quantity
    elif new_quantity > 0:
        cart.append({'id': product_id, 'quantity': new_quantity})

    session['cart'] = cart

    # Подсчитываем общее количество уникальных товаров в корзине
    total_cart_count = len(cart)

    return jsonify({
        'success': True,
        'cart_count': total_cart_count,
        'current_quantity': new_quantity,
        'stock_remaining': max(0, stock_info['stock'] - new_quantity)
    })

@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    cart_products = []
    total_price = 0

    for item in cart_items:
        product_id = item['id']
        quantity = item['quantity']

        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            cart_product = {
                'id': product_id,
                'name': product['name'],
                'price': product['price'],
                'image': product['image'],
                'quantity': quantity,
                'total': product['price'] * quantity
            }
            cart_products.append(cart_product)
            total_price += cart_product['total']

    cart_count = len([item for item in cart_items if item.get('quantity', 0) > 0])
    return render_template('cart.html', cart_products=cart_products, total_price=total_price, cart_count=cart_count)

@app.route('/checkout')
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        return redirect(url_for('cart'))

    cart_products = []
    total_price = 0

    for item in cart_items:
        product_id = item['id']
        quantity = item['quantity']
        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            cart_product = {
                'id': product_id,
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'total': product['price'] * quantity
            }
            cart_products.append(cart_product)
            total_price += cart_product['total']

    cart_count = len(cart_items)
    return render_template('checkout.html', cart_products=cart_products, total_price=total_price, cart_count=cart_count)

@app.route('/apply_promocode', methods=['POST'])
def apply_promocode():
    data = request.get_json()
    code = data.get('code', '').upper().strip()
    total = data.get('total', 0)

    promocodes = load_promocodes()

    if code not in promocodes:
        return jsonify({
            'success': False,
            'message': 'Промокод не найден'
        })

    promo = promocodes[code]

    # Проверяем активность
    if not promo.get('active', True):
        return jsonify({
            'success': False,
            'message': 'Промокод неактивен'
        })

    # Проверяем лимит использований
    used_count = promo.get('used_count', 0)
    usage_limit = promo.get('usage_limit', float('inf'))

    if used_count >= usage_limit:
        return jsonify({
            'success': False,
            'message': 'Промокод исчерпал лимит использований'
        })

    # Проверяем минимальную сумму заказа
    min_order = promo.get('min_order', 0)
    if total < min_order:
        return jsonify({
            'success': False,
            'message': f'Минимальная сумма заказа для этого промокода: {min_order:.2f} сом'
        })

    # Проверяем промокод только для первого заказа
    if promo.get('first_order_only', False):
        phone = session.get('customer_phone') or data.get('phone')
        if phone:
            orders = load_orders()
            user_orders = [order for order in orders 
                          if order.get('customer', {}).get('phone') == phone and 
                          order.get('status') == 'Доставлен']
            # Разрешаем промокод ЯКУМ работать всегда для новых клиентов
            if user_orders and code != 'ЯКУМ':
                return jsonify({
                    'success': False,
                    'message': 'Этот промокод только на первый заказ. У вас уже был первый заказ'
                })

    # Вычисляем скидку
    if promo['type'] == 'percent':
        discount = total * (promo['discount'] / 100)
    else:
        discount = min(promo['discount'], total)  # Скидка не может быть больше суммы заказа

    new_total = max(0, total - discount)

    # Сохраняем информацию о применении промокода в сессии (увеличиваем счетчик при оформлении заказа)
    session['applied_promocode'] = {
        'code': code,
        'discount': discount,
        'original_total': total,
        'new_total': new_total
    }

    remaining_uses = usage_limit - used_count - 1
    message = f'Промокод применен! Скидка: {discount:.2f} сом'
    if usage_limit != float('inf'):
        message += f' (осталось использований: {remaining_uses})'

    return jsonify({
        'success': True,
        'discount': discount,
        'new_total': new_total,
        'message': message
    })

@app.route('/update_cart_ajax/<int:product_id>/<int:new_quantity>', methods=['POST'])
def update_cart_ajax(product_id, new_quantity):
    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    cart_products = []
    total_price = 0

    if new_quantity <= 0:
        # Удаляем товар
        cart = [item for item in cart if item['id'] != product_id]
    else:
        # Обновляем количество
        item = next((item for item in cart if item['id'] == product_id), None)
        if item:
            item['quantity'] = new_quantity
        else:
            cart.append({'id': product_id, 'quantity': new_quantity})

    session['cart'] = cart

    # Пересчитываем корзину
    for item in cart:
        product = next((p for p in products if p['id'] == item['id']), None)
        if product:
            cart_product = {
                'id': item['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': item['quantity'],
                'total': product['price'] * item['quantity']
            }
            cart_products.append(cart_product)
            total_price += cart_product['total']

    # Находим конкретный товар для возврата его стоимости
    item_total = 0
    if new_quantity > 0:
        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            item_total = product['price'] * new_quantity

    return jsonify({
        'success': True,
        'cart_count': len(cart),
        'total_price': total_price,
        'item_total': item_total
    })

@app.route('/remove_from_cart_ajax/<int:product_id>', methods=['POST'])
def remove_from_cart_ajax(product_id):
    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart

    # Пересчитываем корзину
    total_price = 0
    for item in cart:
        product = next((p for p in products if p['id'] == item['id']), None)
        if product:
            total_price += product['price'] * item['quantity']

    return jsonify({
        'success': True,
        'cart_count': len(cart),
        'total_price': total_price
    })

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = []
    return jsonify({'success': True})

@app.route('/place_order', methods=['POST'])
def place_order():
    customer_name = request.form['name']
    customer_phone = request.form['phone']
    customer_address = request.form['address']
    delivery_time = request.form['delivery_time']
    payment_method = request.form['payment_method']
    comments = request.form.get('comments', '')
    courier_comment = request.form.get('courier_comment', '')
    promocode = request.form.get('promocode', '')
    final_total = float(request.form.get('final_total', 0))

    cart_items = session.get('cart', [])
    if not cart_items:
        return redirect(url_for('cart'))

    order_products = []
    total_price = 0

    for item in cart_items:
        product_id = item['id']
        quantity = item['quantity']
        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            order_product = {
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'total': product['price'] * quantity
            }
            order_products.append(order_product)
            total_price += order_product['total']

    order = {
        'customer': {
            'name': customer_name,
            'phone': customer_phone,
            'address': customer_address
        },
        'delivery_time': delivery_time,
        'payment_method': payment_method,
        'comments': comments,
        'courier_comment': courier_comment,
        'promocode': promocode,
        'products': order_products,
        'total_price': total_price,
        'final_total': final_total,
        'delivery_cost': 0
    }

    # Увеличиваем счетчик использования промокода, если он был применен
    if promocode:
        promocodes = load_promocodes()
        if promocode in promocodes:
            promocodes[promocode]['used_count'] = promocodes[promocode].get('used_count', 0) + 1
            # Деактивируем промокод, если достигнут лимит
            if promocodes[promocode]['used_count'] >= promocodes[promocode].get('usage_limit', float('inf')):
                promocodes[promocode]['active'] = False

            with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(promocodes, f, ensure_ascii=False, indent=2)

    # Уменьшаем остатки товаров на складе
    for item in cart_items:
        update_product_stock(item['id'], item['quantity'])

    session['last_order'] = order
    save_order(order)
    session['cart'] = []
    # Очищаем информацию о примененном промокоде
    session.pop('applied_promocode', None)

    return redirect(url_for('order_confirmation'))

@app.route('/order_confirmation')
def order_confirmation():
    order = session.get('last_order')
    if not order:
        return redirect(url_for('home'))

    return render_template('order_confirmation.html', order=order)

@app.route('/my_orders')
def my_orders():
    phone = request.args.get('phone', '').strip()
    cart_count = len(session.get('cart', []))

    # Проверяем, авторизован ли пользователь
    current_user = get_current_user()

    if current_user:
        # Пользователь авторизован, показываем его заказы
        phone = current_user['phone']
        all_orders = load_orders()
        user_orders = [order for order in all_orders 
                      if (order.get('customer', {}).get('phone') == phone and 
                          not order.get('deleted_by_user', False))]
        user_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return render_template('my_orders.html', orders=user_orders, phone=phone, 
                             cart_count=cart_count, authenticated=True, user=current_user)
    elif phone:
        # Старый способ поиска по номеру телефона (для совместимости)
        all_orders = load_orders()
        user_orders = [order for order in all_orders 
                      if (order.get('customer', {}).get('phone') == phone and 
                          not order.get('deleted_by_user', False))]
        user_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return render_template('my_orders.html', orders=user_orders, phone=phone, 
                             cart_count=cart_count, authenticated=False)
    else:
        # Пользователь не авторизован и не указан телефон
        return render_template('my_orders.html', orders=None, phone=None, 
                             cart_count=cart_count, authenticated=False)

@app.route('/leave_review', methods=['POST'])
def leave_review():
    data = request.get_json()

    review = {
        'order_number': data.get('order_number'),
        'customer_phone': data.get('customer_phone'),
        'product_rating': data.get('product_rating'),
        'delivery_rating': data.get('delivery_rating'),
        'comment': data.get('comment', '')
    }

    save_review(review)

    return jsonify({'success': True, 'message': 'Спасибо за отзыв!'})

@app.route('/admin')
def admin():
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['POST'])
def admin_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['admin_authenticated'] = True
        return redirect('/admin_panel')
    else:
        return render_template('admin_login.html', error='Неверный пароль')

@app.route('/admin_panel')
def admin_panel():
    if not session.get('admin_authenticated'):
        return redirect('/admin')

    orders = load_orders()
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Статистика только для доставленных заказов
    delivered_orders = [order for order in orders if order.get('status') == 'Доставлен']
    total_revenue = sum(order.get('final_total', order.get('total_price', 0)) for order in delivered_orders)

    # Подсчет проданных товаров только для доставленных заказов
    total_items_sold = 0
    product_stats = {}
    for order in delivered_orders:
        for product in order.get('products', []):
            name = product['name']
            if name not in product_stats:
                product_stats[name] = {'quantity': 0, 'revenue': 0}
            product_stats[name]['quantity'] += product['quantity']
            product_stats[name]['revenue'] += product['total']
            total_items_sold += product['quantity']

    popular_products = sorted(product_stats.items(), key=lambda x: x[1]['quantity'], reverse=True)[:10]

    return render_template('admin.html', 
                         orders=orders, 
                         total_revenue=total_revenue,
                         total_items_sold=total_items_sold,
                         popular_products=popular_products)

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/')

@app.route('/admin/update_order_status', methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_number = data.get('order_number')
    new_status = data.get('status')

    orders