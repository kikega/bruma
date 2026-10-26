from django.conf import settings
from django.utils import timezone
from django.views.generic import TemplateView

from gallery.models import GalleryImage
from menu.models import Allergen, Category
from reservations.forms import ReservationForm, max_booking_date


class HomeView(TemplateView):
    """Landing page: compone las secciones a partir de cada app (carta, galería, reservas)."""

    template_name = 'home/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            categories=Category.objects.with_active_dishes(),
            allergens=Allergen.objects.all(),
            gallery_images=GalleryImage.objects.published(),
            reservation_form=ReservationForm(),
            reservation_min_date=timezone.localdate().isoformat(),
            reservation_max_date=max_booking_date().isoformat(),
            reservation_max_days=settings.BRUMA_RESERVATION_MAX_DAYS_AHEAD,
        )
        return context
