from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView

from gallery.models import GalleryImage
from menu.models import Allergen, Category, Wine
from reservations.forms import ReservationForm, max_booking_date


class HomeView(TemplateView):
    """Landing page: compone las secciones a partir de cada app (carta, bodega, galería, reservas)."""

    template_name = 'home/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            categories=Category.objects.with_active_dishes(),
            wine_groups=Wine.objects.grouped_by_type(),
            allergens=Allergen.objects.all(),
            gallery_images=GalleryImage.objects.published(),
            reservation_form=ReservationForm(),
            reservation_min_date=timezone.localdate().isoformat(),
            reservation_max_date=max_booking_date().isoformat(),
            reservation_max_days=settings.BRUMA_RESERVATION_MAX_DAYS_AHEAD,
        )
        return context


def robots_txt(request):
    """Archivo robots.txt para indexación profesional por buscadores."""
    site_url = getattr(settings, 'BRUMA_SITE_URL', 'https://brumarestaurant.es')
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        f'Sitemap: {site_url}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    """Sitemap XML principal con el dominio canónico brumarestaurant.es."""
    site_url = getattr(settings, 'BRUMA_SITE_URL', 'https://brumarestaurant.es')
    today = timezone.localdate().isoformat()
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        f'    <loc>{site_url}/</loc>\n'
        f'    <lastmod>{today}</lastmod>\n'
        '    <changefreq>weekly</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>\n'
    )
    return HttpResponse(xml, content_type='application/xml; charset=utf-8')
