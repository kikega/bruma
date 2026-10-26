/**
 * Formulario de reservas reactivo:
 * - Validación en tiempo real tras interacción (:user-invalid + sincronización ARIA)
 * - Consulta de disponibilidad en vivo contra PostgreSQL
 * - Envío asíncrono con spinner y tarjeta de confirmación
 */
export function initReservationForm() {
  const form = document.getElementById('reservation-form');
  const confirmation = document.getElementById('reservation-confirmation');
  if (!form || !confirmation) return;

  const alertBox = form.querySelector('[data-form-alert]');
  const availabilityBox = form.querySelector('[data-availability-box]');
  const availabilityText = form.querySelector('[data-availability-text]');
  const submitBtn = form.querySelector('[data-submit-btn]');
  const submitSpinner = form.querySelector('[data-submit-spinner]');
  const submitLabel = form.querySelector('[data-submit-label]');
  const newReservationBtn = confirmation.querySelector('[data-new-reservation]');

  const interacted = new WeakMap();
  const supportsUserInvalid =
    typeof CSS !== 'undefined' && CSS.supports('selector(:user-invalid)');

  const getCustomMessage = (field) => {
    const v = field.validity;
    if (v.valid) return '';
    if (v.valueMissing && field.dataset.msgMissing) return field.dataset.msgMissing;
    if (v.typeMismatch && field.dataset.msgType) return field.dataset.msgType;
    if (v.tooShort && field.dataset.msgShort) return field.dataset.msgShort;
    if (v.patternMismatch && field.dataset.msgPattern) return field.dataset.msgPattern;
    if (v.rangeUnderflow && field.dataset.msgUnderflow) return field.dataset.msgUnderflow;
    if (v.rangeOverflow && field.dataset.msgOverflow) return field.dataset.msgOverflow;
    return field.validationMessage || 'Revisa este campo.';
  };

  const renderFieldState = (field, { force = false } = {}) => {
    if (!field.name || !field.willValidate) return true;
    const state = interacted.get(field) || { touched: false, blurred: false };
    const shouldShow =
      force ||
      (supportsUserInvalid && field.matches(':user-invalid')) ||
      (state.touched && state.blurred);

    const valid = field.checkValidity();
    const errorEl = form.querySelector(`[data-error-for="${field.name}"]`);

    if (!valid && shouldShow) {
      field.classList.add('is-invalid');
      field.setAttribute('aria-invalid', 'true');
      if (errorEl) errorEl.textContent = getCustomMessage(field);
    } else {
      field.classList.remove('is-invalid');
      field.removeAttribute('aria-invalid');
      if (errorEl) errorEl.textContent = '';
    }
    return valid;
  };

  // Eventos de validación diferida hasta interacción (blur / input tras error)
  form.addEventListener(
    'blur',
    (event) => {
      const field = event.target;
      if (!field.matches?.('input, select, textarea')) return;
      const state = interacted.get(field) || { touched: false, blurred: false };
      state.blurred = true;
      interacted.set(field, state);
      if (state.touched || (supportsUserInvalid && field.matches(':user-invalid'))) {
        renderFieldState(field, { force: true });
      }
    },
    true,
  );

  form.addEventListener('input', (event) => {
    const field = event.target;
    if (!field.matches?.('input, select, textarea')) return;
    const state = interacted.get(field) || { touched: false, blurred: false };
    state.touched = true;
    interacted.set(field, state);
    if (state.blurred || field.hasAttribute('aria-invalid')) {
      renderFieldState(field, { force: true });
    }
  });

  form.addEventListener('change', (event) => {
    const field = event.target;
    if (!field.matches?.('input, select, textarea')) return;
    const state = interacted.get(field) || { touched: true, blurred: true };
    state.touched = true;
    state.blurred = true;
    interacted.set(field, state);
    renderFieldState(field, { force: true });
  });

  // Consulta de disponibilidad en vivo cuando cambian fecha, hora, comensales o zona
  const availabilityUrl = form.dataset.availabilityUrl;
  const dateField = form.elements.namedItem('date');
  const timeField = form.elements.namedItem('time');
  const partyField = form.elements.namedItem('party_size');
  const zoneField = form.elements.namedItem('zone_preference');

  let availabilityTimer = null;
  const checkAvailability = async () => {
    if (!availabilityUrl || !availabilityBox || !availabilityText) return;
    if (!dateField?.value || !timeField?.value || !partyField?.value) {
      availabilityBox.hidden = true;
      return;
    }
    const params = new URLSearchParams({
      fecha: dateField.value,
      hora: timeField.value,
      comensales: partyField.value,
      zona: zoneField?.value || 'indiferente',
    });
    try {
      const response = await fetch(`${availabilityUrl}?${params.toString()}`, {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) {
        availabilityBox.hidden = true;
        return;
      }
      const data = await response.json();
      if (!data.ok) {
        availabilityBox.hidden = true;
        return;
      }
      const dotColor =
        data.level === 'ok'
          ? 'bg-salvia-light'
          : data.level === 'low'
            ? 'bg-arena'
            : 'bg-[#F2A69B]';
      availabilityText.innerHTML = `<span class="inline-block size-2 rounded-full ${dotColor}" aria-hidden="true"></span><span></span>`;
      availabilityText.lastElementChild.textContent = data.message;
      availabilityBox.hidden = false;
    } catch {
      availabilityBox.hidden = true;
    }
  };

  [dateField, timeField, partyField, zoneField].forEach((el) => {
    el?.addEventListener('change', () => {
      clearTimeout(availabilityTimer);
      availabilityTimer = setTimeout(checkAvailability, 150);
    });
  });

  // Envío asíncrono
  const setLoading = (loading) => {
    if (submitBtn) submitBtn.disabled = loading;
    if (submitSpinner) submitSpinner.hidden = !loading;
    if (submitLabel) submitLabel.textContent = loading ? 'Procesando reserva…' : 'Confirmar reserva';
  };

  const formatDateEs = (iso) => {
    try {
      const [y, m, d] = iso.split('-').map(Number);
      return new Intl.DateTimeFormat('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }).format(new Date(y, m - 1, d));
    } catch {
      return iso;
    }
  };

  const showConfirmation = (reservation) => {
    const map = {
      code: reservation.code,
      full_name: reservation.full_name,
      date: formatDateEs(reservation.date),
      time: reservation.time,
      party_size: `${reservation.party_size} comensales`,
      area: reservation.area || reservation.zone_preference,
      email: reservation.email,
      phone: reservation.phone,
    };
    for (const [key, val] of Object.entries(map)) {
      const target = confirmation.querySelector(`[data-confirm-field="${key}"]`);
      if (target) target.textContent = val;
    }
    const statusEl = confirmation.querySelector('[data-confirm-status]');
    const leadEl = confirmation.querySelector('[data-confirm-lead]');
    if (statusEl) statusEl.textContent = reservation.status_label || 'Reserva confirmada';
    if (leadEl) {
      leadEl.textContent = reservation.is_large_group
        ? 'Hemos recibido tu solicitud de grupo. Nuestro jefe de sala te contactará en breve para confirmar los detalles:'
        : 'Te esperamos en Bruma. Hemos registrado tu mesa con el siguiente resumen:';
    }

    form.hidden = true;
    confirmation.hidden = false;
    confirmation.focus();
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (alertBox) {
      alertBox.hidden = true;
      alertBox.textContent = '';
    }

    const controls = [...form.querySelectorAll('input, select, textarea')];
    let firstInvalid = null;
    for (const control of controls) {
      const valid = renderFieldState(control, { force: true });
      if (!valid && !firstInvalid) firstInvalid = control;
    }
    if (firstInvalid) {
      firstInvalid.focus();
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        const errors = payload.errors || {};
        let focused = false;
        for (const [fieldName, messages] of Object.entries(errors)) {
          const message = Array.isArray(messages) ? messages[0] : String(messages);
          if (fieldName === '__all__') {
            if (alertBox) {
              alertBox.textContent = message;
              alertBox.hidden = false;
            }
            continue;
          }
          const field = form.elements.namedItem(fieldName);
          const errorEl = form.querySelector(`[data-error-for="${fieldName}"]`);
          if (errorEl) errorEl.textContent = message;
          if (field && 'classList' in field) {
            field.classList.add('is-invalid');
            field.setAttribute('aria-invalid', 'true');
            if (!focused) {
              field.focus();
              focused = true;
            }
          }
        }
        return;
      }

      showConfirmation(payload.reservation);
    } catch {
      if (alertBox) {
        alertBox.textContent =
          'No hemos podido conectar con el servidor. Por favor, inténtalo de nuevo en unos segundos.';
        alertBox.hidden = false;
      }
    } finally {
      setLoading(false);
    }
  });

  newReservationBtn?.addEventListener('click', () => {
    form.reset();
    for (const control of form.querySelectorAll('input, select, textarea')) {
      interacted.delete(control);
      control.classList.remove('is-invalid');
      control.removeAttribute('aria-invalid');
    }
    for (const err of form.querySelectorAll('[data-error-for]')) {
      err.textContent = '';
    }
    if (alertBox) alertBox.hidden = true;
    if (availabilityBox) availabilityBox.hidden = true;
    confirmation.hidden = true;
    form.hidden = false;
    form.querySelector('input')?.focus();
  });
}
