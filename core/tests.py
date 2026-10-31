import json
import re

from django.test import TestCase, override_settings
from django.urls import reverse


class SeoAndJsonLdTests(TestCase):
    def test_home_contains_professional_seo_and_valid_json_ld(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        # Dominio canónico y metadatos esenciales
        self.assertIn('https://brumarestaurant.es/', html)
        self.assertIn('<link rel="canonical" href="https://brumarestaurant.es/">', html)
        self.assertIn('property="og:type" content="restaurant"', html)
        self.assertIn('name="twitter:card" content="summary_large_image"', html)

        # Variables de contexto SEO y reservas
        self.assertTrue(response.context['accepts_reservations'])
        self.assertTrue(response.context['aceptar_reservas'])
        self.assertEqual(response.context['restaurant']['domain'], 'brumarestaurant.es')

        # Extracción y validación estricta del bloque JSON-LD
        match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'Debe existir un bloque <script type="application/ld+json">')
        data = json.loads(match.group(1))

        self.assertEqual(data['@context'], 'https://schema.org')
        self.assertEqual(data['@type'], 'Restaurant')
        self.assertEqual(data['url'], 'https://brumarestaurant.es/')
        self.assertIs(data['acceptsReservations'], True)
        self.assertIn('Cocina mediterránea', data['servesCuisine'])
        self.assertIn('Alta cocina', data['servesCuisine'])
        self.assertTrue(len(data['openingHours']) >= 2)
        self.assertTrue(len(data['openingHoursSpecification']) >= 2)

    def test_robots_txt_and_sitemap_xml(self):
        robots = self.client.get(reverse('core:robots_txt'))
        self.assertEqual(robots.status_code, 200)
        self.assertIn('Sitemap: https://brumarestaurant.es/sitemap.xml', robots.content.decode('utf-8'))

        sitemap = self.client.get(reverse('core:sitemap_xml'))
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn('<loc>https://brumarestaurant.es/</loc>', sitemap.content.decode('utf-8'))

    def test_hero_title_uses_logo_by_default_and_can_revert_to_text(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'class="hero-title-logo"')
        self.assertContains(response, 'img/brumalogo.webp')

        with override_settings(BRUMA_HERO_USE_LOGO=False):
            response_text = self.client.get(reverse('core:home'))
            self.assertNotContains(response_text, 'class="hero-title-logo"')
            self.assertContains(response_text, 'Donde el mar <em class="font-normal text-mediterraneo">se vuelve</em> bruma')
