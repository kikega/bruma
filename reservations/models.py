"""Modelos de reservas: zonas/categorías de sala y reservas de clientes."""

import secrets
from datetime import time

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Franjas horarias ofrecidas al cliente, agrupadas por turno.
LUNCH_SLOTS = (time(13, 30), time(14, 0), time(14, 30), time(15, 0), time(15, 30))
DINNER_SLOTS = (time(20, 30), time(21, 0), time(21, 30), time(22, 0), time(22, 30))

# A partir de este número de comensales se considera grupo («10+») y requiere confirmación manual.
LARGE_GROUP_SIZE = 10


class Shift(models.TextChoices):
    LUNCH = 'mediodia', 'Mediodía'
    DINNER = 'noche', 'Noche'

    @classmethod
    def for_time(cls, value):
        if value in LUNCH_SLOTS:
            return cls.LUNCH
        if value in DINNER_SLOTS:
            return cls.DINNER
        return None


class ZonePreference(models.TextChoices):
    INTERIOR = 'interior', 'Salón Interior'
    TERRACE = 'terraza', 'Terraza Bruma'
    ANY = 'indiferente', 'Indiferente'


class SeatingAreaQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class SeatingArea(models.Model):
    """Categoría/zona reservable (p. ej. «Mesa · Salón Interior», «Barra»).

    La capacidad se expresa en comensales por turno: es la suma de comensales
    de las reservas activas lo que determina si queda sitio.
    """

    class Kind(models.TextChoices):
        TABLE = 'mesa', 'Mesa'
        BAR = 'barra', 'Barra'

    class Zone(models.TextChoices):
        INTERIOR = ZonePreference.INTERIOR.value, ZonePreference.INTERIOR.label
        TERRACE = ZonePreference.TERRACE.value, ZonePreference.TERRACE.label

    name = models.CharField('nombre', max_length=80)
    kind = models.CharField('tipo', max_length=10, choices=Kind.choices, default=Kind.TABLE)
    zone = models.CharField('zona', max_length=12, choices=Zone.choices, default=Zone.INTERIOR)
    capacity = models.PositiveSmallIntegerField(
        'capacidad (comensales por turno)', validators=[MinValueValidator(1)],
    )
    max_party_size = models.PositiveSmallIntegerField(
        'máx. comensales por reserva', default=LARGE_GROUP_SIZE,
        validators=[MinValueValidator(1)],
    )
    online_bookable = models.BooleanField(
        'reservable desde la web', default=True,
        help_text='Si se desactiva, sólo el equipo puede asignar reservas a esta zona.',
    )
    is_active = models.BooleanField('activa', default=True)
    order = models.PositiveSmallIntegerField(
        'prioridad', default=0, help_text='Las zonas con menor valor se asignan primero.',
    )

    objects = SeatingAreaQuerySet.as_manager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'zona / categoría de sala'
        verbose_name_plural = 'zonas / categorías de sala'

    def __str__(self):
        return self.name


def _generate_code():
    return secrets.token_hex(3).upper()


class ReservationQuerySet(models.QuerySet):
    def active(self):
        """Reservas que ocupan plaza."""
        return self.filter(status__in=Reservation.ACTIVE_STATUSES)

    def for_service(self, date, shift):
        return self.filter(date=date, shift=shift)


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pendiente', 'Pendiente de confirmar'
        CONFIRMED = 'confirmada', 'Confirmada'
        SEATED = 'completada', 'Completada'
        CANCELLED = 'cancelada', 'Cancelada'
        NO_SHOW = 'no_show', 'No presentado'

    class Source(models.TextChoices):
        WEB = 'web', 'Web'
        PHONE = 'telefono', 'Teléfono'
        WALK_IN = 'sala', 'En sala'

    ACTIVE_STATUSES = (Status.PENDING, Status.CONFIRMED)

    code = models.CharField('localizador', max_length=8, unique=True, default=_generate_code, editable=False)
    full_name = models.CharField('nombre completo', max_length=120)
    email = models.EmailField('email')
    phone = models.CharField('teléfono', max_length=20)
    date = models.DateField('fecha')
    time = models.TimeField('hora')
    shift = models.CharField('turno', max_length=10, choices=Shift.choices, editable=False)
    party_size = models.PositiveSmallIntegerField(
        'comensales', validators=[MinValueValidator(1), MaxValueValidator(40)],
    )
    zone_preference = models.CharField(
        'zona preferida', max_length=12, choices=ZonePreference.choices, default=ZonePreference.ANY,
    )
    area = models.ForeignKey(
        SeatingArea, on_delete=models.PROTECT, null=True, blank=True,
        related_name='reservations', verbose_name='zona asignada',
    )
    notes = models.TextField('observaciones / alergias', blank=True)
    status = models.CharField('estado', max_length=12, choices=Status.choices, default=Status.PENDING)
    source = models.CharField('origen', max_length=10, choices=Source.choices, default=Source.WEB)
    internal_notes = models.TextField('notas internas', blank=True)
    created_at = models.DateTimeField('creada', auto_now_add=True)
    updated_at = models.DateTimeField('actualizada', auto_now=True)

    objects = ReservationQuerySet.as_manager()

    class Meta:
        ordering = ['-date', 'time']
        verbose_name = 'reserva'
        verbose_name_plural = 'reservas'
        indexes = [models.Index(fields=['date', 'shift', 'status'])]

    def __str__(self):
        return f'{self.code} · {self.full_name} · {self.date:%d/%m/%Y} {self.time:%H:%M}'

    def save(self, *args, **kwargs):
        self.shift = Shift.for_time(self.time) or self._closest_shift()
        super().save(*args, **kwargs)

    def _closest_shift(self):
        # Horas fuera de las franjas web (p. ej. reservas manuales): asignar por mitad del día.
        return Shift.LUNCH if self.time < time(18, 0) else Shift.DINNER

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def party_label(self):
        return f'{self.party_size}+' if self.party_size >= LARGE_GROUP_SIZE else str(self.party_size)
