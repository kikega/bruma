/**
 * Navbar flotante: estado de scroll, enlace activo por sección y menú móvil.
 */
export function initNavbar() {
  const header = document.getElementById('site-nav');
  if (!header) return;

  const toggleBtn = header.querySelector('[data-menu-toggle]');
  const toggleLabel = header.querySelector('[data-menu-toggle-label]');
  const iconOpen = header.querySelector('[data-icon-open]');
  const iconClose = header.querySelector('[data-icon-close]');
  const mobileMenu = document.getElementById('mobile-menu');
  const navLinks = [...header.querySelectorAll('[data-nav-link]')];

  // Estado compacto al hacer scroll
  const updateScrolled = () => {
    header.dataset.scrolled = window.scrollY > 24 ? 'true' : 'false';
  };
  updateScrolled();
  window.addEventListener('scroll', updateScrolled, { passive: true });

  // Menú móvil
  const setMenuOpen = (open) => {
    if (!toggleBtn || !mobileMenu) return;
    toggleBtn.setAttribute('aria-expanded', String(open));
    if (toggleLabel) toggleLabel.textContent = open ? 'Cerrar menú' : 'Abrir menú';
    mobileMenu.hidden = !open;
    if (iconOpen) iconOpen.hidden = open;
    if (iconClose) iconClose.hidden = !open;
  };

  toggleBtn?.addEventListener('click', () => {
    const isOpen = toggleBtn.getAttribute('aria-expanded') === 'true';
    setMenuOpen(!isOpen);
  });

  mobileMenu?.querySelectorAll('[data-mobile-link]').forEach((link) => {
    link.addEventListener('click', () => setMenuOpen(false));
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggleBtn?.getAttribute('aria-expanded') === 'true') {
      setMenuOpen(false);
      toggleBtn.focus();
    }
  });

  // Resaltado de sección activa con IntersectionObserver
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute('href')))
    .filter(Boolean);

  if ('IntersectionObserver' in window && sections.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const id = `#${entry.target.id}`;
          for (const link of navLinks) {
            if (link.getAttribute('href') === id) {
              link.setAttribute('aria-current', 'true');
            } else {
              link.removeAttribute('aria-current');
            }
          }
        }
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: 0 },
    );
    sections.forEach((section) => observer.observe(section));
  }
}
