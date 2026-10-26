"""Datos de contacto, presencia y metadatos SEO del restaurante disponibles en todas las plantillas."""

from functools import lru_cache

from django.conf import settings
from django.contrib.staticfiles import finders

LOGO_PATH = 'img/brumalogo.webp'

DOMAIN = getattr(settings, 'BRUMA_SITE_DOMAIN', 'brumarestaurant.es')
SITE_URL = getattr(settings, 'BRUMA_SITE_URL', f'https://{DOMAIN}')
ACCEPTS_RESERVATIONS = getattr(settings, 'BRUMA_ACCEPTS_RESERVATIONS', True)

RESTAURANT = {
    'name': 'Bruma',
    'legal_name': 'Bruma Restaurante',
    'tagline': 'Alta cocina mediterránea',
    'domain': DOMAIN,
    'site_url': SITE_URL,
    'accepts_reservations': ACCEPTS_RESERVATIONS,
    'cuisines': [
        'Cocina mediterránea',
        'Alta cocina',
        'Cocina de autor',
        'Pescados y mariscos de lonja',
    ],
    'price_range': '€€€',
    'currencies_accepted': 'EUR',
    'payment_accepted': 'Efectivo, Tarjeta de crédito, Pago móvil',
    'chef': 'Sergio Otero Puig',
    'address_line': 'Paseo Marítimo, 12',
    'postal_code': '03001',
    'locality': 'Alicante',
    'region': 'Comunidad Valenciana',
    'city': '03001 Alicante',
    'country': 'España',
    'country_code': 'ES',
    'geo': {
        'latitude': '38.3422',
        'longitude': '-0.4810',
    },
    'phone': '+34 965 000 000',
    'phone_href': '+34965000000',
    'email': f'reservas@{DOMAIN}',
    'maps_url': 'https://www.google.com/maps/search/?api=1&query=Paseo+Mar%C3%ADtimo+12+Alicante',
    'hours': [
        {'days': 'Martes a sábado', 'time': '13:30 – 16:00 · 20:30 – 23:30'},
        {'days': 'Domingo', 'time': '13:30 – 16:00'},
        {'days': 'Lunes', 'time': 'Cerrado'},
    ],
    'opening_hours_schema': [
        'Tu-Sa 13:30-16:00',
        'Tu-Sa 20:30-23:30',
        'Su 13:30-16:00',
    ],
    'opening_hours_specification': [
        {
            'days': ['Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            'opens': '13:30',
            'closes': '16:00',
        },
        {
            'days': ['Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            'opens': '20:30',
            'closes': '23:30',
        },
        {
            'days': ['Sunday'],
            'opens': '13:30',
            'closes': '16:00',
        },
    ],
    'social': [
        {'name': 'Instagram', 'url': 'https://www.instagram.com/brumarestaurant', 'icon': 'instagram'},
        {'name': 'Facebook', 'url': 'https://www.facebook.com/brumarestaurant', 'icon': 'facebook'},
        {'name': 'TripAdvisor', 'url': 'https://www.tripadvisor.es/', 'icon': 'tripadvisor'},
    ],
}

SEO_DEFAULTS = {
    'title': 'Bruma · Restaurante de Alta Cocina Mediterránea en Alicante',
    'description': (
        'Bruma, restaurante de alta cocina mediterránea frente al mar en Alicante. '
        'Producto fresco de lonja, arroces, pescados de costera y bodega de blancos salinos '
        'por el chef Sergio Otero Puig. Reserva tu mesa en brumarestaurant.es.'
    ),
    'keywords': (
        'Bruma restaurante, cocina mediterránea, alta cocina, restaurante alta cocina Alicante, '
        'cocina mediterránea frente al mar, chef Sergio Otero Puig, arroces Alicante, '
        'pescado de lonja, reservar restaurante Alicante, brumarestaurant.es'
    ),
    'og_title': 'Bruma · Restaurante de Alta Cocina Mediterránea frente al Mar',
    'og_description': (
        'Cocina de lonja, sal y calma frente al Mediterráneo en Alicante. '
        'Descubre la propuesta de alta cocina mediterránea del chef Sergio Otero Puig y reserva tu mesa.'
    ),
    'locale': 'es_ES',
}


@lru_cache(maxsize=1)
def _logo_available():
    return finders.find(LOGO_PATH) is not None


def restaurant(request):
    path = getattr(request, 'path', '/') or '/'
    canonical_url = f'{SITE_URL}{path}'
    seo = {
        **SEO_DEFAULTS,
        'domain': DOMAIN,
        'site_url': SITE_URL,
        'canonical_url': canonical_url,
    }
    return {
        'restaurant': RESTAURANT,
        'seo': seo,
        'accepts_reservations': ACCEPTS_RESERVATIONS,
        'aceptar_reservas': ACCEPTS_RESERVATIONS,
        'logo_path': LOGO_PATH if _logo_available() else None,
    }
