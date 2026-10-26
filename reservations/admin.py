from datetime import timedelta

from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from . import services
from .forms import ReservationAdminForm
from .models import Reservation, SeatingArea, Shift

STATUS_COLORS = {
    Reservation.Status.PENDING: '#C2B280',
    Reservation.Status.CONFIRMED: '#8A9A86',
    Reservation.Status.SEATED: '#1D4E89',
    Reservation.Status.CANCELLED: '#9CA3AF',
    Reservation.Status.NO_SHOW: '#B45309',
}


@admin.register(SeatingArea)
class SeatingAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'zone', 'capacity', 'max_party_size', 'online_bookable', 'is_active', 'order')
    list_editable = ('capacity', 'max_party_size', 'online_bookable', 'is_active', 'order')
    list_filter = ('kind', 'zone', 'is_active')


class UpcomingFilter(admin.SimpleListFilter):
    title = 'periodo'
    parameter_name = 'periodo'

    def lookups(self, request, model_admin):
        return [('hoy', 'Hoy'), ('manana', 'Mañana'), ('proximas', 'Próximas'), ('pasadas', 'Pasadas')]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        match self.value():
            case 'hoy':
                return queryset.filter(date=today)
            case 'manana':
                return queryset.filter(date=today + timedelta(days=1))
            case 'proximas':
                return queryset.filter(date__gte=today)
            case 'pasadas':
                return queryset.filter(date__lt=today)
        return queryset


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    form = ReservationAdminForm
    change_list_template = 'admin/reservations/reservation/change_list.html'
    list_display = (
        'code', 'full_name', 'date', 'time', 'shift', 'party_label_display',
        'zone_preference', 'area', 'status_badge', 'source',
    )
    list_display_links = ('code', 'full_name')
    list_filter = (UpcomingFilter, 'status', 'shift', 'area', 'zone_preference', 'source')
    search_fields = ('code', 'full_name', 'email', 'phone')
    date_hierarchy = 'date'
    list_select_related = ('area',)
    readonly_fields = ('code', 'shift', 'created_at', 'updated_at')
    actions = ('mark_confirmed', 'mark_seated', 'mark_cancelled', 'mark_no_show')
    fieldsets = (
        ('Cliente', {'fields': ('code', 'full_name', 'email', 'phone')}),
        ('Servicio', {'fields': ('date', 'time', 'shift', 'party_size', 'zone_preference', 'area')}),
        ('Gestión', {'fields': ('status', 'source', 'notes', 'internal_notes', 'created_at', 'updated_at')}),
    )

    @admin.display(description='comensales', ordering='party_size')
    def party_label_display(self, obj):
        return obj.party_label

    @admin.display(description='estado', ordering='status')
    def status_badge(self, obj):
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:999px;'
            'font-size:11px;white-space:nowrap">{}</span>',
            STATUS_COLORS.get(obj.status, '#6B7280'), obj.get_status_display(),
        )

    def save_model(self, request, obj, form, change):
        # Asignación automática de zona si el equipo no la indica.
        if obj.area_id is None and obj.is_active:
            obj.shift = Shift.for_time(obj.time) or obj._closest_shift()
            candidates = services.candidate_areas(obj.party_size, obj.zone_preference, online_only=False)
            obj.area = services.find_area(
                obj.date, obj.shift, obj.party_size, obj.zone_preference,
                areas=candidates, exclude_pk=obj.pk,
            )
            if obj.area is None:
                messages.warning(request, 'No hay plazas libres: la reserva se ha guardado sin zona asignada.')
        super().save_model(request, obj, form, change)

    # --- Acciones masivas -------------------------------------------------
    def _set_status(self, request, queryset, status):
        updated = queryset.update(status=status)
        self.message_user(request, f'{updated} reserva(s) actualizada(s).', messages.SUCCESS)

    @admin.action(description='Marcar como confirmadas')
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, Reservation.Status.CONFIRMED)

    @admin.action(description='Marcar como completadas')
    def mark_seated(self, request, queryset):
        self._set_status(request, queryset, Reservation.Status.SEATED)

    @admin.action(description='Cancelar reservas')
    def mark_cancelled(self, request, queryset):
        self._set_status(request, queryset, Reservation.Status.CANCELLED)

    @admin.action(description='Marcar como no presentado')
    def mark_no_show(self, request, queryset):
        self._set_status(request, queryset, Reservation.Status.NO_SHOW)

    # --- Vista de ocupación ----------------------------------------------
    def get_urls(self):
        custom = [
            path(
                'ocupacion/', self.admin_site.admin_view(self.occupancy_view),
                name='reservations_reservation_occupancy',
            ),
        ]
        return custom + super().get_urls()

    def occupancy_view(self, request):
        """Panel de ocupación por día, turno y zona para los próximos días."""
        try:
            days = max(1, min(int(request.GET.get('dias', 14)), 60))
        except ValueError:
            days = 14
        start = timezone.localdate()
        areas = list(SeatingArea.objects.active())
        rows = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            shifts = []
            for shift in Shift:
                occ = services.occupancy(day, shift, areas)
                booked = sum(o.booked for o in occ)
                capacity = sum(o.capacity for o in occ)
                shifts.append({
                    'shift': shift,
                    'areas': occ,
                    'booked': booked,
                    'capacity': capacity,
                    'percent': round(booked * 100 / capacity) if capacity else 0,
                    'full': capacity and booked >= capacity,
                })
            rows.append({'date': day, 'shifts': shifts})

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Ocupación de sala',
            'rows': rows,
            'areas': areas,
            'days': days,
        }
        return TemplateResponse(request, 'admin/reservations/occupancy.html', context)
