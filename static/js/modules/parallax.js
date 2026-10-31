/**
 * Animaciones de aparición ([data-reveal]) y fallback ligero de parallax
 * para navegadores sin soporte completo de CSS Scroll-Driven Animations.
 */
export function initRevealAndParallax() {
  // 1. Aparición suave al entrar en el viewport
  const revealItems = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window && revealItems.length) {
    const revealObserver = new IntersectionObserver(
      (entries, obs) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
          }
        }
      },
      { rootMargin: '0px 0px -10% 0px', threshold: 0.08 },
    );
    revealItems.forEach((el) => revealObserver.observe(el));
  } else {
    revealItems.forEach((el) => el.classList.add('is-visible'));
  }

  // 2. Respetar preferencia de movimiento reducido
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // 3. Si el navegador soporta Scroll-Driven Animations nativas, el CSS se encarga a 60fps
  if (
    typeof CSS !== 'undefined' &&
    CSS.supports('(animation-timeline: view()) and (animation-range: entry)')
  ) {
    return;
  }

  // 4. Fallback con IntersectionObserver + requestAnimationFrame sólo para scopes visibles
  const scopes = [...document.querySelectorAll('[data-parallax-scope]')];
  if (!scopes.length) return;

  const activeScopes = new Set();
  let ticking = false;

  const parseNumber = (raw, fallback) => {
    if (!raw) return fallback;
    const num = parseFloat(raw);
    return Number.isFinite(num) ? num : fallback;
  };

  const updateParallax = () => {
    ticking = false;
    const vh = window.innerHeight || 1;
    for (const scope of activeScopes) {
      const rect = scope.getBoundingClientRect();
      const total = rect.height + vh;
      const coverProgress = Math.min(Math.max((vh - rect.top) / total, 0), 1);
      const exitProgress = Math.min(Math.max(-rect.top / (rect.height || 1), 0), 1);
      const layers = scope.querySelectorAll('[data-parallax]');
      for (const layer of layers) {
        const isExit = layer.dataset.parallaxRange === 'exit';
        const progress = isExit ? exitProgress : coverProgress;
        const style = getComputedStyle(layer);
        const from = parseNumber(style.getPropertyValue('--parallax-from'), 0);
        const to = parseNumber(style.getPropertyValue('--parallax-to'), 0);
        const current = from + (to - from) * progress;
        layer.style.transform = `translate3d(0, ${current}%, 0)`;

        const fadeFromRaw = style.getPropertyValue('--parallax-fade-from').trim();
        const fadeToRaw = style.getPropertyValue('--parallax-fade-to').trim();
        if (fadeFromRaw || fadeToRaw) {
          const fadeFrom = parseNumber(fadeFromRaw, 1);
          const fadeTo = parseNumber(fadeToRaw, 1);
          layer.style.opacity = String(fadeFrom + (fadeTo - fadeFrom) * progress);
        }
      }
    }
  };

  const onScroll = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateParallax);
    }
  };

  const scopeObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeScopes.add(entry.target);
        } else {
          activeScopes.delete(entry.target);
        }
      }
      if (activeScopes.size > 0) {
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
      } else {
        window.removeEventListener('scroll', onScroll);
      }
    },
    { threshold: 0 },
  );

  scopes.forEach((scope) => scopeObserver.observe(scope));
}
