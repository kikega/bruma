from decimal import Decimal

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from .models import Allergen, Category, Dish, Wine


class CategoryMenuPopupTests(TestCase):
    def _create_dishes(self, category, count, *, with_image=False):
        for i in range(1, count + 1):
            dish = Dish.objects.create(
                category=category,
                name=f'{category.name} Plato {i}',
                description=f'Descripción {i}',
                price=Decimal('15.00'),
                order=i,
            )
            if with_image:
                dish.image.save(
                    f'test-{category.slug}-{i}.svg',
                    ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
                    save=True,
                )

    def _create_wines(self, wine_type, count, *, with_image=False):
        for i in range(1, count + 1):
            wine = Wine.objects.create(
                name=f'Vino {wine_type} {i}',
                wine_type=wine_type,
                wine_region='D.O. Rías Baixas',
                varietal='100 % Albariño',
                description=f'Descripción del vino {i}',
                tasting_notes=f'Notas salinas y cítricas {i}',
                price=Decimal('32.00'),
                price_unit='Botella',
                order=i,
            )
            if with_image:
                wine.image.save(
                    f'test-wine-{wine_type}-{i}.svg',
                    ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
                    save=True,
                )

    def test_category_without_intro_limits_at_6_dishes(self):
        cat_exact = Category.objects.create(name='Crudos', slug='crudos', intro='', order=1)
        self._create_dishes(cat_exact, 6)

        cat_overflow = Category.objects.create(name='Mariscos', slug='mariscos', intro='', order=2)
        self._create_dishes(cat_overflow, 8)

        categories = {c.slug: c for c in Category.objects.with_active_dishes()}

        self.assertEqual(categories['crudos'].landing_limit, 6)
        self.assertFalse(categories['crudos'].has_more_dishes)
        self.assertEqual(len(categories['crudos'].landing_dishes), 6)

        self.assertEqual(categories['mariscos'].landing_limit, 6)
        self.assertTrue(categories['mariscos'].has_more_dishes)
        self.assertEqual(categories['mariscos'].extra_dishes_count, 2)
        self.assertEqual(len(categories['mariscos'].landing_dishes), 6)

    def test_category_with_intro_limits_at_4_dishes(self):
        cat_intro = Category.objects.create(
            name='Entrantes de Lonja',
            slug='entrantes-de-lonja',
            intro='Párrafo introductorio sobre nuestra lonja.',
            order=1,
        )
        self._create_dishes(cat_intro, 5)

        category = Category.objects.with_active_dishes().get(slug='entrantes-de-lonja')
        self.assertEqual(category.landing_limit, 4)
        self.assertTrue(category.has_more_dishes)
        self.assertEqual(category.extra_dishes_count, 1)
        self.assertEqual(len(category.landing_dishes), 4)

    def test_landing_renders_popup_button_and_dialog_only_when_overflowing(self):
        cat_short = Category.objects.create(name='Postres', slug='postres', intro='', order=1)
        self._create_dishes(cat_short, 4)

        cat_long = Category.objects.create(
            name='Arroces',
            slug='arroces',
            intro='Selección de arroces al momento.',
            order=2,
        )
        self._create_dishes(cat_long, 6)

        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, 'id="menu-modal-postres"')
        self.assertContains(response, 'id="menu-modal-arroces"')
        self.assertContains(response, 'Ver carta completa de Arroces')
        self.assertContains(response, 'Arroces Plato 5')
        self.assertContains(response, 'Arroces Plato 6')

    def test_cellar_section_separates_wines_by_type_with_all_fields_and_preview(self):
        self._create_wines(Wine.WineType.WHITE, 7, with_image=True)
        self._create_wines(Wine.WineType.RED, 2, with_image=True)

        groups = {g['slug']: g for g in Wine.objects.grouped_by_type()}
        self.assertIn(Wine.WineType.WHITE, groups)
        self.assertIn(Wine.WineType.RED, groups)
        self.assertTrue(groups[Wine.WineType.WHITE]['has_more_wines'])
        self.assertEqual(groups[Wine.WineType.WHITE]['extra_wines_count'], 1)
        self.assertFalse(groups[Wine.WineType.RED]['has_more_wines'])

        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="bodega"')
        self.assertContains(response, 'id="tab-wine-blanco"')
        self.assertContains(response, 'id="tab-wine-tinto"')
        self.assertContains(response, 'D.O. Rías Baixas')
        self.assertContains(response, '100 % Albariño')
        self.assertContains(response, 'Notas salinas y cítricas 1')
        self.assertContains(response, 'id="dish-floating-preview"')
        self.assertContains(response, 'data-dish-kind="wine"')
        self.assertContains(response, 'data-dish-description=')
        self.assertContains(response, 'data-dish-preview-description')
        self.assertContains(response, 'Ver botella o etiqueta de Vino blanco 1')
        self.assertContains(response, 'id="wine-modal-blanco"')
        self.assertContains(response, 'id="wine-modal-tinto"')
        self.assertNotContains(response, 'id="wine-modal-all"')
        self.assertContains(response, 'Ver todos los vinos de la bodega')

    def test_allergen_png_image_renders_in_dish_and_legend(self):
        allergen = Allergen.objects.create(code='pescado', name='Pescado', abbreviation='PE', order=1)
        allergen.image.save('alergeno-pescado.png', ContentFile(b'\x89PNG\r\n\x1a\n'), save=True)

        cat = Category.objects.create(name='Pescados', slug='pescados', order=1)
        dish = Dish.objects.create(category=cat, name='Lubina salvaje', price=Decimal('32.00'), order=1)
        dish.allergens.add(allergen)

        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, allergen.image.url)

