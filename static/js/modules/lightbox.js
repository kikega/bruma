/**
 * Galería con lightbox modal nativo (<dialog closedby="any"> + fallback).
 */
export function initGalleryLightbox() {
  const dialog = document.getElementById('gallery-lightbox');
  const triggers = [...document.querySelectorAll('[data-gallery-open]')];
  if (!dialog || !triggers.length) return;

  const imgEl = dialog.querySelector('[data-lightbox-img]');
  const titleEl = dialog.querySelector('[data-lightbox-title]');
  const captionEl = dialog.querySelector('[data-lightbox-caption]');
  const counterEl = dialog.querySelector('[data-lightbox-counter]');
  const closeBtn = dialog.querySelector('[data-lightbox-close]');
  const prevBtn = dialog.querySelector('[data-lightbox-prev]');
  const nextBtn = dialog.querySelector('[data-lightbox-next]');

  let currentIndex = 0;
  let lastTrigger = null;

  const renderSlide = (index) => {
    currentIndex = (index + triggers.length) % triggers.length;
    const item = triggers[currentIndex];
    if (!item || !imgEl) return;

    imgEl.classList.remove('is-changing');
    imgEl.src = item.dataset.src || '';
    imgEl.alt = item.dataset.alt || item.dataset.title || '';
    void imgEl.offsetWidth;
    imgEl.classList.add('is-changing');

    if (titleEl) titleEl.textContent = item.dataset.title || '';
    if (captionEl) {
      captionEl.textContent = item.dataset.caption || '';
      captionEl.hidden = !item.dataset.caption;
    }
    if (counterEl) counterEl.textContent = `${currentIndex + 1} / ${triggers.length}`;
  };

  triggers.forEach((btn, idx) => {
    btn.addEventListener('click', () => {
      lastTrigger = btn;
      renderSlide(idx);
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.setAttribute('open', '');
      }
    });
  });

  prevBtn?.addEventListener('click', () => renderSlide(currentIndex - 1));
  nextBtn?.addEventListener('click', () => renderSlide(currentIndex + 1));
  closeBtn?.addEventListener('click', () => dialog.close());

  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      renderSlide(currentIndex - 1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      renderSlide(currentIndex + 1);
    }
  });

  dialog.addEventListener('close', () => {
    lastTrigger?.focus();
  });

  // Fallback para navegadores sin soporte nativo de <dialog closedby="any">
  if (typeof HTMLDialogElement !== 'undefined' && !('closedBy' in HTMLDialogElement.prototype)) {
    dialog.addEventListener('click', (event) => {
      // Si se pulsa directamente en el fondo de la capa o en el propio <dialog>, cerramos
      const clickedInteractive = event.target.closest(
        'figure, button, [data-lightbox-prev], [data-lightbox-next], [data-lightbox-close]',
      );
      if (!clickedInteractive) {
        dialog.close();
      }
    });
  }
}
