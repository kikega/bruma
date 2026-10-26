"""Datos de contacto y presencia del restaurante disponibles en todas las plantillas."""

from functools import lru_cache

from django.contrib.staticfiles import finders

LOGO_PATH = 'img/brumalogo.webp'

RESTAURANT = {
    'name': 'Bruma',
    'tagline': 'Alta cocina mediterránea',
    'address_line': 'Paseo Marítimo, 12',
    'city': '03001 Alicante',
    'country': 'España',
    'phone': '+34 965 000 000',
    'phone_href': '+34965000000',
    'email': 'reservas@brumarestaurante.es',
    'maps_url': 'https://www.google.com/maps/search/?api=1&query=Paseo+Mar%C3%ADtimo+12+Alicante',
    'hours': [
        {'days': 'Martes a sábado', 'time': '13:30 – 16:00 · 20:30 – 23:30'},
        {'days': 'Domingo', 'time': '13:30 – 16:00'},
        {'days': 'Lunes', 'time': 'Cerrado'},
    ],
    'social': [
        {'name': 'Instagram', 'url': 'https://instagram.com/', 'icon': 'instagram'},
        {'name': 'Facebook', 'url': 'https://facebook.com/', 'icon': 'facebook'},
        {'name': 'TripAdvisor', 'url': 'https://tripadvisor.es/', 'icon': 'tripadvisor'},
    ],
}


@lru_cache(maxsize=1)
def _logo_available():
    return finders.find(LOGO_PATH) is not None


def restaurant(request):
    return {'restaurant': RESTAURANT, 'logo_path': LOGO_PATH if _logo_available() else None}
