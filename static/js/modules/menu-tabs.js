/**
 * Pestañas interactivas de La Carta (patrón WAI-ARIA Tabs con soporte de teclado).
 */
export function initMenuTabs() {
  const container = document.querySelector('[data-menu-tabs]');
  if (!container) return;

  const tabs = [...container.querySelectorAll('[role="tab"]')];
  const panels = [...container.querySelectorAll('[role="tabpanel"]')];
  if (!tabs.length) return;

  const activateTab = (nextTab, { focus = false } = {}) => {
    const targetId = nextTab.getAttribute('aria-controls');

    for (const tab of tabs) {
      const selected = tab === nextTab;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      if (selected && focus) tab.focus();
    }

    for (const panel of panels) {
      const active = panel.id === targetId;
      panel.hidden = !active;
      panel.classList.remove('is-entering');
      if (active) {
        // Reinicia la animación fade-in al cambiar de categoría
        void panel.offsetWidth;
        panel.classList.add('is-entering');
      }
    }
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab));

    tab.addEventListener('keydown', (event) => {
      let nextIndex = null;
      if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') nextIndex = 0;
      else if (event.key === 'End') nextIndex = tabs.length - 1;

      if (nextIndex !== null) {
        event.preventDefault();
        activateTab(tabs[nextIndex], { focus: true });
      }
    });
  });

  initCategoryModals(container);
  initDishFloatingPreview(container);
}

let supportsDisplayTransition;
function canTransitionDisplay() {
  if (supportsDisplayTransition !== undefined) return supportsDisplayTransition;
  if (!window.CSS?.supports?.('transition-behavior', 'allow-discrete') || !document.body) {
    return false;
  }
  const probe = document.createElement('div');
  probe.style.cssText = 'transition: display 1s allow-discrete !important; display: block;';
  document.body.appendChild(probe);
  getComputedStyle(probe).display;
  probe.style.display = 'none';
  supportsDisplayTransition = getComputedStyle(probe).display === 'block';
  probe.remove();
  return supportsDisplayTransition;
}

function supportsTopLayerExit() {
  return window.CSS?.supports?.('overlay', 'auto') && canTransitionDisplay();
}

/**
 * Vista previa flotante centrada en pantalla (plato o etiqueta de vino) con fade-in / fade-out.
 * Funciona tanto en las tarjetas de la landing como dentro del popup modal (<dialog>) gracias a Top Layer.
 */
function initDishFloatingPreview(container) {
  const popover = document.getElementById('dish-floating-preview');
  const cards = [...container.querySelectorAll('[data-dish-preview-card]')];
  if (!popover || !cards.length) return;

  const imgEl = popover.querySelector('[data-dish-preview-img]');
  const titleEl = popover.querySelector('[data-dish-preview-title]');
  const detailEl = popover.querySelector('[data-dish-preview-detail]');
  const priceEl = popover.querySelector('[data-dish-preview-price]');
  const closeBtn = popover.querySelector('[data-dish-preview-close]');

  const hasPopoverAPI =
    typeof HTMLElement !== 'undefined' && 'popover' in HTMLElement.prototype;

  let activeCard = null;
  let pinned = false;

  const isOpen = () =>
    hasPopoverAPI ? popover.matches(':popover-open') : popover.classList.contains('is-open');

  const showPreview = (card, { pin = false } = {}) => {
    popover.removeAttribute('data-closing');

    const { dishImage, dishTitle, dishDetail, dishPrice, dishKind } = card.dataset;
    if (!dishImage || !imgEl) return;

    activeCard = card;
    if (pin) {
      pinned = true;
      popover.setAttribute('data-pinned', 'true');
    } else if (!pinned) {
      popover.removeAttribute('data-pinned');
    }

    popover.dataset.dishKind = dishKind || 'dish';
    imgEl.src = dishImage;
    imgEl.alt = dishTitle || '';
    if (titleEl) titleEl.textContent = dishTitle || '';
    if (priceEl) priceEl.textContent = dishPrice || '';
    if (detailEl) {
      detailEl.textContent = dishDetail || '';
      detailEl.hidden = !dishDetail;
    }

    if (hasPopoverAPI) {
      // Si ya estaba abierto debajo de un <dialog> recién abierto, re-promover al tope del Top Layer
      if (popover.matches(':popover-open')) {
        popover.hidePopover();
      }
      popover.showPopover();
    } else {
      popover.classList.add('is-open');
    }
  };

  const hidePreview = async ({ force = false } = {}) => {
    if (pinned && !force) return;
    pinned = false;
    activeCard = null;
    popover.removeAttribute('data-pinned');

    if (!isOpen()) return;

    if (!supportsTopLayerExit()) {
      popover.setAttribute('data-closing', '');
      const animations = popover.getAnimations({ subtree: true });
      if (animations.length > 0) {
        await Promise.race([
          Promise.allSettled(animations.map((a) => a.finished)),
          new Promise((r) => setTimeout(r, 400)),
        ]);
      }
      if (!popover.hasAttribute('data-closing')) return;
      popover.removeAttribute('data-closing');
    }

    if (hasPopoverAPI) {
      if (popover.matches(':popover-open')) {
        popover.hidePopover();
      }
    } else {
      popover.classList.remove('is-open');
    }
  };

  cards.forEach((card) => {
    card.addEventListener('click', (event) => {
      event.stopPropagation();
      if (isOpen() && activeCard === card) {
        hidePreview({ force: true });
      } else {
        showPreview(card, { pin: true });
      }
    });
  });

  closeBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    hidePreview({ force: true });
  });

  document.addEventListener('click', (event) => {
    if (!isOpen()) return;
    if (popover.contains(event.target)) return;
    if (event.target.closest('[data-dish-preview-card]')) return;
    hidePreview({ force: true });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen()) {
      hidePreview({ force: true });
    }
  });
}

/**
 * Modales de carta completa por categoría (<dialog closedby="any"> + Invoker Commands + fallbacks).
 */
function initCategoryModals(container) {
  const dialogs = [...container.querySelectorAll('dialog.menu-modal')];
  if (!dialogs.length) return;

  const hasInvokerCommands =
    typeof HTMLButtonElement !== 'undefined' && 'commandForElement' in HTMLButtonElement.prototype;
  const hasClosedBy =
    typeof HTMLDialogElement !== 'undefined' && 'closedBy' in HTMLDialogElement.prototype;

  // Fallback para navegadores sin Invoker Commands API (commandfor / command)
  if (!hasInvokerCommands) {
    const openButtons = container.querySelectorAll('[data-menu-modal-open]');
    openButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const dialog = document.getElementById(btn.dataset.menuModalOpen);
        if (!dialog) return;
        dialog._lastTrigger = btn;
        if (typeof dialog.showModal === 'function') {
          dialog.showModal();
        } else {
          dialog.setAttribute('open', '');
        }
      });
    });

    dialogs.forEach((dialog) => {
      dialog.querySelectorAll('[data-menu-modal-close]').forEach((closeBtn) => {
        closeBtn.addEventListener('click', () => dialog.close());
      });
    });
  }

  dialogs.forEach((dialog) => {
    dialog.addEventListener('close', () => {
      dialog._lastTrigger?.focus();
    });

    // Fallback para navegadores sin soporte nativo de <dialog closedby="any">
    if (!hasClosedBy) {
      dialog.addEventListener('click', (event) => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const isDialogContent =
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width;
        if (!isDialogContent) {
          dialog.close();
        }
      });
    }
  });
}
