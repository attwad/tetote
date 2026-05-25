import Splide from '@splidejs/splide';

document.addEventListener('DOMContentLoaded', () => {
    const homeCarousel = document.getElementById('home-carousel');
    if (homeCarousel) {
        new Splide('#home-carousel', {
            type: 'loop',
            autoplay: true,
            interval: 5000,
            pauseOnHover: false,
            arrows: true,
            pagination: true,
        }).mount();
    }
});
