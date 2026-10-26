import { initGalleryLightbox } from './modules/lightbox.js';
import { initMenuTabs } from './modules/menu-tabs.js';
import { initNavbar } from './modules/navbar.js';
import { initRevealAndParallax } from './modules/parallax.js';
import { initReservationForm } from './modules/reservation-form.js';

const boot = () => {
  initNavbar();
  initRevealAndParallax();
  initMenuTabs();
  initGalleryLightbox();
  initReservationForm();
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot, { once: true });
} else {
  boot();
}
