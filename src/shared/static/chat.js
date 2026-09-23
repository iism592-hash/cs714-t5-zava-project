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

// State
let isStreaming = false;
let uploadedFile = null;
let currentCategory = 'All';
let searchQuery = '';
let currentOffset = 0;
const PAGE_LIMIT = 24;
let loadedProducts = [];
let cartTotalItems = 0;
let searchDebounceTimer = null;

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
    if (reset) {
        currentOffset = 0;
        loadedProducts = [];
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

        const response = await fetch(`/api/products?${params.toString()}`);
        const data = await response.json();

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
                        <h3 style="color: #0f172a; margin-bottom: 6px;">No products match your criteria</h3>
                        <p>Try searching for a different keyword or selecting another category.</p>
                    </div>
                `;
                resultsCount.textContent = '0 items found';
            }
            loadMoreBtn.style.display = 'none';
        }
    } catch (err) {
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
                    <span class="product-price">$${product.base_price ? product.base_price.toFixed(2) : '0.00'}</span>
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

    const query = `I am planning to use "${product.product_name}" (Category: ${product.category_name}, SKU: ${product.sku}, Price: $${product.base_price.toFixed(2)}) for my DIY project. What are the best practices, critical OSHA/PPE safety precautions, and complementary tools or hardware I will need from Zava DIY?`;
    
    messageInput.value = query;
    sendMessage();
}

function addToCart(product) {
    cartTotalItems += 1;
    cartCount.textContent = cartTotalItems;
    
    // Animate cart badge
    cartWidget.style.transform = 'scale(1.15)';
    setTimeout(() => {
        cartWidget.style.transform = 'scale(1)';
    }, 200);

    showToast(`Added "${product.product_name}" to your cart!`);
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

async function sendMessage() {
    const message = messageInput.value.trim();
    if ((!message && !uploadedFile) || isStreaming) return;
    
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
                eventSource.close();
                isStreaming = false;
                sendBtn.disabled = false;
                fileBtn.disabled = false;
                messageInput.focus();
                return;
            }
            
            try {
                const parsed = JSON.parse(event.data);
                
                if (parsed.content) {
                    assistantMessage += parsed.content;
                    assistantDiv.innerHTML = marked.parse(assistantMessage);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                } else if (parsed.done) {
                    assistantDiv.innerHTML = marked.parse(assistantMessage);
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
        loadedProducts.sort((a, b) => a.base_price - b.base_price);
    } else if (sortVal === 'price-desc') {
        loadedProducts.sort((a, b) => b.base_price - a.base_price);
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

// Cart Click
cartWidget.addEventListener('click', () => {
    showToast(`You have ${cartTotalItems} item(s) in your cart.`);
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
