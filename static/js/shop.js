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
            toast.style.animation = 'fadeOut 0.5s ease-out forwards';
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
    } else if (type === 'filter') {
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
    } else if (type === 'new') {
        if (params.get('new') === 'true') params.delete('new');
        else params.set('new', 'true');
    } else if (type === 'sort') {
        if (value) params.set('sort', value);
        else params.delete('sort');
    }

    // Always reset page on filter change
    if (type !== 'drawer') {
        params.delete('page');
    }

    return url.toString();
}

export function toggleDrawer() {
    window.location.href = getNewURL(window.location.href, 'drawer');
}

export function toggleFilter(event, name, value) {
    if (event) event.preventDefault();
    window.location.href = getNewURL(window.location.href, 'filter', name, value);
}

export function toggleStock(event) {
    if (event) event.preventDefault();
    window.location.href = getNewURL(window.location.href, 'stock');
}

export function toggleNew(event) {
    if (event) event.preventDefault();
    window.location.href = getNewURL(window.location.href, 'new');
}

export function toggleSort(value) {
    window.location.href = getNewURL(window.location.href, 'sort', null, value);
}
