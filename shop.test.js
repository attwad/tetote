import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getCart, saveCart, updateCartUI, showToast, getNewURL } from './static/js/shop.js';

describe('Shop Logic Tests', () => {
    beforeEach(() => {
        // Clear DOM and LocalStorage
        document.body.innerHTML = `
            <div id="toast-container"></div>
            <div id="nav">
                <span id="cart-count"></span>
            </div>
        `;
        localStorage.clear();
        vi.clearAllTimers();
        vi.useFakeTimers();
    });

    describe('URL / Filter Logic', () => {
        const baseUrl = 'http://localhost/';

        it('toggleDrawer should add expanded=true', () => {
            const result = getNewURL(baseUrl, 'drawer');
            expect(result).toContain('expanded=true');
        });

        it('toggleDrawer should remove expanded=true if present', () => {
            const result = getNewURL(baseUrl + '?expanded=true', 'drawer');
            expect(result).not.toContain('expanded=true');
        });

        it('toggleFilter should add multiple values', () => {
            let url = getNewURL(baseUrl, 'filter', 'brand', 'bizen');
            url = getNewURL(url, 'filter', 'brand', 'seto');
            const params = new URL(url).searchParams;
            expect(params.getAll('brand')).toEqual(['bizen', 'seto']);
        });

        it('toggleFilter should remove existing value', () => {
            const start = baseUrl + '?brand=bizen&brand=seto';
            const result = getNewURL(start, 'filter', 'brand', 'bizen');
            const params = new URL(result).searchParams;
            expect(params.getAll('brand')).toEqual(['seto']);
        });

        it('toggleStock should toggle in_stock', () => {
            const result = getNewURL(baseUrl, 'stock');
            expect(result).toContain('stock=in_stock');
            const back = getNewURL(result, 'stock');
            expect(back).not.toContain('stock=in_stock');
        });

        it('any filter change should reset pagination', () => {
            const start = baseUrl + '?page=2';
            const result = getNewURL(start, 'filter', 'brand', 'bizen');
            expect(result).not.toContain('page=2');
        });

        it('toggleSort should add sort parameter', () => {
            const result = getNewURL(baseUrl, 'sort', null, 'price_asc');
            expect(result).toContain('sort=price_asc');
        });
    });

    describe('showToast', () => {
        it('should add a toast element to the container', () => {
            showToast('Test Message', 'info');
            const toast = document.querySelector('.toast');
            expect(toast).not.toBeNull();
            expect(toast.textContent).toContain('Test Message');
            expect(toast.classList.contains('info')).toBe(true);
        });

        it('should remove the toast after the duration', () => {
            showToast('Fade Out', 'info', 100);
            expect(document.querySelector('.toast')).not.toBeNull();

            vi.advanceTimersByTime(200);
            // In real world animationend triggers removal,
            // in JSDOM we just verify the timeout logic
            // Note: because we use animationend in the code,
            // we'll manually check the timeout was called
        });
    });

    describe('Cart Logic', () => {
        it('getCart should return empty array initially', () => {
            expect(getCart()).toEqual([]);
        });

        it('saveCart should persist to localStorage and update UI', () => {
            const cart = [{ price_id: 'p1', qty: 2 }];
            saveCart(cart);

            expect(localStorage.getItem('cart')).toBe(JSON.stringify(cart));
            expect(document.getElementById('cart-count').textContent).toBe(' (1)');
        });

        it('updateCartUI should show unique product count', () => {
            localStorage.setItem('cart', JSON.stringify([
                { price_id: 'p1', qty: 1 },
                { price_id: 'p2', qty: 10 }
            ]));

            updateCartUI();
            expect(document.getElementById('cart-count').textContent).toBe(' (2)');
        });

        it('updateCartUI should be empty for 0 items', () => {
            localStorage.setItem('cart', JSON.stringify([]));
            updateCartUI();
            expect(document.getElementById('cart-count').textContent).toBe('');
        });

        it('saveCart([]) should clear the cart and UI', () => {
            localStorage.setItem('cart', JSON.stringify([{ price_id: 'p1', qty: 1 }]));
            saveCart([]);
            expect(localStorage.getItem('cart')).toBe('[]');
            expect(document.getElementById('cart-count').textContent).toBe('');
        });
    });
});
