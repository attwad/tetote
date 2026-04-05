/**
 * Tetote E-commerce Logic
 */

export function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            toast.classList.add('animate-fade-out');
            toast.style.animationFillMode = 'forwards';
            toast.addEventListener('animationend', () => toast.remove());
        }, duration);
    }
    return toast;
}

export function getCart() {
    return JSON.parse(localStorage.getItem('cart') || '[]');
}

export function saveCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartUI();
}

export function updateCartUI() {
    const cart = getCart();
    const count = cart.length;
    const badge = document.getElementById('cart-count');
    if (badge) {
        badge.textContent = count > 0 ? ` (${count})` : "";
        badge.style.display = 'inline-block';
    }
    const mobileBadge = document.getElementById('cart-count-mobile');
    if (mobileBadge) {
        mobileBadge.textContent = count > 0 ? ` (${count})` : "";
    }
}

export function toggleMobileMenu() {
    const drawer = document.getElementById('mobile-menu-drawer');
    const overlay = document.getElementById('mobile-menu-overlay');

    if (!drawer || !overlay) return;

    if (drawer.classList.contains('-translate-x-full')) {
        // Open
        drawer.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
        setTimeout(() => {
            overlay.classList.remove('opacity-0');
        }, 10);
        document.body.style.overflow = 'hidden';
    } else {
        // Close
        drawer.classList.add('-translate-x-full');
        overlay.classList.add('opacity-0');
        const transitionHandler = function() {
            overlay.classList.add('hidden');
            overlay.removeEventListener('transitionend', transitionHandler);
        };
        overlay.addEventListener('transitionend', transitionHandler);
        document.body.style.overflow = '';
    }
}

/**
 * Filter Logic
 */

export function getNewURL(currentUrlStr, type, name, value) {
    const url = new URL(currentUrlStr);
    const params = url.searchParams;

    if (type === 'drawer') {
        const currentlyExpanded = params.get('expanded') === 'true';
        if (currentlyExpanded) params.delete('expanded');
        else params.set('expanded', 'true');
    } else {
        // For filters, stock, and sort: preserve the expanded state if it's already true
        // This keeps the drawer open on mobile after reload
        const currentlyExpanded = params.get('expanded') === 'true';

        if (type === 'filter') {
            const currentValues = params.getAll(name);
            if (currentValues.includes(value)) {
                const newValues = currentValues.filter(v => v !== value);
                params.delete(name);
                newValues.forEach(v => params.append(name, v));
            } else {
                params.append(name, value);
            }
        } else if (type === 'stock') {
            if (params.get('stock') === 'in_stock') params.delete('stock');
            else params.set('stock', 'in_stock');
        } else if (type === 'sort') {
            if (value) params.set('sort', value);
            else params.delete('sort');
        }

        if (currentlyExpanded) {
            params.set('expanded', 'true');
        }
    }

    // Always reset page on filter change
    if (type !== 'drawer') {
        params.delete('page');
    }

    return url.toString();
}

export function toggleDrawer() {
    const drawer = document.getElementById('filter-drawer');
    const overlay = document.getElementById('filter-overlay');
    const isMobile = window.innerWidth < 768;

    if (isMobile && drawer && overlay) {
        if (drawer.classList.contains('open')) {
            // Close
            drawer.classList.remove('open');
            overlay.classList.add('opacity-0');
            const transitionHandler = function() {
                overlay.classList.add('hidden');
                overlay.classList.remove('show');
                overlay.removeEventListener('transitionend', transitionHandler);
            };
            overlay.addEventListener('transitionend', transitionHandler);
            document.body.style.overflow = '';
        } else {
            // Open
            drawer.classList.add('open');
            overlay.classList.remove('hidden');
            overlay.classList.add('show');
            setTimeout(() => {
                overlay.classList.remove('opacity-0');
            }, 10);
            document.body.style.overflow = 'hidden';
        }
    } else {
        window.location.href = getNewURL(window.location.href, 'drawer');
    }
}

// Initial state cleanup for drawer logic
if (typeof window !== 'undefined') {
    window.addEventListener('load', () => {
        const drawer = document.getElementById('filter-drawer');
        const overlay = document.getElementById('filter-overlay');
        const isMobile = window.innerWidth < 768;
        if (isMobile && drawer && drawer.classList.contains('open')) {
            if (overlay) overlay.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    });
}

export function toggleFilter(event, name, value) {
    if (event) event.preventDefault();
    window.location.href = getNewURL(window.location.href, 'filter', name, value);
}

export function toggleStock(event) {
    if (event) event.preventDefault();
    window.location.href = getNewURL(window.location.href, 'stock');
}

export function toggleSort(value) {
    window.location.href = getNewURL(window.location.href, 'sort', null, value);
}
