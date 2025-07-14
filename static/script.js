
// Основной JavaScript для Дучарха
let currentCategory = '';
let cartQuantities = {};
let products = [];
let isInitialized = false;

// Утилиты
function showNotification(message, type = 'success', duration = 3000) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        background: ${type === 'success' ? '#28a745' : '#dc3545'};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        z-index: 1000;
        transition: transform 0.3s ease;
        max-width: 300px;
        text-align: center;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.transform = 'translateX(-50%) translateY(0)';
    }, 100);

    setTimeout(() => {
        notification.style.transform = 'translateX(-50%) translateY(100px)';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
}

// Управление корзиной
function changeQuantity(productId, change) {
    const currentQty = cartQuantities[productId] || 0;
    const newQty = currentQty + change;

    if (newQty < 0) return;

    // Проверяем максимальный остаток
    const plusBtn = document.getElementById(`plus-${productId}`);
    if (plusBtn) {
        const maxStock = parseInt(plusBtn.dataset.maxStock || '999');
        if (newQty > maxStock) {
            showNotification(`В наличии только ${maxStock} шт.`, 'error');
            return;
        }
    }

    fetch('/update_cart_quantity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'product_id': productId,
            'change': change
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            cartQuantities[productId] = data.current_quantity;
            updateQuantityDisplay(productId, data.current_quantity);
            updateCartCount(data.cart_count);

            if (change > 0) {
                showSuccessMessage();
            }
        } else {
            showNotification(data.error || 'Ошибка добавления товара', 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showNotification('Ошибка соединения', 'error');
    });
}

function updateQuantityDisplay(productId, quantity) {
    // Обновляем все элементы отображения количества
    const qtyElements = document.querySelectorAll(`[id^="qty-${productId}"], [id^="search-qty-${productId}"], [id^="modal-qty-${productId}"]`);
    qtyElements.forEach(element => {
        if (element) element.textContent = quantity;
    });

    // Обновляем кнопки минус
    const minusButtons = document.querySelectorAll(`[id^="minus-${productId}"], [id^="search-minus-${productId}"]`);
    minusButtons.forEach(button => {
        if (button) button.disabled = quantity <= 0;
    });
}

function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('.cart-count, #cart-count');
    cartCountElements.forEach(element => {
        if (element) element.textContent = count;
    });
}

function showSuccessMessage() {
    const successMessage = document.getElementById('success-message');
    if (successMessage) {
        successMessage.style.display = 'block';
        setTimeout(() => {
            successMessage.style.display = 'none';
        }, 2000);
    }
}

// Profile Menu
function toggleProfileMenu() {
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// Категории и товары
function showCategoryProducts(category) {
    currentCategory = category;

    const categoriesSection = document.getElementById('categories-section');
    const productsSection = document.getElementById('products-section');
    const mainProducts = document.getElementById('main-products');
    const backButton = document.getElementById('back-to-categories');
    const productsTitle = document.getElementById('products-title');

    if (categoriesSection) categoriesSection.style.display = 'none';
    if (productsSection) productsSection.classList.add('show');
    if (mainProducts) mainProducts.classList.add('show');
    if (backButton) backButton.classList.add('show');
    if (productsTitle) productsTitle.textContent = category;

    // Фильтруем товары по категории
    const productGroups = document.querySelectorAll('.product-group');
    productGroups.forEach(group => {
        const groupCategory = group.dataset.category;
        if (groupCategory === category) {
            group.style.display = 'block';
        } else {
            group.style.display = 'none';
        }
    });

    hideSearchResults();
}

function showCategories() {
    currentCategory = '';
    
    const categoriesSection = document.getElementById('categories-section');
    const productsSection = document.getElementById('products-section');
    const mainProducts = document.getElementById('main-products');
    const backButton = document.getElementById('back-to-categories');

    if (categoriesSection) categoriesSection.style.display = 'block';
    if (productsSection) productsSection.classList.remove('show');
    if (mainProducts) mainProducts.classList.remove('show');
    if (backButton) backButton.classList.remove('show');

    // Показываем все товары
    const productGroups = document.querySelectorAll('.product-group');
    productGroups.forEach(group => {
        group.style.display = 'block';
    });

    hideSearchResults();
}

// Поиск
let searchTimeout;

function handleSearchInput(input) {
    const query = input.value.trim();
    
    // Очищаем предыдущий таймер
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    if (query.length >= 1) {
        showSearchSuggestions(query, input.id.includes('sticky') ? 'sticky-search-suggestions' : 'search-suggestions');
    } else {
        hideSearchSuggestions(input.id.includes('sticky') ? 'sticky-search-suggestions' : 'search-suggestions');
        hideSearchResults();
        return;
    }

    if (query.length >= 2) {
        searchTimeout = setTimeout(() => {
            performSearch(query, false);
        }, 300);
    }
}

function searchProducts() {
    const query = document.getElementById('search-input').value.trim();
    if (query) {
        performSearch(query, true);
    }
}

function searchProductsSticky() {
    const query = document.getElementById('sticky-search-input').value.trim();
    const mainInput = document.getElementById('search-input');
    if (mainInput) mainInput.value = query;
    if (query) {
        performSearch(query, true);
    }
}

function performSearch(query, saveHistory) {
    if (!query.trim()) {
        hideSearchResults();
        return;
    }

    fetch(`/search?q=${encodeURIComponent(query)}&save_history=${saveHistory}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data.results, data.query, data.count);
        })
        .catch(error => {
            console.error('Ошибка поиска:', error);
            showNotification('Ошибка поиска', 'error');
        });
}

function displaySearchResults(results, query, count) {
    const resultsContainer = document.getElementById('search-results');
    const resultsGrid = document.getElementById('results-grid');
    const noResults = document.getElementById('no-results');
    const resultsTitle = document.getElementById('results-title');
    const categoriesSection = document.getElementById('categories-section');
    const productsSection = document.getElementById('products-section');

    if (!resultsContainer || !resultsGrid) return;

    if (resultsTitle) resultsTitle.textContent = `Результаты поиска "${query}" (${count})`;

    if (results.length === 0) {
        if (resultsGrid) resultsGrid.style.display = 'none';
        if (noResults) noResults.style.display = 'block';
    } else {
        if (noResults) noResults.style.display = 'none';
        if (resultsGrid) resultsGrid.style.display = 'grid';

        resultsGrid.innerHTML = results.map(product => `
            <div class="product-group ${!product.available ? 'out-of-stock' : ''}" onclick="openProductModal(${product.id})">
                <div class="product-image">
                    ${product.image.startsWith('http') 
                        ? `<img src="${product.image}" alt="${product.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                           <div class="product-emoji" style="display: none;">🛒</div>`
                        : `<div class="product-emoji">${product.image}</div>`
                    }
                </div>
                <div class="product-info">
                    ${product.brand ? `<div class="product-brand">${product.brand}</div>` : ''}
                    <div class="product-name">${product.name}</div>
                    <div class="product-description">${product.description}</div>

                    ${!product.available ? '<div class="out-of-stock"><span>❌ Нет в наличии</span></div>' :
                      product.stock <= 5 ? `<div class="low-stock"><span>⚠️ Осталось ${product.stock} шт.</span></div>` : ''}

                    <div class="product-footer">
                        <div class="product-price">
                            ${product.price.toFixed(2)} <span class="currency">сом</span>
                        </div>
                        ${product.available ? `
                            <div class="quantity-controls">
                                <button class="quantity-btn minus" id="search-minus-${product.id}" onclick="event.stopPropagation(); changeQuantity(${product.id}, -1)" ${!(cartQuantities[product.id] > 0) ? 'disabled' : ''}>−</button>
                                <span class="quantity-display" id="search-qty-${product.id}">${cartQuantities[product.id] || 0}</span>
                                <button class="quantity-btn plus" id="search-plus-${product.id}" onclick="event.stopPropagation(); changeQuantity(${product.id}, 1)" data-max-stock="${product.stock}">+</button>
                            </div>
                        ` : '<div class="unavailable-btn">Недоступно</div>'}
                    </div>
                </div>
            </div>
        `).join('');
    }

    if (categoriesSection) categoriesSection.style.display = 'none';
    if (productsSection) productsSection.classList.remove('show');
    if (resultsContainer) resultsContainer.style.display = 'block';
}

function hideSearchResults() {
    const resultsContainer = document.getElementById('search-results');
    const searchInputs = document.querySelectorAll('#search-input, #sticky-search-input');
    
    if (resultsContainer) resultsContainer.style.display = 'none';
    
    searchInputs.forEach(input => {
        if (input) input.value = '';
    });
    
    if (!currentCategory) {
        showCategories();
    }
}

function showSearchSuggestions(query, containerId) {
    // Простая реализация подсказок
    console.log('Показать подсказки для:', query);
}

function hideSearchSuggestions(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.remove('show');
    }
}

// Модальные окна
function openProductModal(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    const modal = document.getElementById('product-modal');
    const overlay = document.getElementById('product-overlay');
    const content = document.getElementById('product-modal-content');

    if (!modal || !overlay || !content) return;

    const stockInfo = cartQuantities[productId] || 0;
    const isAvailable = product.available && product.stock > 0;

    content.innerHTML = `
        <div class="product-modal-image">
            ${product.image.startsWith('http') 
                ? `<img src="${product.image}" alt="${product.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                   <div class="product-modal-emoji" style="display: none;">🛒</div>`
                : `<div class="product-modal-emoji">${product.image}</div>`
            }
        </div>
        ${product.brand ? `<div class="product-modal-brand">${product.brand}</div>` : ''}
        <div class="product-modal-name">${product.name}</div>
        <div class="product-modal-description">${product.description}</div>
        <div class="product-modal-price">${product.price.toFixed(2)} сом</div>
        ${!isAvailable ? '<div class="out-of-stock">❌ Нет в наличии</div>' : 
          product.stock <= 5 ? `<div class="low-stock">⚠️ Осталось ${product.stock} шт.</div>` : ''}
        ${isAvailable ? `
            <div class="product-modal-controls">
                <div class="quantity-controls">
                    <button class="quantity-btn" onclick="changeQuantity(${product.id}, -1)">−</button>
                    <span class="quantity-display" id="modal-qty-${product.id}">${stockInfo}</span>
                    <button class="quantity-btn" onclick="changeQuantity(${product.id}, 1)" data-max-stock="${product.stock}">+</button>
                </div>
            </div>
        ` : '<div class="unavailable-btn">Недоступно</div>'}
    `;

    modal.classList.add('show');
    overlay.style.display = 'block';
}

function closeProductModal() {
    const modal = document.getElementById('product-modal');
    const overlay = document.getElementById('product-overlay');
    
    if (modal) modal.classList.remove('show');
    if (overlay) overlay.style.display = 'none';
}

// Help Modal
function toggleHelpModal() {
    const modal = document.getElementById('help-modal');
    const overlay = document.getElementById('help-overlay');
    
    if (!modal || !overlay) return;
    
    const isVisible = modal.style.display === 'block';
    
    modal.style.display = isVisible ? 'none' : 'block';
    overlay.style.display = isVisible ? 'none' : 'block';
    
    // Закрываем профильное меню
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) dropdown.classList.remove('show');
}

function closeHelpModal() {
    const modal = document.getElementById('help-modal');
    const overlay = document.getElementById('help-overlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

// Поиск в истории
function searchFromHistory(query) {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = query;
        performSearch(query, true);
    }
}

function removeFromHistory(query) {
    fetch('/remove_search_history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({query: query})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    })
    .catch(error => {
        console.error('Ошибка удаления из истории:', error);
    });
}

function clearAllHistory() {
    fetch('/clear_search_history', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    })
    .catch(error => {
        console.error('Ошибка очистки истории:', error);
    });
}

// Аутентификация
function checkAuthentication() {
    const sessionToken = getCookie('session_token');
    if (sessionToken) {
        fetch('/auth/check_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({session_token: sessionToken})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateUIForAuthenticatedUser(data.user);
            } else {
                updateUIForGuestUser();
            }
        })
        .catch(error => {
            console.log('Ошибка проверки сессии:', error);
            updateUIForGuestUser();
        });
    } else {
        updateUIForGuestUser();
    }
}

function updateUIForAuthenticatedUser(user) {
    const userInfo = document.getElementById('user-info');
    const userPhone = document.getElementById('user-phone');
    const loginItem = document.getElementById('login-item');
    const logoutItem = document.getElementById('logout-item');
    
    if (userInfo) userInfo.style.display = 'block';
    if (userPhone) userPhone.textContent = formatPhone(user.phone);
    if (loginItem) loginItem.style.display = 'none';
    if (logoutItem) logoutItem.style.display = 'flex';
}

function updateUIForGuestUser() {
    const userInfo = document.getElementById('user-info');
    const loginItem = document.getElementById('login-item');
    const logoutItem = document.getElementById('logout-item');
    
    if (userInfo) userInfo.style.display = 'none';
    if (loginItem) loginItem.style.display = 'flex';
    if (logoutItem) logoutItem.style.display = 'none';
}

function formatPhone(phone) {
    if (phone.length >= 12) {
        return '+' + phone.substring(0, 3) + ' ' + 
               phone.substring(3, 6) + ' ' + 
               phone.substring(6, 8) + ' ' + 
               phone.substring(8, 10) + ' ' + 
               phone.substring(10, 12);
    }
    return phone;
}

function logoutUser() {
    fetch('/auth/logout', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateUIForGuestUser();
            const dropdown = document.getElementById('profile-dropdown');
            if (dropdown) dropdown.classList.remove('show');
            showNotification('Вы вышли из системы', 'success');
        }
    })
    .catch(error => {
        console.error('Ошибка при выходе:', error);
    });
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Sticky search
function setupStickySearch() {
    window.addEventListener('scroll', function() {
        const searchSection = document.querySelector('.search-section');
        const stickySearch = document.getElementById('sticky-search');
        const headerCenter = document.querySelector('.header-center');
        
        if (!searchSection || !stickySearch || !headerCenter) return;
        
        const searchSectionBottom = searchSection.offsetTop + searchSection.offsetHeight;

        if (window.scrollY > searchSectionBottom) {
            stickySearch.classList.add('show');
            headerCenter.classList.add('search-mode');
        } else {
            stickySearch.classList.remove('show');
            headerCenter.classList.remove('search-mode');
        }
    });
}

// Курьер и промокод
function startCourierAnimation() {
    const courierAnimation = document.getElementById('courier-animation');
    const hasSeenCourier = localStorage.getItem('has_seen_courier');

    if (!hasSeenCourier && courierAnimation) {
        setTimeout(() => {
            courierAnimation.classList.add('show');
            setTimeout(() => {
                courierAnimation.classList.remove('show');
            }, 15000);
        }, 3000);
    }
}

function catchCourier() {
    const courierAnimation = document.getElementById('courier-animation');
    const promoModal = document.getElementById('promo-modal');
    const promoOverlay = document.getElementById('promo-modal-overlay');

    if (courierAnimation) courierAnimation.classList.remove('show');
    if (promoModal) promoModal.classList.add('show');
    if (promoOverlay) promoOverlay.classList.add('show');

    localStorage.setItem('has_seen_courier', 'true');
}

function closePromoModal() {
    const promoModal = document.getElementById('promo-modal');
    const promoOverlay = document.getElementById('promo-modal-overlay');

    if (promoModal) promoModal.classList.remove('show');
    if (promoOverlay) promoOverlay.classList.remove('show');
}

function copyPromoCode() {
    navigator.clipboard.writeText('ЯКУМ').then(() => {
        showNotification('Промокод скопирован!', 'success');
    });
}

function usePromoCode() {
    closePromoModal();
    showNotification('Добавьте товары в корзину и используйте промокод ЯКУМ при оформлении', 'success');
}

// Инициализация
function initializeApp() {
    if (isInitialized) return;
    
    console.log('🚀 Дучарха загружается...');
    
    // Получаем данные о товарах и корзине
    if (window.products) {
        products = window.products;
    }
    
    if (window.cartItems) {
        window.cartItems.forEach(item => {
            cartQuantities[item.id] = item.quantity;
            updateQuantityDisplay(item.id, item.quantity);
        });
    }

    // Настраиваем обработчики событий
    setupEventListeners();
    setupStickySearch();
    
    // Проверяем аутентификацию
    checkAuthentication();
    
    // Запускаем анимацию курьера
    startCourierAnimation();
    
    isInitialized = true;
    console.log('✅ Дучарха готова к работе!');
}

function setupEventListeners() {
    // Поиск
    const searchInput = document.getElementById('search-input');
    const stickySearchInput = document.getElementById('sticky-search-input');
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => handleSearchInput(e.target));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchProducts();
        });
    }
    
    if (stickySearchInput) {
        stickySearchInput.addEventListener('input', (e) => handleSearchInput(e.target));
        stickySearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchProductsSticky();
        });
    }

    // Синхронизация поисковых строк
    if (searchInput && stickySearchInput) {
        searchInput.addEventListener('input', () => {
            stickySearchInput.value = searchInput.value;
        });
        stickySearchInput.addEventListener('input', () => {
            searchInput.value = stickySearchInput.value;
        });
    }

    // Закрытие меню при клике вне его
    document.addEventListener('click', (e) => {
        const profileMenu = document.querySelector('.profile-menu');
        if (profileMenu && !profileMenu.contains(e.target)) {
            const dropdown = document.getElementById('profile-dropdown');
            if (dropdown) dropdown.classList.remove('show');
        }
        
        // Закрытие модальных окон при клике на overlay
        if (e.target.classList.contains('help-modal-overlay')) {
            closeProductModal();
            closeHelpModal();
        }
    });
}

// Запуск при загрузке страницы
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}
