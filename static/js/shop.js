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
        document.body.classList.add('overflow-hidden');
    } else {
        // Close
        drawer.classList.add('-translate-x-full');
        overlay.classList.add('opacity-0');
        const transitionHandler = function() {
            overlay.classList.add('hidden');
            overlay.removeEventListener('transitionend', transitionHandler);
        };
        overlay.addEventListener('transitionend', transitionHandler);
        document.body.classList.remove('overflow-hidden');
    }
}

/**
 * Filter Logic
 */

export function getNewURL(currentUrlStr, type, name, value, shouldBeExpanded = null) {
    const url = new URL(currentUrlStr);
    const params = url.searchParams;

    if (type === 'drawer') {
        const currentlyExpanded = params.get('expanded') === 'true';
        if (currentlyExpanded) params.delete('expanded');
        else params.set('expanded', 'true');
    } else {
        // If shouldBeExpanded is provided, use it. Otherwise, keep current state.
        const currentlyExpanded = (shouldBeExpanded !== null)
            ? shouldBeExpanded
            : (params.get('expanded') === 'true');

        if (currentlyExpanded) {
            params.set('expanded', 'true');
        } else {
            params.delete('expanded');
        }

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
        // Update URL state without reload to keep it in sync
        const newUrl = getNewURL(window.location.href, 'drawer');
        window.history.replaceState(null, '', newUrl);

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
            document.body.classList.remove('overflow-hidden');
        } else {
            // Open
            drawer.classList.add('open');
            overlay.classList.remove('hidden');
            overlay.classList.add('show');
            setTimeout(() => {
                overlay.classList.remove('opacity-0');
            }, 10);
            document.body.classList.add('overflow-hidden');
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
            document.body.classList.add('overflow-hidden');
        }
    });
}

export function toggleFilter(event, name, value) {
    if (event) event.preventDefault();
    const drawer = document.getElementById('filter-drawer');
    const isExpanded = drawer && drawer.classList.contains('open');
    window.location.href = getNewURL(window.location.href, 'filter', name, value, isExpanded);
}

export function toggleStock(event) {
    if (event) event.preventDefault();
    const drawer = document.getElementById('filter-drawer');
    const isExpanded = drawer && drawer.classList.contains('open');
    window.location.href = getNewURL(window.location.href, 'stock', null, null, isExpanded);
}

export function toggleSort(value) {
    const drawer = document.getElementById('filter-drawer');
    const isExpanded = drawer && drawer.classList.contains('open');
    window.location.href = getNewURL(window.location.href, 'sort', null, value, isExpanded);
}

/**
 * Header Scroll Logic
 */
export function initHeaderScroll() {
    const header = document.querySelector('.site-header');
    if (!header) return;

    let lastScrollY = window.scrollY;
    let scrollUpAccumulator = 0;
    const threshold = 150; // Initial distance from top
    const hideThreshold = 300; // Total scroll before hiding starts
    const showThreshold = 150; // Amount to scroll up before showing again

    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;
        const delta = currentScrollY - lastScrollY;

        // Add border/shadow if scrolled even a little
        if (currentScrollY > 10) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        // Hide/Show logic
        if (currentScrollY > threshold) {
            if (delta > 0) {
                // Scrolling down
                scrollUpAccumulator = 0; // Reset accumulator when scrolling down
                if (currentScrollY > hideThreshold) {
                    header.classList.add('hidden-up');
                }
            } else {
                // Scrolling up
                scrollUpAccumulator += Math.abs(delta);
                if (scrollUpAccumulator > showThreshold) {
                    header.classList.remove('hidden-up');
                }
            }
        } else {
            // Near top - always show
            header.classList.remove('hidden-up');
            scrollUpAccumulator = 0;
        }

        lastScrollY = currentScrollY;
    }, { passive: true });
}
