from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from menu.models import Allergen, Category, Dish
from reservations import services
from reservations.models import Reservation, SeatingArea, Shift, ZonePreference


class MenuAndHomeTests(TestCase):
    def setUp(self):
        self.allergen = Allergen.objects.create(code='crustaceos', name='Crustáceos', abbreviation='CR', order=1)
        self.cat = Category.objects.create(name='Crudos y Bruma', slug='crudos-y-bruma', order=1)
        self.dish = Dish.objects.create(
            category=self.cat,
            name='Carpaccio de gamba roja',
            description='Láminas translúcidas con aceite de sus cabezas.',
            price=Decimal('28.00'),
            is_signature=True,
        )
        self.dish.allergens.add(self.allergen)

    def test_home_renders_sections_and_menu(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carpaccio de gamba roja')
        self.assertContains(response, 'Sergio Otero Puig')
        self.assertContains(response, 'brumalogo.webp')


class ReservationCapacityTests(TestCase):
    def setUp(self):
        self.tomorrow = timezone.localdate() + timedelta(days=1)
        self.interior = SeatingArea.objects.create(
            name='Mesa · Salón Interior',
            kind=SeatingArea.Kind.TABLE,
            zone=SeatingArea.Zone.INTERIOR,
            capacity=6,
            max_party_size=10,
            order=10,
        )
        self.barra = SeatingArea.objects.create(
            name='Barra',
            kind=SeatingArea.Kind.BAR,
            zone=SeatingArea.Zone.INTERIOR,
            capacity=2,
            max_party_size=2,
            order=20,
        )

    def test_allocates_table_then_bar_and_blocks_when_full(self):
        # 1ª reserva de 6 comensales llena las mesas de Salón Interior
        r1 = services.create_reservation(
            full_name='Ana Marín',
            email='ana@example.com',
            phone='+34 600 111 222',
            date=self.tomorrow,
            time=timezone.datetime.strptime('14:00', '%H:%M').time(),
            shift=Shift.LUNCH,
            party_size=6,
            zone_preference=ZonePreference.ANY,
        )
        self.assertEqual(r1.area, self.interior)
        self.assertEqual(r1.status, Reservation.Status.CONFIRMED)

        # 2ª reserva de 2 con zona Indiferente pasa a Barra (quedan 2 plazas)
        r2 = services.create_reservation(
            full_name='Carlos Ruiz',
            email='carlos@example.com',
            phone='600333444',
            date=self.tomorrow,
            time=timezone.datetime.strptime('14:30', '%H:%M').time(),
            shift=Shift.LUNCH,
            party_size=2,
            zone_preference=ZonePreference.ANY,
        )
        self.assertEqual(r2.area, self.barra)

        # 3ª reserva en el mismo turno ya no tiene sitio
        with self.assertRaises(services.NoAvailability):
            services.create_reservation(
                full_name='Lucía Pérez',
                email='lucia@example.com',
                phone='600555666',
                date=self.tomorrow,
                time=timezone.datetime.strptime('15:00', '%H:%M').time(),
                shift=Shift.LUNCH,
                party_size=2,
                zone_preference=ZonePreference.ANY,
            )

    def test_json_create_and_availability_endpoints(self):
        avail = self.client.get(
            reverse('reservations:availability'),
            {'fecha': self.tomorrow.isoformat(), 'hora': '21:00', 'comensales': 4, 'zona': 'interior'},
        )
        self.assertEqual(avail.status_code, 200)
        self.assertTrue(avail.json()['available'])

        res = self.client.post(
            reverse('reservations:create'),
            {
                'full_name': 'Elena Navarro',
                'email': 'elena@example.com',
                'phone': '+34 612 345 678',
                'date': self.tomorrow.isoformat(),
                'time': '21:00',
                'party_size': '4',
                'zone_preference': 'interior',
                'notes': 'Sin gluten',
            },
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['reservation']['area'], 'Mesa · Salón Interior')
