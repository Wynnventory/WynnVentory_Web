function initCarousel() {
    const items = document.querySelectorAll('.carousel-item-3d');
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    let currentIndex = 0;

    if (!items.length || !prevBtn || !nextBtn) return;

    function updateCarousel() {
        items.forEach((item, index) => {
            item.classList.remove('active', 'prev', 'next');
            if (index === currentIndex) {
                item.classList.add('active');
            } else if (index === (currentIndex - 1 + items.length) % items.length) {
                item.classList.add('prev');
            } else if (index === (currentIndex + 1) % items.length) {
                item.classList.add('next');
            }
        });
    }

    prevBtn.addEventListener('click', () => {
        currentIndex = (currentIndex - 1 + items.length) % items.length;
        updateCarousel();
    });

    nextBtn.addEventListener('click', () => {
        currentIndex = (currentIndex + 1) % items.length;
        updateCarousel();
    });

    // Initialize carousel
    updateCarousel();
}

document.addEventListener('DOMContentLoaded', initCarousel);
