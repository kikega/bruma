from datetime import time

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import services
from .forms import AvailabilityQueryForm, ReservationForm
from .models import LARGE_GROUP_SIZE, Shift

FULL_MESSAGE = (
    'Lo sentimos, no quedan plazas para ese turno en la zona elegida. '
    'Prueba con otra hora, otra zona o llámanos.'
)


def _wants_json(request):
    return 'application/json' in request.headers.get('Accept', '')


def _serialize(reservation):
    return {
        'code': reservation.code,
        'full_name': reservation.full_name,
        'email': reservation.email,
        'phone': reservation.phone,
        'date': reservation.date.isoformat(),
        'time': reservation.time.strftime('%H:%M'),
        'shift': reservation.get_shift_display(),
        'party_size': reservation.party_label,
        'zone_preference': reservation.get_zone_preference_display(),
        'area': str(reservation.area) if reservation.area else '',
        'notes': reservation.notes,
        'status': reservation.status,
        'status_label': reservation.get_status_display(),
        'is_large_group': reservation.party_size >= LARGE_GROUP_SIZE,
    }


@require_POST
def create_reservation(request):
    """Crea una reserva. Responde JSON para el formulario reactivo y redirige sin JS."""
    form = ReservationForm(request.POST)
    as_json = _wants_json(request)

    if not form.is_valid():
        if as_json:
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
        messages.error(request, 'Revisa los datos del formulario de reserva.')
        return redirect(reverse('core:home') + '#reservas')

    try:
        reservation = form.save()
    except services.NoAvailability:
        if as_json:
            return JsonResponse({'ok': False, 'errors': {'__all__': [FULL_MESSAGE]}}, status=409)
        messages.error(request, FULL_MESSAGE)
        return redirect(reverse('core:home') + '#reservas')

    if as_json:
        return JsonResponse({'ok': True, 'reservation': _serialize(reservation)}, status=201)
    messages.success(request, f'Reserva registrada. Localizador: {reservation.code}')
    return redirect(reverse('core:home') + '#reservas')


@require_GET
def check_availability(request):
    """Consulta ligera de disponibilidad para el indicador en tiempo real."""
    query = AvailabilityQueryForm(request.GET)
    if not query.is_valid():
        return JsonResponse({'ok': False, 'errors': query.errors}, status=400)

    data = query.cleaned_data
    slot = time.fromisoformat(data['hora'])
    result = services.availability(
        data['fecha'], Shift.for_time(slot), data['comensales'], data['zona'] or 'indiferente',
    )
    messages_by_level = {
        'ok': 'Hay disponibilidad para este turno.',
        'low': 'Quedan pocas plazas para este turno.',
        'full': 'Turno completo en esta zona. Prueba otra hora o zona.',
    }
    return JsonResponse({'ok': True, **result, 'message': messages_by_level[result['level']]})
