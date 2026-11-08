import QRCode from 'qrcode';
import { showToast } from './shop.js';

export function formatChf(cents) {
    return (cents / 100).toFixed(2);
}

export function calculateTotals(products, basket, discountConfig = { mode: 'none', value: 0 }) {
    let itemCount = 0;
    let subtotalCents = 0;

    for (const [idStr, qty] of Object.entries(basket)) {
        const productId = parseInt(idStr, 10);
        const product = products.find(p => p.id === productId);
        if (product && qty > 0) {
            itemCount += qty;
            subtotalCents += product.price_cents * qty;
        }
    }

    let discountCents = 0;
    if (subtotalCents > 0 && discountConfig && discountConfig.mode !== 'none') {
        const rawVal = Number(discountConfig.value) || 0;
        if (discountConfig.mode === 'percent' && rawVal > 0) {
            discountCents = Math.round(subtotalCents * (rawVal / 100));
        } else if (discountConfig.mode === 'custom_discount' && rawVal > 0) {
            discountCents = Math.round(rawVal * 100);
        } else if (discountConfig.mode === 'custom_total' && rawVal > 0) {
            const targetCents = Math.round(rawVal * 100);
            if (targetCents < subtotalCents) {
                discountCents = subtotalCents - targetCents;
            }
        }
    }

    const maxDiscount = Math.max(0, subtotalCents - 50);
    discountCents = Math.max(0, Math.min(discountCents, maxDiscount));
    const totalCents = Math.max(0, subtotalCents - discountCents);

    return {
        itemCount,
        subtotalCents,
        discountCents,
        totalCents,
        subtotalChf: formatChf(subtotalCents),
        discountChf: formatChf(discountCents),
        totalChf: formatChf(totalCents),
    };
}

export function filterProducts(products, filters = {}) {
    const query = (filters.query || '').trim().toLowerCase();
    const brand = filters.brand || '';
    const type = filters.type || '';
    const inStockOnly = filters.inStockOnly !== undefined ? Boolean(filters.inStockOnly) : true;

    return products.filter(p => {
        if (inStockOnly && p.stock <= 0) return false;
        if (brand && p.brand_slug !== brand) return false;
        if (type && p.type_slug !== type) return false;
        if (query) {
            const haystack = `${p.name} ${p.brand_name || ''} ${p.type_name || ''} ${p.glaze_name || ''}`.toLowerCase();
            if (!haystack.includes(query)) return false;
        }
        return true;
    });
}

export function getPosUrl(currentUrlStr, filters = {}, isExpanded = false) {
    const url = new URL(currentUrlStr);
    const params = url.searchParams;

    if (filters.query) params.set('q', filters.query);
    else params.delete('q');

    if (filters.brand) params.set('brand', filters.brand);
    else params.delete('brand');

    if (filters.type) params.set('type', filters.type);
    else params.delete('type');

    if (filters.inStockOnly === false) params.set('in_stock', 'false');
    else params.delete('in_stock');

    if (isExpanded) params.set('expanded', 'true');
    else params.delete('expanded');

    return url.toString();
}

export function readPosUrlState(currentUrlStr) {
    const url = new URL(currentUrlStr);
    const params = url.searchParams;
    return {
        query: params.get('q') || '',
        brand: params.get('brand') || '',
        type: params.get('type') || '',
        inStockOnly: params.get('in_stock') !== 'false',
        isExpanded: params.get('expanded') === 'true',
    };
}

export function updateBasketItem(products, basket, productId, newQty) {
    const nextBasket = { ...basket };
    const product = products.find(p => p.id === productId);
    if (!product) {
        return { basket: nextBasket, limitReached: false, maxStock: 0 };
    }

    const parsedQty = parseInt(newQty, 10) || 0;
    if (parsedQty <= 0) {
        delete nextBasket[productId];
        return { basket: nextBasket, limitReached: false, maxStock: product.stock };
    }

    if (parsedQty > product.stock) {
        if (product.stock > 0) {
            nextBasket[productId] = product.stock;
        } else {
            delete nextBasket[productId];
        }
        return { basket: nextBasket, limitReached: true, maxStock: product.stock };
    }

    nextBasket[productId] = parsedQty;
    return { basket: nextBasket, limitReached: false, maxStock: product.stock };
}

export async function renderQrSvg(url) {
    if (!url) return '';
    return await QRCode.toString(url, {
        type: 'svg',
        margin: 1,
        color: {
            dark: '#2c2c2c',
            light: '#fdfcfb',
        },
    });
}

export function initPosApp() {
    const appEl = document.getElementById('pos-app');
    if (!appEl) return;

    const dataEl = document.getElementById('pos-products-data');
    let products = [];
    if (dataEl) {
        try {
            products = JSON.parse(dataEl.textContent);
        } catch {
            products = [];
        }
    }

    const createSaleUrl = appEl.dataset.createSaleUrl;
    const statusUrlTemplate = appEl.dataset.statusUrlTemplate;
    const csrfToken = appEl.dataset.csrfToken;
    const i18nStockLimit = appEl.dataset.i18nStockLimit || 'Only X left in stock';
    const i18nCopied = appEl.dataset.i18nCopied || 'Amount copied to clipboard';
    const i18nReceiptSent = appEl.dataset.i18nReceiptSent || 'Receipt sent!';

    const initialState = readPosUrlState(window.location.href);
    let filters = {
        query: initialState.query,
        brand: initialState.brand,
        type: initialState.type,
        inStockOnly: initialState.inStockOnly,
    };
    let isDrawerOpen = initialState.isExpanded;
    let basket = {};
    let discountConfig = { mode: 'none', value: 0 };
    let wantsReceipt = false;
    let customerEmail = '';
    let activeSaleId = null;
    let pollInterval = null;

    const searchInput = document.getElementById('pos-search-input');
    const inStockToggle = document.getElementById('pos-in-stock-toggle');
    const productGrid = document.getElementById('pos-product-grid');
    const emptyState = document.getElementById('pos-empty-state');
    const bottomBar = document.getElementById('pos-bottom-bar');
    const bottomCount = document.getElementById('pos-bottom-count');
    const bottomTotal = document.getElementById('pos-bottom-total');
    const checkoutDrawer = document.getElementById('pos-checkout-drawer');
    const checkoutOverlay = document.getElementById('pos-checkout-overlay');
    const basketList = document.getElementById('pos-basket-items');
    const subtotalEl = document.getElementById('pos-subtotal-display');
    const discountRowEl = document.getElementById('pos-discount-row');
    const discountEl = document.getElementById('pos-discount-display');
    const totalEl = document.getElementById('pos-total-display');
    const customDiscountBtn = document.getElementById('pos-discount-custom-btn');
    const customDiscountWrap = document.getElementById('pos-custom-discount-wrap');
    const customDiscountInput = document.getElementById('pos-custom-discount-input');
    const customTotalInput = document.getElementById('pos-custom-total-input');
    const receiptNoBtn = document.getElementById('pos-receipt-no');
    const receiptYesBtn = document.getElementById('pos-receipt-yes');
    const receiptEmailWrap = document.getElementById('pos-receipt-email-wrap');
    const receiptEmailInput = document.getElementById('pos-receipt-email-input');
    const tapToPayBtn = document.getElementById('pos-btn-tap-to-pay');
    const twintBtn = document.getElementById('pos-btn-twint');

    // Modals for Waiting & Completion
    const paymentModal = document.getElementById('pos-payment-modal');
    const waitingView = document.getElementById('pos-waiting-view');
    const completedView = document.getElementById('pos-completed-view');
    const waitingAmountEl = document.getElementById('pos-waiting-amount');
    const tapInstructionsEl = document.getElementById('pos-tap-instructions');
    const twintQrContainer = document.getElementById('pos-twint-qr-container');
    const twintSvgHolder = document.getElementById('pos-twint-svg');
    const twintExternalLink = document.getElementById('pos-twint-external-link');
    const copyAmountBtn = document.getElementById('pos-copy-amount-btn');
    const cancelSaleBtn = document.getElementById('pos-cancel-sale-btn');
    const completedTotalEl = document.getElementById('pos-completed-total');
    const lateReceiptWrap = document.getElementById('pos-late-receipt-wrap');
    const lateReceiptSentMsg = document.getElementById('pos-late-receipt-sent');
    const lateReceiptEmailInput = document.getElementById('pos-late-receipt-email');
    const lateReceiptSendBtn = document.getElementById('pos-late-receipt-btn');
    const newSaleBtn = document.getElementById('pos-new-sale-btn');

    function blurActiveInput() {
        if (searchInput) {
            searchInput.setAttribute('readonly', '');
            searchInput.setAttribute('tabindex', '-1');
        }
        const active = document.activeElement;
        if (
            active &&
            (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT') &&
            typeof active.blur === 'function'
        ) {
            active.blur();
        }
    }

    function syncUrl() {
        const nextUrl = getPosUrl(window.location.href, filters, isDrawerOpen);
        window.history.replaceState(null, '', nextUrl);
    }

    function setDrawerOpen(open) {
        blurActiveInput();
        const totals = calculateTotals(products, basket, discountConfig);
        if (open && totals.itemCount === 0) return;
        isDrawerOpen = open;
        if (checkoutDrawer && checkoutOverlay) {
            if (open) {
                checkoutDrawer.classList.remove('hidden', 'translate-y-full');
                checkoutOverlay.classList.remove('hidden');
            } else {
                checkoutDrawer.classList.add('translate-y-full', 'hidden');
                checkoutOverlay.classList.add('hidden');
            }
        }
        syncUrl();
    }

    function handleQtyChange(productId, targetQty) {
        blurActiveInput();
        const result = updateBasketItem(products, basket, productId, targetQty);
        basket = result.basket;
        if (result.limitReached) {
            showToast(i18nStockLimit.replace('X', result.maxStock), 'error');
        }
        const totals = calculateTotals(products, basket, discountConfig);
        if (totals.itemCount === 0 && isDrawerOpen) {
            setDrawerOpen(false);
        }
        renderAll();
    }

    function renderFilterState() {
        if (searchInput && searchInput.value !== filters.query) {
            searchInput.value = filters.query;
        }
        if (inStockToggle) {
            inStockToggle.classList.toggle('active', filters.inStockOnly);
        }
        document.querySelectorAll('[data-pos-brand]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.posBrand === filters.brand);
        });
        document.querySelectorAll('[data-pos-type]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.posType === filters.type);
        });
    }

    function renderProducts() {
        if (!productGrid) return;
        const visible = filterProducts(products, filters);
        productGrid.replaceChildren();

        if (visible.length === 0) {
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        if (emptyState) emptyState.classList.add('hidden');

        visible.forEach(p => {
            const selectedQty = basket[p.id] || 0;
            const outOfStock = p.stock <= 0;
            const card = document.createElement('div');
            card.className = `pos-product-card bg-white border rounded-[4px] p-2.5 flex flex-col justify-between transition-all ${
                selectedQty > 0
                    ? 'border-brand-accent ring-1 ring-brand-accent bg-[#f7f9f7]'
                    : 'border-brand-border'
            } ${outOfStock ? 'opacity-50' : 'cursor-pointer'}`;
            card.dataset.productId = String(p.id);

            const topSection = document.createElement('div');
            const imageWrapper = document.createElement('div');
            imageWrapper.className = 'relative';

            if (p.image) {
                const img = document.createElement('img');
                img.src = p.image;
                img.alt = p.name;
                img.className = 'w-full aspect-square object-cover rounded-[2px] mb-2';
                imageWrapper.appendChild(img);
            } else {
                const noImg = document.createElement('div');
                noImg.className = 'w-full aspect-square bg-brand-border/40 rounded-[2px] mb-2 flex items-center justify-center text-brand-muted text-xs';
                noImg.textContent = 'No image';
                imageWrapper.appendChild(noImg);
            }

            const stockBadge = document.createElement('span');
            stockBadge.className = 'absolute top-1.5 right-1.5 bg-white/90 px-1.5 py-0.5 text-[0.75rem] rounded border border-brand-border text-brand-text';
            stockBadge.textContent = `${p.stock} left`;
            imageWrapper.appendChild(stockBadge);

            const brandEl = document.createElement('p');
            brandEl.className = 'text-[0.75rem] text-brand-muted uppercase tracking-wider truncate m-0';
            brandEl.textContent = p.brand_name || '\u00a0';

            const nameEl = document.createElement('h3');
            nameEl.className = 'text-[1rem] font-medium leading-tight m-0 mt-0.5 line-clamp-2';
            nameEl.textContent = p.name;

            const priceEl = document.createElement('p');
            priceEl.className = 'text-[0.95rem] font-semibold text-brand-text m-0 mt-1';
            priceEl.textContent = `CHF ${p.price_chf.toFixed(2)}`;

            topSection.appendChild(imageWrapper);
            topSection.appendChild(brandEl);
            topSection.appendChild(nameEl);
            topSection.appendChild(priceEl);
            card.appendChild(topSection);

            if (selectedQty > 0) {
                const stepper = document.createElement('div');
                stepper.className = 'flex items-center justify-between mt-2 pt-2 border-t border-brand-border';
                stepper.dataset.posStepper = '';

                const minusBtn = document.createElement('button');
                minusBtn.type = 'button';
                minusBtn.className = 'pos-step-minus w-8 h-8 flex items-center justify-center bg-white border border-brand-border rounded text-lg leading-none';
                minusBtn.dataset.id = String(p.id);
                minusBtn.textContent = '-';

                const qtySpan = document.createElement('span');
                qtySpan.className = 'font-bold text-base';
                qtySpan.textContent = String(selectedQty);

                const plusBtn = document.createElement('button');
                plusBtn.type = 'button';
                plusBtn.className = 'pos-step-plus w-8 h-8 flex items-center justify-center bg-brand-accent text-white border-none rounded text-lg leading-none';
                plusBtn.dataset.id = String(p.id);
                plusBtn.textContent = '+';

                stepper.appendChild(minusBtn);
                stepper.appendChild(qtySpan);
                stepper.appendChild(plusBtn);
                card.appendChild(stepper);
            }

            card.addEventListener('click', (e) => {
                e.preventDefault();
                blurActiveInput();
                if (outOfStock) return;
                if (e.target.closest('.pos-step-minus')) {
                    e.stopPropagation();
                    handleQtyChange(p.id, selectedQty - 1);
                    return;
                }
                if (e.target.closest('.pos-step-plus')) {
                    e.stopPropagation();
                    handleQtyChange(p.id, selectedQty + 1);
                    return;
                }
                handleQtyChange(p.id, selectedQty + 1);
            });

            productGrid.appendChild(card);
        });
    }

    function renderBasketAndTotals() {
        const totals = calculateTotals(products, basket, discountConfig);

        if (bottomBar) {
            if (totals.itemCount > 0) {
                bottomBar.classList.remove('translate-y-full');
            } else {
                bottomBar.classList.add('translate-y-full');
            }
        }
        if (bottomCount) bottomCount.textContent = totals.itemCount;
        if (bottomTotal) bottomTotal.textContent = `CHF ${totals.totalChf}`;

        if (subtotalEl) subtotalEl.textContent = `CHF ${totals.subtotalChf}`;
        if (discountRowEl && discountEl) {
            if (totals.discountCents > 0) {
                discountRowEl.classList.remove('hidden');
                discountEl.textContent = `- CHF ${totals.discountChf}`;
            } else {
                discountRowEl.classList.add('hidden');
            }
        }
        if (totalEl) totalEl.textContent = `CHF ${totals.totalChf}`;

        // Discount pills active state
        const isCustomMode =
            discountConfig.mode === 'custom_discount' || discountConfig.mode === 'custom_total';
        document.querySelectorAll('[data-pos-discount-pct]').forEach(btn => {
            const pct = Number(btn.dataset.posDiscountPct);
            const isActive =
                !isCustomMode &&
                ((pct === 0 && discountConfig.mode === 'none') ||
                    (discountConfig.mode === 'percent' && Number(discountConfig.value) === pct));
            btn.classList.toggle('active', isActive);
        });
        if (customDiscountBtn) {
            const isWrapVisible = customDiscountWrap && !customDiscountWrap.classList.contains('hidden');
            customDiscountBtn.classList.toggle('active', isCustomMode || Boolean(isWrapVisible));
        }

        if (basketList) {
            basketList.replaceChildren();
            for (const [idStr, qty] of Object.entries(basket)) {
                const productId = parseInt(idStr, 10);
                const product = products.find(p => p.id === productId);
                if (!product || qty <= 0) continue;

                const row = document.createElement('div');
                row.className = 'flex items-center justify-between py-2.5 border-b border-brand-border gap-3';
                const lineChf = formatChf(product.price_cents * qty);

                const infoDiv = document.createElement('div');
                infoDiv.className = 'flex-grow min-w-0';

                const titleP = document.createElement('p');
                titleP.className = 'm-0 font-medium text-[1rem] truncate';
                titleP.textContent = product.name;

                const subP = document.createElement('p');
                subP.className = 'm-0 text-[0.85rem] text-brand-muted';
                subP.textContent = `CHF ${product.price_chf.toFixed(2)} \u00d7 ${qty} = CHF ${lineChf}`;

                infoDiv.appendChild(titleP);
                infoDiv.appendChild(subP);

                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'flex items-center gap-2 flex-shrink-0';

                const minusBtn = document.createElement('button');
                minusBtn.type = 'button';
                minusBtn.className = 'pos-drawer-minus w-8 h-8 flex items-center justify-center bg-white border border-brand-border rounded';
                minusBtn.dataset.id = String(product.id);
                minusBtn.textContent = '-';
                minusBtn.addEventListener('click', () => handleQtyChange(product.id, qty - 1));

                const qtySpan = document.createElement('span');
                qtySpan.className = 'w-6 text-center font-semibold';
                qtySpan.textContent = String(qty);

                const plusBtn = document.createElement('button');
                plusBtn.type = 'button';
                plusBtn.className = 'pos-drawer-plus w-8 h-8 flex items-center justify-center bg-white border border-brand-border rounded';
                plusBtn.dataset.id = String(product.id);
                plusBtn.textContent = '+';
                plusBtn.addEventListener('click', () => handleQtyChange(product.id, qty + 1));

                actionsDiv.appendChild(minusBtn);
                actionsDiv.appendChild(qtySpan);
                actionsDiv.appendChild(plusBtn);

                row.appendChild(infoDiv);
                row.appendChild(actionsDiv);
                basketList.appendChild(row);
            }
        }

        if (tapToPayBtn) {
            tapToPayBtn.querySelector('.pos-btn-amount').textContent = `CHF ${totals.totalChf}`;
        }
        if (twintBtn) {
            twintBtn.querySelector('.pos-btn-amount').textContent = `CHF ${totals.totalChf}`;
        }
    }

    function renderAll() {
        renderFilterState();
        renderProducts();
        renderBasketAndTotals();
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    function showCompletedScreen(saleData) {
        stopPolling();
        if (saleData.updated_stocks) {
            for (const [idStr, newStock] of Object.entries(saleData.updated_stocks)) {
                const prod = products.find(p => p.id === parseInt(idStr, 10));
                if (prod) prod.stock = newStock;
            }
        }
        if (waitingView) waitingView.classList.add('hidden');
        if (completedView) completedView.classList.remove('hidden');
        if (completedTotalEl) completedTotalEl.textContent = `CHF ${saleData.total_chf}`;

        if (saleData.receipt_sent) {
            if (lateReceiptWrap) lateReceiptWrap.classList.add('hidden');
            if (lateReceiptSentMsg) {
                lateReceiptSentMsg.classList.remove('hidden');
                lateReceiptSentMsg.textContent = `${i18nReceiptSent} (${saleData.customer_email})`;
            }
        } else {
            if (lateReceiptWrap) lateReceiptWrap.classList.remove('hidden');
            if (lateReceiptSentMsg) lateReceiptSentMsg.classList.add('hidden');
            if (lateReceiptEmailInput) lateReceiptEmailInput.value = saleData.customer_email || '';
        }
    }

    async function checkSaleStatus() {
        if (!activeSaleId || !statusUrlTemplate) return;
        const url = statusUrlTemplate.replace('0', String(activeSaleId));
        try {
            const resp = await fetch(url);
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.status === 'completed') {
                showCompletedScreen(data);
            } else if (data.status === 'canceled') {
                stopPolling();
                if (paymentModal) paymentModal.classList.add('hidden');
            }
        } catch {
            // Ignore transient network errors while polling
        }
    }

    async function startCheckout(paymentMethod) {
        const totals = calculateTotals(products, basket, discountConfig);
        if (totals.itemCount === 0) return;

        const itemsPayload = Object.entries(basket).map(([idStr, qty]) => ({
            product_id: parseInt(idStr, 10),
            qty,
        }));

        const emailToSend = wantsReceipt && receiptEmailInput ? receiptEmailInput.value.trim() : '';

        try {
            const resp = await fetch(createSaleUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    items: itemsPayload,
                    discount_amount: totals.discountCents,
                    payment_method: paymentMethod,
                    customer_email: emailToSend,
                }),
            });
            const data = await resp.json();
            if (!resp.ok) {
                showToast(data.error || 'Checkout error', 'error');
                return;
            }

            activeSaleId = data.sale_id;
            if (paymentModal) paymentModal.classList.remove('hidden');
            if (waitingView) waitingView.classList.remove('hidden');
            if (completedView) completedView.classList.add('hidden');
            if (waitingAmountEl) waitingAmountEl.textContent = `CHF ${data.total_chf}`;

            if (paymentMethod === 'tap_to_pay') {
                if (tapInstructionsEl) tapInstructionsEl.classList.remove('hidden');
                if (twintQrContainer) twintQrContainer.classList.add('hidden');
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(data.total_chf).then(() => {
                        showToast(`${i18nCopied}: CHF ${data.total_chf}`, 'info');
                    }).catch(() => {});
                }
            } else if (paymentMethod === 'twint') {
                if (tapInstructionsEl) tapInstructionsEl.classList.add('hidden');
                if (twintQrContainer) twintQrContainer.classList.remove('hidden');
                if (twintSvgHolder && data.twint_redirect_url) {
                    const svg = await renderQrSvg(data.twint_redirect_url);
                    const parsedDoc = new DOMParser().parseFromString(svg, 'image/svg+xml');
                    const svgEl = parsedDoc.querySelector('svg');
                    if (svgEl) {
                        twintSvgHolder.replaceChildren(svgEl);
                    }
                }
                if (twintExternalLink && data.twint_redirect_url) {
                    twintExternalLink.href = data.twint_redirect_url;
                }
            }

            stopPolling();
            pollInterval = setInterval(checkSaleStatus, 2000);
        } catch {
            showToast('Network error starting checkout', 'error');
        }
    }

    // Event bindings
    if (searchInput) {
        const unlockSearch = () => {
            searchInput.removeAttribute('readonly');
            searchInput.removeAttribute('tabindex');
        };
        searchInput.addEventListener('pointerdown', unlockSearch);
        searchInput.addEventListener('touchstart', unlockSearch, { passive: true });
        searchInput.addEventListener('mousedown', unlockSearch);
        searchInput.addEventListener('blur', () => {
            searchInput.setAttribute('readonly', '');
            searchInput.setAttribute('tabindex', '-1');
        });
        searchInput.addEventListener('input', (e) => {
            filters.query = e.target.value;
            syncUrl();
            renderProducts();
        });
    }

    if (inStockToggle) {
        inStockToggle.addEventListener('click', () => {
            blurActiveInput();
            filters.inStockOnly = !filters.inStockOnly;
            syncUrl();
            renderAll();
        });
    }

    document.querySelectorAll('[data-pos-brand]').forEach(btn => {
        btn.addEventListener('click', () => {
            blurActiveInput();
            const slug = btn.dataset.posBrand;
            filters.brand = filters.brand === slug ? '' : slug;
            syncUrl();
            renderAll();
        });
    });

    document.querySelectorAll('[data-pos-type]').forEach(btn => {
        btn.addEventListener('click', () => {
            blurActiveInput();
            const slug = btn.dataset.posType;
            filters.type = filters.type === slug ? '' : slug;
            syncUrl();
            renderAll();
        });
    });

    const openDrawerBtn = document.getElementById('pos-open-drawer-btn');
    if (openDrawerBtn) {
        openDrawerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            setDrawerOpen(true);
        });
    }
    const closeDrawerBtn = document.getElementById('pos-close-drawer-btn');
    if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            setDrawerOpen(false);
        });
    }
    if (checkoutOverlay) {
        checkoutOverlay.addEventListener('click', () => setDrawerOpen(false));
    }

    const clearBasketBtn = document.getElementById('pos-clear-basket-btn');
    if (clearBasketBtn) {
        clearBasketBtn.addEventListener('click', () => {
            blurActiveInput();
            basket = {};
            discountConfig = { mode: 'none', value: 0 };
            if (customDiscountInput) customDiscountInput.value = '';
            if (customTotalInput) customTotalInput.value = '';
            if (customDiscountWrap) customDiscountWrap.classList.add('hidden');
            setDrawerOpen(false);
            renderAll();
        });
    }

    document.querySelectorAll('[data-pos-discount-pct]').forEach(btn => {
        btn.addEventListener('click', () => {
            blurActiveInput();
            const pct = Number(btn.dataset.posDiscountPct);
            if (pct === 0 || (discountConfig.mode === 'percent' && Number(discountConfig.value) === pct)) {
                discountConfig = { mode: 'none', value: 0 };
            } else {
                discountConfig = { mode: 'percent', value: pct };
            }
            if (customDiscountInput) customDiscountInput.value = '';
            if (customTotalInput) customTotalInput.value = '';
            if (customDiscountWrap) customDiscountWrap.classList.add('hidden');
            renderBasketAndTotals();
        });
    });

    if (customDiscountBtn && customDiscountWrap) {
        customDiscountBtn.addEventListener('click', () => {
            blurActiveInput();
            const willShow = customDiscountWrap.classList.contains('hidden');
            customDiscountWrap.classList.toggle('hidden', !willShow);
            if (!willShow) {
                discountConfig = { mode: 'none', value: 0 };
                if (customDiscountInput) customDiscountInput.value = '';
                if (customTotalInput) customTotalInput.value = '';
            }
            renderBasketAndTotals();
        });
    }

    if (customDiscountInput) {
        customDiscountInput.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            if (customTotalInput) customTotalInput.value = '';
            if (!isNaN(val) && val > 0) {
                discountConfig = { mode: 'custom_discount', value: val };
            } else {
                discountConfig = { mode: 'none', value: 0 };
            }
            renderBasketAndTotals();
        });
    }

    if (customTotalInput) {
        customTotalInput.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            if (customDiscountInput) customDiscountInput.value = '';
            if (!isNaN(val) && val > 0) {
                discountConfig = { mode: 'custom_total', value: val };
            } else {
                discountConfig = { mode: 'none', value: 0 };
            }
            renderBasketAndTotals();
        });
    }

    if (receiptNoBtn && receiptYesBtn && receiptEmailWrap) {
        receiptNoBtn.addEventListener('click', () => {
            blurActiveInput();
            wantsReceipt = false;
            receiptNoBtn.classList.add('active');
            receiptYesBtn.classList.remove('active');
            receiptEmailWrap.classList.add('hidden');
        });
        receiptYesBtn.addEventListener('click', () => {
            wantsReceipt = true;
            receiptYesBtn.classList.add('active');
            receiptNoBtn.classList.remove('active');
            receiptEmailWrap.classList.remove('hidden');
            if (receiptEmailInput) receiptEmailInput.focus();
        });
    }

    if (receiptEmailInput) {
        receiptEmailInput.addEventListener('input', (e) => {
            customerEmail = e.target.value;
        });
    }

    if (tapToPayBtn) {
        tapToPayBtn.addEventListener('click', () => startCheckout('tap_to_pay'));
    }
    if (twintBtn) {
        twintBtn.addEventListener('click', () => startCheckout('twint'));
    }

    if (copyAmountBtn) {
        copyAmountBtn.addEventListener('click', () => {
            const amountText = (waitingAmountEl ? waitingAmountEl.textContent : '').replace('CHF ', '').trim();
            if (amountText && navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(amountText).then(() => {
                    showToast(`${i18nCopied}: CHF ${amountText}`, 'info');
                }).catch(() => {});
            }
        });
    }

    if (cancelSaleBtn) {
        cancelSaleBtn.addEventListener('click', async () => {
            stopPolling();
            if (activeSaleId && statusUrlTemplate) {
                const url = statusUrlTemplate.replace('0', String(activeSaleId));
                try {
                    await fetch(url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken,
                        },
                        body: JSON.stringify({ action: 'cancel' }),
                    });
                } catch {
                    // Ignore
                }
            }
            activeSaleId = null;
            if (paymentModal) paymentModal.classList.add('hidden');
        });
    }

    if (lateReceiptSendBtn && lateReceiptEmailInput) {
        lateReceiptSendBtn.addEventListener('click', async () => {
            const email = lateReceiptEmailInput.value.trim();
            if (!email || !activeSaleId || !statusUrlTemplate) return;
            const url = statusUrlTemplate.replace('0', String(activeSaleId));
            try {
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify({
                        action: 'send_receipt',
                        customer_email: email,
                    }),
                });
                const data = await resp.json();
                if (!resp.ok) {
                    showToast(data.error || 'Error sending receipt', 'error');
                    return;
                }
                showCompletedScreen(data);
                showToast(i18nReceiptSent, 'info');
            } catch {
                showToast('Network error sending receipt', 'error');
            }
        });
    }

    if (newSaleBtn) {
        newSaleBtn.addEventListener('click', () => {
            blurActiveInput();
            basket = {};
            discountConfig = { mode: 'none', value: 0 };
            wantsReceipt = false;
            customerEmail = '';
            activeSaleId = null;
            if (customDiscountInput) customDiscountInput.value = '';
            if (customTotalInput) customTotalInput.value = '';
            if (customDiscountWrap) customDiscountWrap.classList.add('hidden');
            if (receiptEmailInput) receiptEmailInput.value = '';
            if (receiptNoBtn) receiptNoBtn.classList.add('active');
            if (receiptYesBtn) receiptYesBtn.classList.remove('active');
            if (receiptEmailWrap) receiptEmailWrap.classList.add('hidden');
            if (paymentModal) paymentModal.classList.add('hidden');
            setDrawerOpen(false);
            renderAll();
        });
    }

    renderAll();
}

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPosApp);
    } else {
        initPosApp();
    }
}
