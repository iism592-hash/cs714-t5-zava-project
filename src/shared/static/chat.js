/**
 * Zava DIY Hardware - Commercial Storefront & Multi-Agent Assistant
 * Connects to WebApp on port 8005 and Multi-Agent streaming backend on port 8006
 */

// DOM Elements - Chat & AI
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const fileBtn = document.getElementById('fileBtn');
const fileInput = document.getElementById('fileInput');
const clearChatBtn = document.getElementById('clearChatBtn');
const collapseAiBtn = document.getElementById('collapseAiBtn');
const toggleAiDrawerBtn = document.getElementById('toggleAiDrawerBtn');
const aiAdvisorPanel = document.getElementById('aiAdvisorPanel');
const storeLayout = document.getElementById('storeLayout');

// DOM Elements - Catalog
const productGrid = document.getElementById('productGrid');
const catalogTitle = document.getElementById('catalogTitle');
const resultsCount = document.getElementById('resultsCount');
const categoryPillsContainer = document.getElementById('categoryPillsContainer');
const catalogSearchInput = document.getElementById('catalogSearchInput');
const clearSearchBtn = document.getElementById('clearSearchBtn');
const sortSelect = document.getElementById('sortSelect');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const cartWidget = document.getElementById('cartWidget');
const cartCount = document.getElementById('cartCount');
const toastNotification = document.getElementById('toastNotification');
const toastMessage = document.getElementById('toastMessage');

// DOM Elements - Cart Modal
const cartModalBackdrop = document.getElementById('cartModalBackdrop');
const cartModal = document.getElementById('cartModal');
const cartModalBody = document.getElementById('cartModalBody');
const modalCartSubtitle = document.getElementById('modalCartSubtitle');
const cartSubtotal = document.getElementById('cartSubtotal');
const cartTax = document.getElementById('cartTax');
const cartTotal = document.getElementById('cartTotal');
const closeCartModalBtn = document.getElementById('closeCartModalBtn');
const clearCartModalBtn = document.getElementById('clearCartModalBtn');
const checkoutBtn = document.getElementById('checkoutBtn');

// State
let isStreaming = false;
let uploadedFile = null;
let currentCategory = 'All';
let clearanceOnly = false;
let searchQuery = '';
let currentOffset = 0;
const PAGE_LIMIT = 24;
let loadedProducts = [];
let cartTotalItems = 0;
let cartItems = [];
let searchDebounceTimer = null;
let catalogRequestSequence = 0;
let lastRecommendedProducts = [];

// =============================================================================
// CATALOG CONTROLLER
// =============================================================================

async function fetchCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        if (data.categories && data.categories.length > 0) {
            renderCategoryPills(data.categories);
        }
    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

function renderCategoryPills(categories) {
    categoryPillsContainer.innerHTML = '';

    // Sort categories alphabetically
    categories.sort((a, b) => a.category_name.localeCompare(b.category_name));

    categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'category-pill';
        btn.dataset.category = cat.category_name;
        // Format category name nicely: e.g. "POWER TOOLS" -> "Power Tools"
        const formattedName = cat.category_name
            .toLowerCase()
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');

        btn.textContent = `${formattedName} (${cat.product_count})`;
        btn.addEventListener('click', () => selectCategory(cat.category_name, btn));
        categoryPillsContainer.appendChild(btn);
    });

    // "All Products" pill listener
    const allPill = document.querySelector('.category-pill[data-category="All"]');
    if (allPill) {
        allPill.addEventListener('click', () => selectCategory('All', allPill));
    }
}

function selectCategory(categoryName, activeBtn) {
    clearanceOnly = false;
    currentCategory = categoryName;
    currentOffset = 0;

    // Update active pill styling
    document.querySelectorAll('.category-pill').forEach(pill => pill.classList.remove('active'));
    if (activeBtn) activeBtn.classList.add('active');

    // Update catalog title
    if (categoryName === 'All') {
        catalogTitle.textContent = 'All Hardware & Supplies';
    } else {
        const formatted = categoryName
            .toLowerCase()
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
        catalogTitle.textContent = formatted;
    }

    fetchProducts(true);
}

async function fetchProducts(reset = false) {
    const requestSequence = ++catalogRequestSequence;
    if (reset) {
        currentOffset = 0;
        loadedProducts = [];
        loadMoreBtn.style.display = 'none';
        productGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #64748b;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">⏳</div>
                Loading inventory from live database...
            </div>
        `;
    }

    try {
        const params = new URLSearchParams({
            limit: PAGE_LIMIT,
            offset: currentOffset
        });
        if (currentCategory && currentCategory !== 'All') {
            params.append('category', currentCategory);
        }
        if (searchQuery && searchQuery.trim()) {
            params.append('search', searchQuery.trim());
        }

        const response = await fetch(`${clearanceOnly ? '/api/clearance' : '/api/products'}?${params.toString()}`);
        if (!response.ok) throw new Error('Catalog request failed: ' + response.status);
        const data = await response.json();
        if (requestSequence !== catalogRequestSequence) return;
        if (data.error) throw new Error(data.error);

        if (reset) {
            productGrid.innerHTML = '';
        }

        if (data.products && data.products.length > 0) {
            loadedProducts = reset ? data.products : [...loadedProducts, ...data.products];
            renderProducts(data.products, !reset);
            resultsCount.textContent = `Showing ${loadedProducts.length} items`;

            // Show or hide load more
            if (data.products.length < PAGE_LIMIT) {
                loadMoreBtn.style.display = 'none';
            } else {
                loadMoreBtn.style.display = 'inline-block';
            }
        } else {
            if (reset) {
                productGrid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: #64748b;">
                        <div style="font-size: 2.2rem; margin-bottom: 12px;">🔍</div>
                        <h3 style="color: #0f172a; margin-bottom: 6px;">${clearanceOnly ? 'No active clearance offers' : 'No products match your criteria'}</h3>
                        <p>${clearanceOnly ? 'No approved clearance offers match this view. Select All Products to browse the full catalog.' : 'Try searching for a different keyword or selecting another category.'}</p>
                    </div>
                `;
                resultsCount.textContent = '0 items found';
            }
            loadMoreBtn.style.display = 'none';
        }
    } catch (err) {
        if (requestSequence !== catalogRequestSequence) return;
        resultsCount.textContent = 'Catalog unavailable';
        loadMoreBtn.style.display = 'none';
        console.error('Failed to load products:', err);
        productGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #dc2626;">
                Failed to load products from database: ${err.message}
            </div>
        `;
    }
}

function renderProducts(products, append = false) {
    if (!append) {
        productGrid.innerHTML = '';
    }

    products.forEach(product => {
        const card = document.createElement('div');
        card.className = 'product-card';

        // Image handling with fallback
        const imageSrc = product.image_url ? `/images/${product.image_url}` : '/static/favicon.ico';
        const stockStatus = product.total_stock > 0 ?
            `<span class="stock-tag">● In Stock (${product.total_stock.toLocaleString()})</span>` :
            `<span class="stock-tag low-stock">Special Order</span>`;

        card.innerHTML = `
            <div class="product-card-header">
                <img src="${imageSrc}"
                     alt="${escapeHtml(product.product_name)}"
                     class="product-img"
                     loading="lazy"
                     onerror="this.onerror=null; this.src='/static/favicon.ico';" />
                <div class="product-badge-group">
                    <span class="category-tag">${escapeHtml(product.category_name)}</span>
                    ${stockStatus}
                </div>
            </div>
            <div class="product-card-body">
                <div class="product-sku">SKU: ${escapeHtml(product.sku || 'N/A')}</div>
                <h3 class="product-name" title="${escapeHtml(product.product_name)}">${escapeHtml(product.product_name)}</h3>
                <p class="product-desc">${escapeHtml(product.product_description || '')}</p>
                <div class="product-pricing">
                    ${product.sale_price != null ? `<del aria-label="Original price">$${Number(product.base_price).toFixed(2)}</del>` : ''}
                    <span class="product-price">$${catalogPrice(product).toFixed(2)}</span>
                    ${product.sale_price != null ? '<span class="clearance-badge">Clearance</span>' : ''}
                    <span class="stock-count-text">${product.type_name || ''}</span>
                </div>
                <div class="card-actions">
                    <button class="ask-ai-card-btn" title="Ask AI Advisor about using this item">
                        <span>✨ Ask AI</span>
                    </button>
                    <button class="add-cart-card-btn" title="Add to Cart">
                        🛒
                    </button>
                </div>
            </div>
        `;

        // Action: Ask AI Specialist about this product
        const askAiBtn = card.querySelector('.ask-ai-card-btn');
        askAiBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            askAiAboutProduct(product);
        });

        // Action: Add to Cart
        const addCartBtn = card.querySelector('.add-cart-card-btn');
        addCartBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            addToCart(product);
        });

        productGrid.appendChild(card);
    });
}

function askAiAboutProduct(product) {
    // Ensure AI side panel is open and visible
    openAiDrawer();

    const query = `I am planning to use "${product.product_name}" (Category: ${product.category_name}, SKU: ${product.sku}, Price: $${catalogPrice(product).toFixed(2)}) for my DIY project. What are the best practices, critical OSHA/PPE safety precautions, and complementary tools or hardware I will need from Zava DIY?`;

    messageInput.value = query;
    sendMessage();
}

function catalogPrice(product) {
    const price = Number(product.sale_price ?? product.base_price ?? product.price);
    if (!Number.isFinite(price) || price < 0) throw new Error('Invalid catalog price');
    return price;
}

function addToCart(product, qty = 1) {
    const price = catalogPrice(product);
    const existing = cartItems.find(item => item.name === product.product_name || (product.sku && item.sku && item.sku === product.sku));
    if (existing) {
        existing.qty += qty;
        existing.price = price;
    } else {
        cartItems.push({
            id: product.product_id || '',
            name: product.product_name,
            price,
            qty: qty,
            image_url: product.image_url || '',
            sku: product.sku || ''
        });
    }
    updateCartUI();
    showToast(`Added "${product.product_name}" to your cart!`);
}

function updateCartUI() {
    cartTotalItems = cartItems.reduce((sum, item) => sum + item.qty, 0);
    cartCount.textContent = cartTotalItems;

    // Animate cart badge
    cartWidget.style.transform = 'scale(1.25)';
    setTimeout(() => {
        cartWidget.style.transform = 'scale(1)';
    }, 200);

    renderCartModal();
}

function openCartModal() {
    renderCartModal();
    if (cartModalBackdrop) {
        cartModalBackdrop.classList.add('open');
    }
}

function closeCartModal() {
    if (cartModalBackdrop) {
        cartModalBackdrop.classList.remove('open');
    }
}

function renderCartModal() {
    if (!cartModalBody) return;

    if (modalCartSubtitle) {
        modalCartSubtitle.textContent = `${cartTotalItems} item${cartTotalItems === 1 ? '' : 's'} in your cart`;
    }

    if (cartItems.length === 0) {
        cartModalBody.innerHTML = `
            <div class="cart-empty-state">
                <div class="cart-empty-icon">🛒</div>
                <h4>Your cart is empty</h4>
                <p>Browse products or ask the AI Advisor to find project materials!</p>
            </div>
        `;
        if (cartSubtotal) cartSubtotal.textContent = '$0.00';
        if (cartTax) cartTax.textContent = '$0.00';
        if (cartTotal) cartTotal.textContent = '$0.00';
        return;
    }

    let subtotal = 0;
    cartModalBody.innerHTML = '';

    cartItems.forEach((item, index) => {
        const itemTotal = item.price * item.qty;
        subtotal += itemTotal;

        const itemCard = document.createElement('div');
        itemCard.className = 'cart-item-card';

        const imgSrc = item.image_url ? `/images/${item.image_url}` : '/static/favicon.ico';

        itemCard.innerHTML = `
            <img src="${imgSrc}" class="cart-item-img" alt="${escapeHtml(item.name)}" onerror="this.src='/static/favicon.ico';" />
            <div class="cart-item-details">
                <div class="cart-item-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
                <div class="cart-item-price">$${item.price.toFixed(2)} each</div>
            </div>
            <div class="cart-item-controls">
                <button class="cart-qty-btn dec-btn" data-index="${index}">-</button>
                <span class="cart-qty-val">${item.qty}</span>
                <button class="cart-qty-btn inc-btn" data-index="${index}">+</button>
                <button class="cart-item-delete" data-index="${index}" title="Remove item">✕</button>
            </div>
        `;
        cartModalBody.appendChild(itemCard);
    });

    const tax = subtotal * 0.085;
    const total = subtotal + tax;

    if (cartSubtotal) cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
    if (cartTax) cartTax.textContent = `$${tax.toFixed(2)}`;
    if (cartTotal) cartTotal.textContent = `$${total.toFixed(2)}`;

    // Quantity dec button
    cartModalBody.querySelectorAll('.dec-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.index);
            cartItems[idx].qty -= 1;
            if (cartItems[idx].qty <= 0) {
                cartItems.splice(idx, 1);
            }
            updateCartUI();
        });
    });

    // Quantity inc button
    cartModalBody.querySelectorAll('.inc-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.index);
            cartItems[idx].qty += 1;
            updateCartUI();
        });
    });

    // Delete item button
    cartModalBody.querySelectorAll('.cart-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.index);
            const removed = cartItems.splice(idx, 1);
            updateCartUI();
            if (removed[0]) showToast(`Removed "${removed[0].name}" from cart`);
        });
    });
}

function showToast(msg) {
    toastMessage.textContent = msg;
    toastNotification.classList.add('show');
    setTimeout(() => {
        toastNotification.classList.remove('show');
    }, 3000);
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}


// =============================================================================
// MULTI-AGENT CHAT CONTROLLER (PORT 8005 <--> PORT 8006)
// =============================================================================

function addMessage(content, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    if (isUser) {
        messageDiv.textContent = content;
    } else {
        messageDiv.innerHTML = marked.parse(content);
    }
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return messageDiv;
}

function addFileInfo(fileName, fileSize) {
    const fileInfoDiv = document.createElement('div');
    fileInfoDiv.className = 'file-info';
    fileInfoDiv.innerHTML = `
        📄 <span class="file-name">${escapeHtml(fileName)}</span>
        <span class="file-size">(${formatFileSize(fileSize)})</span>
    `;
    messagesDiv.appendChild(fileInfoDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return fileInfoDiv;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function handleFileSelection() {
    const file = fileInput.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        fileInput.value = '';
        return;
    }

    uploadedFile = file;
    addFileInfo(file.name, file.size);
    messageInput.placeholder = `File attached: ${file.name}. Type your question and click send.`;
}

let bundleAddInProgress = false;

async function executeAddAllToCart() {
    if (bundleAddInProgress) return null;
    bundleAddInProgress = true;
    const recommendations = [...lastRecommendedProducts];
    const added = [];
    const unavailable = [];
    const normalize = name => name.trim().toLowerCase().replace(/\s+/g, ' ');
    try {
        for (const item of recommendations) {
            const name = typeof item === 'string' ? item : item.name;
            let product = loadedProducts.find(p => normalize(p.product_name || '') === normalize(name));
            if (!product) {
                try {
                    const response = await fetch('/api/products?search=' + encodeURIComponent(name) + '&limit=50');
                    if (!response.ok) throw new Error('Catalog request failed: ' + response.status);
                    const data = await response.json();
                    product = (data.products || []).find(p => normalize(p.product_name || '') === normalize(name));
                } catch (error) {
                    console.error('Could not resolve recommended product', name, error);
                }
            }
            if (!product || !Number.isFinite(Number(product.base_price)) || Number(product.base_price) < 0) {
                unavailable.push(name);
                continue;
            }
            addToCart(product, 1);
            added.push(product.product_name);
        }
        updateCartUI();
        showToast('Added ' + added.length + ' of ' + recommendations.length + ' items' +
            (unavailable.length ? '. Unavailable: ' + unavailable.join(', ') : '.'));
        return { added, unavailable, requested: recommendations.length };
    } finally {
        bundleAddInProgress = false;
    }
}

function attachCartActions(assistantDiv) {
    const productLinks = assistantDiv.querySelectorAll('a[href^="#product="]');
    if (productLinks.length > 0) {
        const foundProducts = Array.from(productLinks).map(a => {
            const href = a.getAttribute('href') || '';
            const keyword = decodeURIComponent(href.replace('#product=', '').replace(/\+/g, ' ')).trim();
            const linkText = (a.textContent || '').trim();
            return {
                name: linkText || keyword,
                keyword: keyword
            };
        });

        // Deduplicate products by display name
        const uniqueProducts = [];
        const seenNames = new Set();
        for (const item of foundProducts) {
            const key = item.name.toLowerCase();
            if (!seenNames.has(key)) {
                seenNames.add(key);
                uniqueProducts.push(item);
            }
        }
        lastRecommendedProducts = uniqueProducts;

        if (!assistantDiv.querySelector('.cart-action-bar') && lastRecommendedProducts.length > 0) {
            const bar = document.createElement('div');
            bar.className = 'cart-action-bar';
            bar.style.marginTop = '14px';
            bar.style.paddingTop = '10px';
            bar.style.borderTop = '1px dashed #cbd5e1';

            const btn = document.createElement('button');
            btn.className = 'add-all-cart-btn';
            btn.innerHTML = `🛒 <strong>Yes, Add All (${lastRecommendedProducts.length} items) to Cart</strong>`;
            btn.style.backgroundColor = '#ea580c';
            btn.style.color = '#ffffff';
            btn.style.border = 'none';
            btn.style.padding = '8px 16px';
            btn.style.borderRadius = '8px';
            btn.style.fontWeight = '600';
            btn.style.cursor = 'pointer';
            btn.style.fontSize = '0.9rem';
            btn.style.boxShadow = '0 2px 6px rgba(234, 88, 12, 0.3)';
            btn.style.transition = 'all 0.2s ease';

            btn.onmouseover = () => { btn.style.backgroundColor = '#c2410c'; };
            btn.onmouseout = () => { btn.style.backgroundColor = '#ea580c'; };

            btn.onclick = async () => {
                btn.disabled = true;
                btn.textContent = 'Adding items...';
                const result = await executeAddAllToCart();
                if (!result) {
                    btn.disabled = false;
                    btn.textContent = 'Another cart update is in progress. Try again.';
                    return;
                }
                btn.textContent = `Added ${result.added.length} of ${result.requested} items` +
                    (result.unavailable.length ? ` — Unavailable: ${result.unavailable.join(', ')}` : '');
                btn.style.backgroundColor = result.unavailable.length ? '#b45309' : '#16a34a';
                btn.style.boxShadow = 'none';
            };

            bar.appendChild(btn);
            assistantDiv.appendChild(bar);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if ((!message && !uploadedFile) || isStreaming) return;

    // Check if user is confirming adding to cart (e.g. "yes", "add to cart", "ok")
    const isAffirmative = /^(yes|yeah|yep|sure|ok|okay|add|please|add to cart|add them|add all|yes please|y)$/i.test(message.trim());
    if (isAffirmative && lastRecommendedProducts && lastRecommendedProducts.length > 0) {
        addMessage(message, true);
        messageInput.value = '';
        executeAddAllToCart();

        const itemsList = result.added.map(name => `• **${name}**`).join('\n');
        const confirmMsg = `🛒 **Items Added to Your Shopping Cart!**\n\nI've added the following items to your cart:\n${itemsList}\n\nYour cart now has **${cartTotalItems} item(s)**. You can review your cart at the top right, or let me know if you have questions about the installation steps!`;
        addMessage(confirmMsg + (result.unavailable.length ? "\n\nUnavailable: " + result.unavailable.join(", ") : ""), false);

        // Reset to prevent double catching
        lastRecommendedProducts = [];
        return;
    }

    isStreaming = true;
    sendBtn.disabled = true;
    fileBtn.disabled = true;

    try {
        let finalMessage = message;

        if (uploadedFile) {
            const fileMessage = message ?
                `${message}\n\n📄 Uploaded file: ${uploadedFile.name}` :
                `📄 Please analyze this project attachment: ${uploadedFile.name}`;
            addMessage(fileMessage, true);

            const formData = new FormData();
            formData.append('file', uploadedFile);
            if (message) formData.append('message', message);

            const uploadResponse = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('File upload failed');
            }

            const uploadResult = await uploadResponse.json();
            finalMessage = uploadResult.content || 'Please analyze this file.';
            uploadedFile = null;
            fileInput.value = '';
            messageInput.placeholder = 'Ask about any DIY project, tool specs, or safety protocols...';
        } else {
            addMessage(message, true);
        }

        messageInput.value = '';

        // Assistant streaming container
        const assistantDiv = document.createElement('div');
        assistantDiv.className = 'message assistant';
        messagesDiv.appendChild(assistantDiv);

        // Stream via Server-Sent Events from web_app.py
        const eventSource = new EventSource('/chat/stream?' + new URLSearchParams({
            message: finalMessage
        }));

        let assistantMessage = '';

        eventSource.onmessage = function(event) {
            if (event.data === '[DONE]') {
                assistantDiv.innerHTML = marked.parse(assistantMessage);
                attachCartActions(assistantDiv);
                eventSource.close();
                isStreaming = false;
                sendBtn.disabled = false;
                fileBtn.disabled = false;
                messageInput.focus();
                return;
            }

            try {
                const parsed = JSON.parse(event.data);

                if (parsed.action === 'add_all_to_cart') {
                    executeAddAllToCart();
                }

                if (parsed.content) {
                    assistantMessage += parsed.content;
                    assistantDiv.innerHTML = marked.parse(assistantMessage);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                } else if (parsed.done) {
                    assistantDiv.innerHTML = marked.parse(assistantMessage);
                    attachCartActions(assistantDiv);
                    eventSource.close();
                    isStreaming = false;
                    sendBtn.disabled = false;
                    fileBtn.disabled = false;
                    messageInput.focus();
                } else if (parsed.error) {
                    assistantDiv.innerHTML = `<span style="color: #dc2626;">Error: ${escapeHtml(parsed.error)}</span>`;
                    eventSource.close();
                    isStreaming = false;
                    sendBtn.disabled = false;
                    fileBtn.disabled = false;
                    messageInput.focus();
                }
            } catch (e) {
                console.error('SSE JSON error:', e);
            }
        };

        eventSource.onerror = function(event) {
            console.error('EventSource error:', event);
            if (!assistantMessage) {
                assistantDiv.innerHTML = '<span style="color: #dc2626;">Unable to reach Agent Backend Service. Please verify agent_service.py is running on port 8006.</span>';
            } else {
                assistantDiv.innerHTML = marked.parse(assistantMessage);
            }
            eventSource.close();
            isStreaming = false;
            sendBtn.disabled = false;
            fileBtn.disabled = false;
            messageInput.focus();
        };

    } catch (error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message assistant';
        errorDiv.innerHTML = `<span style="color: #dc2626;">Error: ${escapeHtml(error.message)}</span>`;
        messagesDiv.appendChild(errorDiv);

        isStreaming = false;
        sendBtn.disabled = false;
        fileBtn.disabled = false;
        messageInput.focus();
    }
}


// =============================================================================
// UI DRAWER & INTERACTION HANDLERS
// =============================================================================

function openAiDrawer() {
    if (window.innerWidth <= 1024) {
        aiAdvisorPanel.classList.add('open');
    } else {
        storeLayout.classList.remove('chat-collapsed');
        toggleAiDrawerBtn.classList.add('active');
    }
}

function closeAiDrawer() {
    if (window.innerWidth <= 1024) {
        aiAdvisorPanel.classList.remove('open');
    } else {
        storeLayout.classList.add('chat-collapsed');
        toggleAiDrawerBtn.classList.remove('active');
    }
}

function toggleAiDrawer() {
    if (window.innerWidth <= 1024) {
        aiAdvisorPanel.classList.toggle('open');
    } else {
        storeLayout.classList.toggle('chat-collapsed');
        toggleAiDrawerBtn.classList.toggle('active');
    }
}

// Quick Prompt Chips
document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const promptText = chip.dataset.prompt;
        openAiDrawer();
        messageInput.value = promptText;
        sendMessage();
    });
});

// Clear Chat History
if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
        messagesDiv.innerHTML = `
            <div class="message assistant welcome-message">
                <div class="welcome-header">👋 Conversation Cleared</div>
                <p>Ask a new question or click <strong>✨ Ask AI Advisor</strong> on any catalog item.</p>
            </div>
        `;
    });
}

// Collapse Drawer Button
if (collapseAiBtn) {
    collapseAiBtn.addEventListener('click', closeAiDrawer);
}

// Header Toggle Button
if (toggleAiDrawerBtn) {
    toggleAiDrawerBtn.addEventListener('click', toggleAiDrawer);
}

// Search Input Listener (Debounced)
const shopClearanceBtn = document.getElementById('shopClearanceBtn');
if (shopClearanceBtn) shopClearanceBtn.addEventListener('click', () => {
    clearanceOnly = true;
    currentCategory = 'All';
    searchQuery = '';
    catalogSearchInput.value = '';
    clearSearchBtn.style.display = 'none';
    clearTimeout(searchDebounceTimer);
    document.querySelectorAll('.category-pill').forEach(pill => pill.classList.remove('active'));
    catalogTitle.textContent = 'Clearance & Overstock Specials';
    fetchProducts(true);
    document.getElementById('catalogSection').scrollIntoView({behavior: 'smooth'});
});

catalogSearchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    clearSearchBtn.style.display = searchQuery ? 'block' : 'none';

    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        fetchProducts(true);
    }, 300);
});

clearSearchBtn.addEventListener('click', () => {
    catalogSearchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    fetchProducts(true);
});

// Sort Dropdown
sortSelect.addEventListener('change', () => {
    const sortVal = sortSelect.value;
    if (sortVal === 'price-asc') {
        loadedProducts.sort((a, b) => catalogPrice(a) - catalogPrice(b));
    } else if (sortVal === 'price-desc') {
        loadedProducts.sort((a, b) => catalogPrice(b) - catalogPrice(a));
    } else if (sortVal === 'stock-desc') {
        loadedProducts.sort((a, b) => b.total_stock - a.total_stock);
    } else {
        loadedProducts.sort((a, b) => a.product_name.localeCompare(b.product_name));
    }
    renderProducts(loadedProducts, false);
});

// Load More Button
loadMoreBtn.addEventListener('click', () => {
    currentOffset += PAGE_LIMIT;
    fetchProducts(false);
});

// Chat Input Keys
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// File Upload
fileBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelection);

// Cart Click -> Open Cart Modal
cartWidget.addEventListener('click', openCartModal);

// Close Cart Modal
if (closeCartModalBtn) closeCartModalBtn.addEventListener('click', closeCartModal);
if (cartModalBackdrop) {
    cartModalBackdrop.addEventListener('click', (e) => {
        if (e.target === cartModalBackdrop) closeCartModal();
    });
}

// Clear Cart Modal
if (clearCartModalBtn) {
    clearCartModalBtn.addEventListener('click', () => {
        cartItems = [];
        updateCartUI();
        showToast('Cart has been cleared');
    });
}

// Checkout Button
if (checkoutBtn) {
    checkoutBtn.addEventListener('click', () => {
        if (cartItems.length === 0) {
            alert('Your cart is currently empty!');
            return;
        }
        const orderId = 'ZV-' + Math.floor(100000 + Math.random() * 900000);
        const totalAmount = cartTotal ? cartTotal.textContent : '$0.00';
        alert(`🎉 Order Placed Successfully!\n\nThank you for choosing Zava DIY Hardware!\nYour Order Number: ${orderId}\nTotal: ${totalAmount}\n\nYour items are reserved and ready for pickup at our Seattle store.`);
        cartItems = [];
        updateCartUI();
        closeCartModal();
    });
}

// Delegate clicks on product links inside chat messages
messagesDiv.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;

    const href = link.getAttribute('href') || '';
    if (href.startsWith('#product=') || href.startsWith('#sku=')) {
        e.preventDefault();
        let queryTerm = '';
        if (href.startsWith('#product=')) {
            queryTerm = decodeURIComponent(href.replace('#product=', '').replace(/\+/g, ' ')).trim();
        } else if (href.startsWith('#sku=')) {
            queryTerm = decodeURIComponent(href.replace('#sku=', '').replace(/\+/g, ' ')).trim();
        }

        if (queryTerm) {
            catalogSearchInput.value = queryTerm;
            searchQuery = queryTerm;
            clearSearchBtn.style.display = 'block';

            // Switch category filter to All
            currentCategory = 'All';
            clearanceOnly = false;
            document.querySelectorAll('.category-pill').forEach(pill => {
                pill.classList.toggle('active', pill.dataset.category === 'All');
            });

            catalogTitle.textContent = `Search: "${queryTerm}"`;
            fetchProducts(true);
            showToast(`Loading "${queryTerm}" in catalog...`);

            // On mobile devices, close drawer so customer sees product card
            if (window.innerWidth <= 1024) {
                closeAiDrawer();
            }

            // Scroll to catalog grid smoothly
            const targetPos = productGrid.getBoundingClientRect().top + window.pageYOffset - 120;
            window.scrollTo({ top: targetPos, behavior: 'smooth' });
        }
    }
});

// Initialize on page load (handles already loaded DOM)
function initApp() {
    fetchCategories();
    fetchProducts(true);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
