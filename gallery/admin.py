from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryImage


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'title', 'order', 'is_published', 'created_at')
    list_display_links = ('thumbnail', 'title')
    list_editable = ('order', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('title', 'alt_text', 'caption')
    readonly_fields = ('preview',)
    fields = ('image', 'preview', 'title', 'alt_text', 'caption', 'order', 'is_published')

    @admin.display(description='miniatura')
    def thumbnail(self, obj):
        if not obj.image:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="height:56px;width:84px;object-fit:cover;border-radius:6px">',
            obj.image.url,
        )

    @admin.display(description='vista previa')
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return 'Se mostrará tras guardar.'
        return format_html(
            '<img src="{}" alt="" style="max-height:280px;border-radius:8px">', obj.image.url,
        )
