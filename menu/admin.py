from django.contrib import admin
from django.utils.html import format_html

from .models import Allergen, Category, Dish


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ('icon_preview', 'name', 'abbreviation', 'code', 'order')
    list_display_links = ('icon_preview', 'name')
    list_editable = ('order',)
    prepopulated_fields = {'code': ('name',)}

    @admin.display(description='icono')
    def icon_preview(self, obj):
        if not obj.image:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="height:28px;width:28px;object-fit:contain">',
            obj.image.url,
        )


class DishInline(admin.TabularInline):
    model = Dish
    extra = 0
    fields = ('name', 'image', 'price', 'price_unit', 'is_signature', 'is_active', 'order')
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active', 'dish_count')
    list_editable = ('order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DishInline]

    @admin.display(description='nº platos')
    def dish_count(self, obj):
        return obj.dishes.count()


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'name', 'category', 'price', 'is_signature', 'is_active', 'order')
    list_display_links = ('thumbnail', 'name')
    list_editable = ('price', 'is_active', 'order')
    list_filter = ('category', 'is_active', 'is_signature', 'allergens')
    search_fields = ('name', 'description')
    filter_horizontal = ('allergens',)
    list_select_related = ('category',)
    readonly_fields = ('preview',)

    @admin.display(description='imagen')
    def thumbnail(self, obj):
        if not obj.image:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="height:44px;width:44px;object-fit:cover;border-radius:6px">',
            obj.image.url,
        )

    @admin.display(description='vista previa')
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return 'Se mostrará tras guardar.'
        return format_html(
            '<img src="{}" alt="" style="max-height:240px;border-radius:8px">', obj.image.url,
        )
