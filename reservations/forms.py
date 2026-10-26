import re
from datetime import datetime, time, timedelta

from django import forms
from django.conf import settings
from django.utils import timezone

from . import services
from .models import DINNER_SLOTS, LARGE_GROUP_SIZE, LUNCH_SLOTS, Reservation, Shift, ZonePreference

PHONE_PATTERN = r'^\+?[0-9][0-9\s\-]{7,16}$'
PHONE_RE = re.compile(PHONE_PATTERN)


def _slot_choices(slots):
    return [(t.strftime('%H:%M'), t.strftime('%H:%M')) for t in slots]


TIME_CHOICES = [
    ('', 'Selecciona una hora'),
    ('Mediodía · 13:30 – 15:30', _slot_choices(LUNCH_SLOTS)),
    ('Noche · 20:30 – 22:30', _slot_choices(DINNER_SLOTS)),
]

PARTY_CHOICES = [('', 'Comensales')] + [
    (n, f'{n} persona' if n == 1 else f'{n} personas') for n in range(1, LARGE_GROUP_SIZE)
] + [(LARGE_GROUP_SIZE, f'{LARGE_GROUP_SIZE} o más (grupo)')]


def max_booking_date():
    return timezone.localdate() + timedelta(days=settings.BRUMA_RESERVATION_MAX_DAYS_AHEAD)


class ReservationForm(forms.Form):
    """Formulario público de reserva. La presentación vive en la plantilla."""

    full_name = forms.CharField(
        label='Nombre completo', min_length=3, max_length=120,
        error_messages={'required': 'Indica tu nombre completo.', 'min_length': 'El nombre es demasiado corto.'},
    )
    email = forms.EmailField(
        label='Email',
        error_messages={'required': 'Indica tu email.', 'invalid': 'Introduce un email válido (nombre@dominio.com).'},
    )
    phone = forms.CharField(
        label='Teléfono', max_length=20,
        error_messages={'required': 'Indica un teléfono de contacto.'},
    )
    date = forms.DateField(
        label='Fecha', error_messages={'required': 'Elige una fecha.', 'invalid': 'Fecha no válida.'},
    )
    time = forms.ChoiceField(
        label='Turno y hora', choices=TIME_CHOICES,
        error_messages={'required': 'Elige una hora.', 'invalid_choice': 'Hora no disponible.'},
    )
    party_size = forms.TypedChoiceField(
        label='Comensales', choices=PARTY_CHOICES, coerce=int,
        error_messages={'required': 'Indica el número de comensales.'},
    )
    zone_preference = forms.ChoiceField(
        label='Zona preferida', choices=ZonePreference.choices, initial=ZonePreference.ANY,
    )
    notes = forms.CharField(label='Observaciones / alergias', required=False, max_length=600)

    def clean_full_name(self):
        return ' '.join(self.cleaned_data['full_name'].split())

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = re.sub(r'\D', '', phone)
        if not PHONE_RE.match(phone) or not 9 <= len(digits) <= 15:
            raise forms.ValidationError('Introduce un teléfono válido (mínimo 9 dígitos).')
        return phone

    def clean_date(self):
        value = self.cleaned_data['date']
        if value < timezone.localdate():
            raise forms.ValidationError('La fecha no puede ser anterior a hoy.')
        if value > max_booking_date():
            raise forms.ValidationError(
                f'Aceptamos reservas con un máximo de {settings.BRUMA_RESERVATION_MAX_DAYS_AHEAD} días de antelación.'
            )
        return value

    def clean_time(self):
        return time.fromisoformat(self.cleaned_data['time'])

    def clean(self):
        cleaned = super().clean()
        date, slot = cleaned.get('date'), cleaned.get('time')
        if date and slot:
            moment = timezone.make_aware(datetime.combine(date, slot))
            if moment <= timezone.now() + timedelta(minutes=30):
                self.add_error('time', 'Esa hora ya no está disponible hoy. Elige otra franja.')
        return cleaned

    @property
    def shift(self):
        return Shift.for_time(self.cleaned_data['time'])

    def save(self):
        """Crea la reserva; lanza ``services.NoAvailability`` si el turno está completo."""
        data = self.cleaned_data
        return services.create_reservation(
            full_name=data['full_name'], email=data['email'], phone=data['phone'],
            date=data['date'], time=data['time'], shift=self.shift,
            party_size=data['party_size'], zone_preference=data['zone_preference'],
            notes=data['notes'], source=Reservation.Source.WEB,
        )


class AvailabilityQueryForm(forms.Form):
    """Parámetros GET de la consulta de disponibilidad en tiempo real."""

    fecha = forms.DateField()
    hora = forms.ChoiceField(choices=_slot_choices(LUNCH_SLOTS + DINNER_SLOTS))
    comensales = forms.IntegerField(min_value=1, max_value=LARGE_GROUP_SIZE)
    zona = forms.ChoiceField(choices=ZonePreference.choices, required=False)


class ReservationAdminForm(forms.ModelForm):
    """Valida en el admin que la zona asignada no supere su capacidad."""

    class Meta:
        model = Reservation
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        area, date, slot = cleaned.get('area'), cleaned.get('date'), cleaned.get('time')
        party, status = cleaned.get('party_size'), cleaned.get('status')
        if not (area and date and slot and party) or status not in Reservation.ACTIVE_STATUSES:
            return cleaned
        if party > area.max_party_size:
            self.add_error('area', f'«{area}» admite como máximo {area.max_party_size} comensales por reserva.')
        shift = Shift.for_time(slot) or (Shift.LUNCH if slot < time(18, 0) else Shift.DINNER)
        [occ] = services.occupancy(date, shift, [area], exclude_pk=self.instance.pk)
        if occ.remaining < party:
            self.add_error(
                'area',
                f'Sin plazas suficientes en «{area}» para ese turno: quedan {occ.remaining} de {occ.capacity}.',
            )
        return cleaned
