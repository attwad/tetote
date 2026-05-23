import {
    updateCartUI,
    initHeaderScroll,
    getCart,
    saveCart,
    showToast,
    toggleMobileMenu,
    toggleDrawer,
    toggleFilter,
    toggleStock,
    toggleSort
} from './shop.js';

// Expose to window for existing inline onclick handlers
window.getCart = getCart;
window.saveCart = saveCart;
window.updateCartUI = updateCartUI;
window.showToast = showToast;
window.toggleMobileMenu = toggleMobileMenu;
window.toggleDrawer = toggleDrawer;
window.toggleFilter = toggleFilter;
window.toggleStock = toggleStock;
window.toggleSort = toggleSort;

// Initialize global features
document.addEventListener('DOMContentLoaded', () => {
    updateCartUI();
    initHeaderScroll();
});

window.addEventListener('pageshow', (event) => {
    updateCartUI();
});
