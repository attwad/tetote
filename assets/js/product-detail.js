import Splide from '@splidejs/splide';
import PhotoSwipeLightbox from 'photoswipe/lightbox';

export function initProductGallery() {
    // Initialize Splide
    const mainCarousel = document.getElementById('main-carousel');
    if (!mainCarousel) return;

    const main = new Splide('#main-carousel', {
        type: 'fade',
        rewind: true,
        pagination: false,
        arrows: false,
        lazyLoad: 'nearby',
    });

    const thumbnails = new Splide('#thumbnail-carousel', {
        perPage: 5,
        gap: '1rem',
        isNavigation: true,
        pagination: true,
        arrows: false,
        focus: 'center',
        breakpoints: {
            768: {
                perPage: 4,
            },
            480: {
                perPage: 3,
            },
        },
    });

    main.sync(thumbnails);
    main.mount();
    thumbnails.mount();

    // Initialize PhotoSwipe
    const lightbox = new PhotoSwipeLightbox({
        gallery: '#gallery',
        children: 'a',
        pswpModule: () => import('photoswipe'),
        imageClickAction: 'toggle-controls',
        tapAction: 'toggle-controls',
        zoomAllowed: true,
    });

    // Best Practice: Inject dimensions from already loaded images to prevent stretching
    const galleryAnchors = document.querySelectorAll('#gallery a');
    galleryAnchors.forEach(anchor => {
        const img = anchor.querySelector('img');
        const updateDims = () => {
            if (img.naturalWidth) {
                anchor.setAttribute('data-pswp-width', img.naturalWidth);
                anchor.setAttribute('data-pswp-height', img.naturalHeight);
            }
        };

        if (img.complete) {
            updateDims();
        } else {
            img.onload = updateDims;
        }
    });

    lightbox.init();
}
