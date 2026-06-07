import Splide from '@splidejs/splide';

document.addEventListener('DOMContentLoaded', () => {
    const homeCarousel = document.getElementById('home-carousel');
    if (homeCarousel) {
        new Splide('#home-carousel', {
            type: 'fade',
            rewind: true,
            autoplay: true,
            interval: 5000,
            pauseOnHover: true,
            pauseOnFocus: true,
            arrows: true,
            pagination: false,
            lazyLoad: 'nearby',
            height: '700px',
            breakpoints: {
                768: {
                    height: '400px',
                },
            },
        }).mount();
    }
});
