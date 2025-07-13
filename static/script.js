
// Основной JavaScript для Дучарха
(function() {
    'use strict';

    // Глобальные переменные
    window.ducharkApp = {
        cart: [],
        currentUser: null,
        isLoading: false
    };

    // Утилиты
    const utils = {
        // Показать уведомление
        showNotification: function(message, type = 'success', duration = 3000) {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            setTimeout(() => notification.classList.add('show'), 100);
            
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (document.body.contains(notification)) {
                        document.body.removeChild(notification);
                    }
                }, 300);
            }, duration);
        },

        // Форматирование телефона
        formatPhone: function(phone) {
            if (phone.length >= 12) {
                return '+' + phone.substring(0, 3) + ' ' + 
                       phone.substring(3, 6) + ' ' + 
                       phone.substring(6, 8) + ' ' + 
                       phone.substring(8, 10) + ' ' + 
                       phone.substring(10, 12);
            }
            return phone;
        },

        // Получить cookie
        getCookie: function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        },

        // Установить cookie
        setCookie: function(name, value, days = 30) {
            const expires = new Date();
            expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
            document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
        },

        // Показать загрузку
        showLoading: function(element) {
            if (element) {
                const originalText = element.textContent;
                element.innerHTML = '<span class="loading"></span> Загрузка...';
                element.disabled = true;
                return originalText;
            }
        },

        // Скрыть загрузку
        hideLoading: function(element, originalText) {
            if (element && originalText) {
                element.textContent = originalText;
                element.disabled = false;
            }
        },

        // Debounce функция
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };

    // API методы
    const api = {
        // Базовый запрос
        request: async function(url, options = {}) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },

        // Поиск товаров
        search: async function(query, saveHistory = false) {
            return this.request(`/search?q=${encodeURIComponent(query)}&save_history=${saveHistory}`);
        },

        // Обновление корзины
        updateCart: async function(productId, change) {
            return this.request('/update_cart_quantity', {
                method: 'POST',
                body: JSON.stringify({
                    product_id: productId,
                    change: change
                })
            });
        },

        // Применение промокода
        applyPromocode: async function(code, total) {
            return this.request('/apply_promocode', {
                method: 'POST',
                body: JSON.stringify({
                    code: code,
                    total: total
                })
            });
        }
    };

    // Управление корзиной
    const cart = {
        quantities: {},

        // Обновить количество товара
        updateQuantity: async function(productId, change) {
            try {
                const data = await api.updateCart(productId, change);
                
                if (data.success) {
                    this.quantities[productId] = data.current_quantity;
                    this.updateDisplay(productId, data.current_quantity);
                    this.updateCartCount(data.cart_count);

                    if (change > 0) {
                        utils.showNotification('Товар добавлен в корзину!');
                    }
                } else {
                    utils.showNotification(data.error || 'Ошибка добавления товара', 'error');
                }
            } catch (error) {
                utils.showNotification('Ошибка соединения', 'error');
            }
        },

        // Обновить отображение количества
        updateDisplay: function(productId, quantity) {
            const displays = document.querySelectorAll(`#qty-${productId}, #modal-qty-${productId}`);
            displays.forEach(display => {
                if (display) display.textContent = quantity;
            });

            const minusBtn = document.getElementById(`minus-${productId}`);
            if (minusBtn) {
                minusBtn.disabled = quantity <= 0;
            }
        },

        // Обновить счетчик корзины
        updateCartCount: function(count) {
            const cartCountElement = document.getElementById('cart-count');
            if (cartCountElement) {
                cartCountElement.textContent = count;
            }
        }
    };

    // Управление поиском
    const search = {
        currentQuery: '',
        suggestions: null,

        // Инициализация поиска
        init: function() {
            const searchInputs = document.querySelectorAll('#search-input, #sticky-search-input');
            
            searchInputs.forEach(input => {
                // Поиск при вводе
                input.addEventListener('input', utils.debounce((e) => {
                    this.handleInput(e.target);
                }, 300));

                // Поиск при Enter
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.performSearch(e.target.value);
                    }
                });
            });

            // Синхронизация поисковых строк
            const mainInput = document.getElementById('search-input');
            const stickyInput = document.getElementById('sticky-search-input');

            if (mainInput && stickyInput) {
                mainInput.addEventListener('input', () => {
                    stickyInput.value = mainInput.value;
                });

                stickyInput.addEventListener('input', () => {
                    mainInput.value = stickyInput.value;
                });
            }
        },

        // Обработка ввода
        handleInput: function(input) {
            const query = input.value.trim();
            this.currentQuery = query;

            if (query.length >= 1) {
                this.showSuggestions(input, query);
            } else {
                this.hideSuggestions(input);
            }

            if (query.length >= 2) {
                this.performSearch(query, false);
            }
        },

        // Выполнить поиск
        performSearch: async function(query, saveHistory = true) {
            if (!query.trim()) return;

            try {
                const data = await api.search(query, saveHistory);
                this.displayResults(data.results, data.query, data.count);
            } catch (error) {
                console.error('Ошибка поиска:', error);
                utils.showNotification('Ошибка поиска', 'error');
            }
        },

        // Показать подсказки
        showSuggestions: function(input, query) {
            // Базовая реализация - в будущем можно расширить
            console.log('Показать подсказки для:', query);
        },

        // Скрыть подсказки
        hideSuggestions: function(input) {
            const suggestionContainers = document.querySelectorAll('.search-suggestions');
            suggestionContainers.forEach(container => {
                container.classList.remove('show');
            });
        },

        // Отобразить результаты
        displayResults: function(results, query, count) {
            console.log(`Результаты поиска для "${query}": ${count} товаров`);
            // Реализация отображения результатов
        }
    };

    // Управление модальными окнами
    const modal = {
        // Открыть модальное окно
        open: function(modalId) {
            const modal = document.getElementById(modalId);
            const overlay = document.getElementById(modalId + '-overlay');
            
            if (modal) modal.classList.add('show');
            if (overlay) overlay.classList.add('show');
        },

        // Закрыть модальное окно
        close: function(modalId) {
            const modal = document.getElementById(modalId);
            const overlay = document.getElementById(modalId + '-overlay');
            
            if (modal) modal.classList.remove('show');
            if (overlay) overlay.classList.remove('show');
        },

        // Закрыть при клике на overlay
        setupOverlayClose: function() {
            document.addEventListener('click', (e) => {
                if (e.target.classList.contains('modal-overlay')) {
                    const modalId = e.target.id.replace('-overlay', '');
                    this.close(modalId);
                }
            });
        }
    };

    // Управление формами
    const forms = {
        // Валидация телефона
        validatePhone: function(phone) {
            const phoneRegex = /^[0-9]{9,12}$/;
            return phoneRegex.test(phone.replace(/\D/g, ''));
        },

        // Валидация email
        validateEmail: function(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        },

        // Обработка отправки формы
        handleSubmit: function(form, callback) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = form.querySelector('button[type="submit"]');
                const originalText = utils.showLoading(submitBtn);
                
                try {
                    await callback(new FormData(form));
                    utils.showNotification('Форма успешно отправлена!');
                } catch (error) {
                    utils.showNotification('Ошибка при отправке формы', 'error');
                } finally {
                    utils.hideLoading(submitBtn, originalText);
                }
            });
        }
    };

    // Инициализация приложения
    function init() {
        console.log('🚀 Дучарха загружается...');

        // Инициализируем модули
        search.init();
        modal.setupOverlayClose();

        // Загружаем корзину из сессии
        const cartItems = window.cartItems || [];
        cartItems.forEach(item => {
            cart.quantities[item.id] = item.quantity;
            cart.updateDisplay(item.id, item.quantity);
        });

        console.log('✅ Дучарха готова к работе!');
    }

    // Экспортируем в глобальную область
    window.ducharkApp.utils = utils;
    window.ducharkApp.api = api;
    window.ducharkApp.cart = cart;
    window.ducharkApp.search = search;
    window.ducharkApp.modal = modal;
    window.ducharkApp.forms = forms;

    // Запускаем при загрузке DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Глобальные функции для совместимости с существующим кодом
    window.changeQuantity = (productId, change) => cart.updateQuantity(productId, change);
    window.searchProducts = () => search.performSearch(document.getElementById('search-input').value, true);
    window.searchProductsSticky = () => search.performSearch(document.getElementById('sticky-search-input').value, true);
    window.showNotification = utils.showNotification;

})();
