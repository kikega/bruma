"""Lógica de negocio de reservas: ocupación, disponibilidad y asignación de zona.

Se mantiene fuera de vistas y modelos para poder reutilizarla desde la web,
el admin y los tests (principio de responsabilidad única).
"""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum

from .models import LARGE_GROUP_SIZE, Reservation, SeatingArea, ZonePreference


class NoAvailability(Exception):
    """No hay plazas suficientes para el turno solicitado."""


@dataclass(frozen=True)
class AreaOccupancy:
    area: SeatingArea
    booked: int

    @property
    def capacity(self):
        return self.area.capacity

    @property
    def remaining(self):
        return max(self.capacity - self.booked, 0)

    @property
    def percent(self):
        return min(round(self.booked * 100 / self.capacity), 100) if self.capacity else 100


def booked_covers(date, shift, *, exclude_pk=None):
    """Comensales ya reservados por zona → ``{area_id: covers}``."""
    qs = Reservation.objects.active().for_service(date, shift).exclude(area__isnull=True)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    rows = qs.values('area_id').annotate(total=Sum('party_size'))
    return {row['area_id']: row['total'] for row in rows}


def occupancy(date, shift, areas=None, *, exclude_pk=None):
    areas = list(areas if areas is not None else SeatingArea.objects.active())
    booked = booked_covers(date, shift, exclude_pk=exclude_pk)
    return [AreaOccupancy(area=a, booked=booked.get(a.pk, 0)) for a in areas]


def candidate_areas(party_size, zone_preference, *, online_only=True):
    """Zonas válidas para una petición, en orden de prioridad (mesas antes que barra)."""
    qs = SeatingArea.objects.active().filter(max_party_size__gte=min(party_size, LARGE_GROUP_SIZE))
    if online_only:
        qs = qs.filter(online_bookable=True)
    if zone_preference != ZonePreference.ANY:
        qs = qs.filter(zone=zone_preference, kind=SeatingArea.Kind.TABLE)
    areas = list(qs)
    areas.sort(key=lambda a: (a.kind != SeatingArea.Kind.TABLE, a.order))
    return areas


def find_area(date, shift, party_size, zone_preference, *, areas=None, exclude_pk=None):
    areas = areas if areas is not None else candidate_areas(party_size, zone_preference)
    for occ in occupancy(date, shift, areas, exclude_pk=exclude_pk):
        if occ.remaining >= party_size:
            return occ.area
    return None


def availability(date, shift, party_size, zone_preference):
    """Resumen público de disponibilidad para el formulario (sin datos sensibles)."""
    areas = candidate_areas(party_size, zone_preference)
    occ = occupancy(date, shift, areas)
    remaining = max((o.remaining for o in occ), default=0)
    total_capacity = sum(o.capacity for o in occ)
    total_booked = sum(o.booked for o in occ)
    available = remaining >= party_size
    low = available and total_capacity and (total_booked / total_capacity) >= 0.75
    return {
        'available': available,
        'level': 'full' if not available else ('low' if low else 'ok'),
    }


@transaction.atomic
def create_reservation(*, party_size, zone_preference, date, shift=None, **fields):
    """Crea una reserva asignando zona de forma segura frente a reservas concurrentes.

    Se bloquean las filas de las zonas candidatas (``SELECT … FOR UPDATE``) para que dos
    peticiones simultáneas no puedan sobrevender el mismo turno.
    """
    reservation = Reservation(party_size=party_size, zone_preference=zone_preference, date=date, **fields)
    reservation.shift = shift or reservation._closest_shift()
    candidates = candidate_areas(party_size, zone_preference)
    locked = list(SeatingArea.objects.select_for_update().filter(pk__in=[a.pk for a in candidates]))
    locked.sort(key=lambda a: (a.kind != SeatingArea.Kind.TABLE, a.order))

    area = find_area(date, reservation.shift, party_size, zone_preference, areas=locked)
    if area is None:
        raise NoAvailability

    reservation.area = area
    reservation.status = (
        Reservation.Status.PENDING if party_size >= LARGE_GROUP_SIZE else Reservation.Status.CONFIRMED
    )
    reservation.save()
    return reservation
