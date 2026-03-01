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
        badge.style.display = 'inline';
    }
}
