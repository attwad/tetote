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
    });

    const thumbnails = document.querySelectorAll('.thumbnail');
    let currentThumbnail = thumbnails[0];

    main.on('mounted move', () => {
        const thumbnail = thumbnails[main.index];
        if (thumbnail) {
            if (currentThumbnail) currentThumbnail.classList.remove('is-active');
            thumbnail.classList.add('is-active');
            currentThumbnail = thumbnail;
        }
    });

    thumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener('click', () => {
            main.go(index);
        });
    });

    main.mount();

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
