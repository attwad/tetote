import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
    formatChf,
    calculateTotals,
    filterProducts,
    getPosUrl,
    readPosUrlState,
    updateBasketItem,
    renderQrSvg,
    initPosApp,
} from './pos.js';

const mockProducts = [
    {
        id: 1,
        name: 'Bizen Mug',
        price_cents: 4500,
        price_chf: 45.0,
        stock: 3,
        image: '/media/mug.jpg',
        brand_name: 'Bizen Studio',
        brand_slug: 'bizen',
        type_name: 'Mug',
        type_slug: 'mug',
        glaze_name: 'Natural Ash',
    },
    {
        id: 2,
        name: 'Seto Matcha Bowl',
        price_cents: 8000,
        price_chf: 80.0,
        stock: 1,
        image: '',
        brand_name: 'Seto Kiln',
        brand_slug: 'seto',
        type_name: 'Bowl',
        type_slug: 'bowl',
        glaze_name: 'Oribe',
    },
    {
        id: 3,
        name: 'Sold Out Plate',
        price_cents: 3000,
        price_chf: 30.0,
        stock: 0,
        image: '',
        brand_name: 'Bizen Studio',
        brand_slug: 'bizen',
        type_name: 'Plate',
        type_slug: 'plate',
        glaze_name: 'Shino',
    },
];

describe('POS Logic & UI Tests', () => {
    it('formatChf formats cents to 2 decimals', () => {
        expect(formatChf(4500)).toBe('45.00');
        expect(formatChf(50)).toBe('0.50');
    });

    describe('calculateTotals', () => {
        it('calculates subtotal and total with no discount', () => {
            const totals = calculateTotals(mockProducts, { 1: 2, 2: 1 });
            expect(totals.itemCount).toBe(3);
            expect(totals.subtotalCents).toBe(17000);
            expect(totals.discountCents).toBe(0);
            expect(totals.totalCents).toBe(17000);
            expect(totals.totalChf).toBe('170.00');
        });

        it('applies percentage discount', () => {
            const totals = calculateTotals(mockProducts, { 1: 2 }, { mode: 'percent', value: 10 });
            expect(totals.subtotalCents).toBe(9000);
            expect(totals.discountCents).toBe(900);
            expect(totals.totalCents).toBe(8100);
            expect(totals.totalChf).toBe('81.00');
        });

        it('applies custom CHF discount and clamps to minimum 0.50 CHF total', () => {
            const totals = calculateTotals(mockProducts, { 1: 1 }, { mode: 'custom_discount', value: 5 });
            expect(totals.subtotalCents).toBe(4500);
            expect(totals.discountCents).toBe(500);
            expect(totals.totalCents).toBe(4000);

            const clamped = calculateTotals(mockProducts, { 1: 1 }, { mode: 'custom_discount', value: 100 });
            expect(clamped.discountCents).toBe(4450);
            expect(clamped.totalCents).toBe(50);
        });

        it('applies custom final CHF total', () => {
            const totals = calculateTotals(mockProducts, { 1: 2 }, { mode: 'custom_total', value: 75 });
            expect(totals.subtotalCents).toBe(9000);
            expect(totals.discountCents).toBe(1500);
            expect(totals.totalCents).toBe(7500);
            expect(totals.totalChf).toBe('75.00');
        });
    });

    describe('filterProducts', () => {
        it('filters in-stock by default and supports search/brand/type', () => {
            expect(filterProducts(mockProducts, {}).map(p => p.id)).toEqual([1, 2]);
            expect(filterProducts(mockProducts, { inStockOnly: false }).map(p => p.id)).toEqual([1, 2, 3]);
            expect(filterProducts(mockProducts, { brand: 'bizen' }).map(p => p.id)).toEqual([1]);
            expect(filterProducts(mockProducts, { type: 'bowl' }).map(p => p.id)).toEqual([2]);
            expect(filterProducts(mockProducts, { query: 'oribe' }).map(p => p.id)).toEqual([2]);
        });
    });

    describe('URL state persistence', () => {
        it('serializes and parses POS URL state', () => {
            const url = getPosUrl(
                'http://localhost/pos/',
                { query: 'mug', brand: 'bizen', type: 'mug', inStockOnly: false },
                true
            );
            expect(url).toContain('q=mug');
            expect(url).toContain('brand=bizen');
            expect(url).toContain('type=mug');
            expect(url).toContain('in_stock=false');
            expect(url).toContain('expanded=true');

            const parsed = readPosUrlState(url);
            expect(parsed).toEqual({
                query: 'mug',
                brand: 'bizen',
                type: 'mug',
                inStockOnly: false,
                isExpanded: true,
            });
        });

        it('removes default parameters cleanly', () => {
            const url = getPosUrl(
                'http://localhost/pos/?q=mug&brand=bizen&type=mug&in_stock=false&expanded=true',
                { query: '', brand: '', type: '', inStockOnly: true },
                false
            );
            expect(url).toBe('http://localhost/pos/');
        });
    });

    describe('updateBasketItem', () => {
        it('adds, removes, and enforces max stock', () => {
            let res = updateBasketItem(mockProducts, {}, 1, 2);
            expect(res.basket).toEqual({ 1: 2 });
            expect(res.limitReached).toBe(false);

            res = updateBasketItem(mockProducts, res.basket, 1, 5);
            expect(res.basket).toEqual({ 1: 3 });
            expect(res.limitReached).toBe(true);
            expect(res.maxStock).toBe(3);

            res = updateBasketItem(mockProducts, res.basket, 1, 0);
            expect(res.basket).toEqual({});

            const unknown = updateBasketItem(mockProducts, {}, 999, 1);
            expect(unknown.basket).toEqual({});
        });
    });

    describe('renderQrSvg', () => {
        it('returns SVG string for valid URL and empty string for empty input', async () => {
            expect(await renderQrSvg('')).toBe('');
            const svg = await renderQrSvg('https://hooks.stripe.com/redirect/test');
            expect(svg).toContain('<svg');
        });
    });

    describe('DOM Interactive Flow (initPosApp)', () => {
        beforeEach(() => {
            window.history.replaceState(null, '', '/pos/');
            document.body.innerHTML = `
                <div id="pos-app"
                     data-create-sale-url="/pos/api/sales/"
                     data-status-url-template="/pos/api/sales/0/status/"
                     data-csrf-token="test-csrf"
                     data-i18n-stock-limit="Only X left"
                     data-i18n-copied="Copied"
                     data-i18n-receipt-sent="Receipt sent">
                    <button id="pos-in-stock-toggle" class="chip active"></button>
                    <button id="pos-clear-basket-btn"></button>
                    <input id="pos-search-input" type="search" readonly>
                    <button data-pos-brand="bizen"></button>
                    <button data-pos-type="mug"></button>
                    <div id="pos-product-grid"></div>
                    <div id="pos-empty-state" class="hidden"></div>
                    <div id="pos-bottom-bar" class="translate-y-full">
                        <span id="pos-bottom-count">0</span>
                        <span id="pos-bottom-total">CHF 0.00</span>
                        <button id="pos-open-drawer-btn"></button>
                    </div>
                    <div id="pos-checkout-overlay" class="hidden"></div>
                    <section id="pos-checkout-drawer" class="translate-y-full hidden">
                        <button id="pos-close-drawer-btn"></button>
                        <div id="pos-basket-items"></div>
                        <button data-pos-discount-pct="0" class="active"></button>
                        <button data-pos-discount-pct="10"></button>
                        <button id="pos-discount-custom-btn"></button>
                        <div id="pos-custom-discount-wrap" class="hidden">
                            <input id="pos-custom-discount-input" type="number">
                            <input id="pos-custom-total-input" type="number">
                        </div>
                        <button id="pos-receipt-no" class="active"></button>
                        <button id="pos-receipt-yes"></button>
                        <div id="pos-receipt-email-wrap" class="hidden">
                            <input id="pos-receipt-email-input" type="email">
                        </div>
                        <span id="pos-subtotal-display"></span>
                        <div id="pos-discount-row" class="hidden"><span id="pos-discount-display"></span></div>
                        <span id="pos-total-display"></span>
                        <button id="pos-btn-tap-to-pay"><span class="pos-btn-amount"></span></button>
                        <button id="pos-btn-twint"><span class="pos-btn-amount"></span></button>
                    </section>
                    <div id="pos-payment-modal" class="hidden">
                        <div id="pos-waiting-view">
                            <span id="pos-waiting-amount"></span>
                            <div id="pos-tap-instructions">
                                <button id="pos-copy-amount-btn"></button>
                            </div>
                            <div id="pos-twint-qr-container" class="hidden">
                                <div id="pos-twint-svg"></div>
                                <a id="pos-twint-external-link"></a>
                            </div>
                            <button id="pos-cancel-sale-btn"></button>
                        </div>
                        <div id="pos-completed-view" class="hidden">
                            <span id="pos-completed-total"></span>
                            <p id="pos-late-receipt-sent" class="hidden"></p>
                            <div id="pos-late-receipt-wrap">
                                <input id="pos-late-receipt-email" type="email">
                                <button id="pos-late-receipt-btn"></button>
                            </div>
                            <button id="pos-new-sale-btn"></button>
                        </div>
                    </div>
                </div>
                <div id="toast-container"></div>
                <script id="pos-products-data" type="application/json">${JSON.stringify(mockProducts)}</script>
            `;
            global.fetch = vi.fn();
            Object.assign(navigator, {
                clipboard: {
                    writeText: vi.fn().mockResolvedValue(undefined),
                },
            });
        });

        it('renders cards, handles selection, discounts, and Tap to Pay / TWINT checkout', async () => {
            initPosApp();

            const cards = document.querySelectorAll('.pos-product-card');
            expect(cards.length).toBe(2);

            // Click first card to add 1 Bizen Mug
            cards[0].click();
            expect(document.getElementById('pos-bottom-count').textContent).toBe('1');
            expect(document.getElementById('pos-bottom-total').textContent).toBe('CHF 45.00');

            // Click + button inside card
            document.querySelector('.pos-step-plus').click();
            expect(document.getElementById('pos-bottom-count').textContent).toBe('2');
            expect(document.getElementById('pos-bottom-total').textContent).toBe('CHF 90.00');

            // Open drawer
            document.getElementById('pos-open-drawer-btn').click();
            expect(window.location.href).toContain('expanded=true');

            // Apply 10% discount
            document.querySelector('[data-pos-discount-pct="10"]').click();
            expect(document.getElementById('pos-total-display').textContent).toBe('CHF 81.00');

            // Toggle custom discount section and apply custom total
            expect(document.getElementById('pos-custom-discount-wrap').classList.contains('hidden')).toBe(true);
            document.getElementById('pos-discount-custom-btn').click();
            expect(document.getElementById('pos-custom-discount-wrap').classList.contains('hidden')).toBe(false);
            const customTotalInput = document.getElementById('pos-custom-total-input');
            customTotalInput.value = '80';
            customTotalInput.dispatchEvent(new Event('input'));
            expect(document.getElementById('pos-total-display').textContent).toBe('CHF 80.00');

            // Enable receipt and set email
            document.getElementById('pos-receipt-yes').click();
            const emailInput = document.getElementById('pos-receipt-email-input');
            emailInput.value = 'buyer@example.com';
            emailInput.dispatchEvent(new Event('input'));

            // Trigger TWINT checkout
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    sale_id: 42,
                    status: 'pending',
                    payment_method: 'twint',
                    total_chf: '80.00',
                    twint_redirect_url: 'https://hooks.stripe.com/redirect/twint_test',
                    customer_email: 'buyer@example.com',
                }),
            });

            document.getElementById('pos-btn-twint').click();
            await new Promise(r => setTimeout(r, 50));

            expect(global.fetch).toHaveBeenCalledWith(
                '/pos/api/sales/',
                expect.objectContaining({ method: 'POST' })
            );
            expect(document.getElementById('pos-payment-modal').classList.contains('hidden')).toBe(false);
            expect(document.getElementById('pos-twint-svg').innerHTML).toContain('<svg');

            // Cancel sale
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ status: 'canceled' }),
            });
            document.getElementById('pos-cancel-sale-btn').click();
            await new Promise(r => setTimeout(r, 20));
            expect(document.getElementById('pos-payment-modal').classList.contains('hidden')).toBe(true);
        });

        it('handles Tap to Pay checkout, status polling completion, late receipt, and new sale reset', async () => {
            vi.useFakeTimers();
            initPosApp();

            document.querySelectorAll('.pos-product-card')[0].click();

            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    sale_id: 55,
                    status: 'pending',
                    payment_method: 'tap_to_pay',
                    total_chf: '45.00',
                    twint_redirect_url: '',
                    customer_email: '',
                }),
            });

            document.getElementById('pos-btn-tap-to-pay').click();
            await vi.advanceTimersByTimeAsync(50);

            expect(navigator.clipboard.writeText).toHaveBeenCalledWith('45.00');

            // Poll returns completed
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    sale_id: 55,
                    status: 'completed',
                    total_chf: '45.00',
                    customer_email: '',
                    receipt_sent: false,
                    updated_stocks: { 1: 2 },
                }),
            });

            await vi.advanceTimersByTimeAsync(2000);
            expect(document.getElementById('pos-completed-view').classList.contains('hidden')).toBe(false);

            // Send late receipt
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    sale_id: 55,
                    status: 'completed',
                    total_chf: '45.00',
                    customer_email: 'late@example.com',
                    receipt_sent: true,
                }),
            });
            const lateEmail = document.getElementById('pos-late-receipt-email');
            lateEmail.value = 'late@example.com';
            document.getElementById('pos-late-receipt-btn').click();
            await vi.advanceTimersByTimeAsync(50);

            expect(document.getElementById('pos-late-receipt-sent').textContent).toContain('late@example.com');

            // Start new sale
            document.getElementById('pos-new-sale-btn').click();
            expect(document.getElementById('pos-payment-modal').classList.contains('hidden')).toBe(true);
            expect(document.getElementById('pos-bottom-count').textContent).toBe('0');
            vi.useRealTimers();
        });

        it('prevents virtual keyboard popup by keeping inputs blurred and readonly on item, +, and checkout taps', () => {
            initPosApp();
            const searchInput = document.getElementById('pos-search-input');
            const drawer = document.getElementById('pos-checkout-drawer');

            expect(searchInput.hasAttribute('readonly')).toBe(true);
            expect(drawer.classList.contains('hidden')).toBe(true);

            // Unlock search on direct tap, then verify clicking item blurs and re-locks it
            searchInput.dispatchEvent(new Event('touchstart'));
            expect(searchInput.hasAttribute('readonly')).toBe(false);
            searchInput.focus();
            expect(document.activeElement).toBe(searchInput);

            // Tap product card -> blurs search input and sets readonly back
            document.querySelectorAll('.pos-product-card')[0].click();
            expect(document.activeElement).not.toBe(searchInput);
            expect(searchInput.hasAttribute('readonly')).toBe(true);

            // Tap + button -> no input focused
            document.querySelector('.pos-step-plus').click();
            expect(document.activeElement.tagName).not.toBe('INPUT');

            // Tap Checkout -> opens drawer without focusing any input
            document.getElementById('pos-open-drawer-btn').click();
            expect(drawer.classList.contains('hidden')).toBe(false);
            expect(document.activeElement.tagName).not.toBe('INPUT');
        });
    });
});
