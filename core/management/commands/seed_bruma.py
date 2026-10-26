"""Carga datos iniciales realistas de Bruma (idempotente).

Uso:  uv run python manage.py seed_bruma [--reset-menu]
"""

from decimal import Decimal
import io
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, ImageDraw

from gallery.models import GalleryImage
from menu.models import Allergen, Category, Dish, Wine
from reservations.models import SeatingArea

ALLERGENS = [
    ('gluten', 'Gluten', 'GL'), ('crustaceos', 'Crustáceos', 'CR'), ('huevos', 'Huevos', 'HU'),
    ('pescado', 'Pescado', 'PE'), ('cacahuetes', 'Cacahuetes', 'CA'), ('soja', 'Soja', 'SO'),
    ('lacteos', 'Lácteos', 'LA'), ('frutos-cascara', 'Frutos de cáscara', 'FC'), ('apio', 'Apio', 'AP'),
    ('mostaza', 'Mostaza', 'MS'), ('sesamo', 'Sésamo', 'SE'), ('sulfitos', 'Sulfitos', 'SU'),
    ('altramuces', 'Altramuces', 'AL'), ('moluscos', 'Moluscos', 'ML'),
]

LONJA_INTRO = """En Bruma, nuestra sección de lonja es el corazón de nuestra propuesta gastronómica, donde seleccionamos diariamente el mejor pescado y marisco fresco, directamente de las lonjas locales. Esta conexión directa con el mar nos permite ofrecer ingredientes que reflejan la esencia y riqueza del Mediterráneo en cada plato.

Cada producto que llega a nuestra cocina es cuidadosamente elegido para garantizar frescura, sabor y calidad excepcionales. Nuestro compromiso con la sostenibilidad y el respeto por las tradiciones pesqueras locales nos permite crear recetas que honran el sabor auténtico del mar.

En Bruma, la lonja no es solo una sección, es la promesa de una experiencia gastronómica única, que conecta a nuestros comensales con la frescura y pureza del mar en cada bocado."""

BODEGA_INTRO = """En Bruma, nuestra bodega es un homenaje al arte del vino, seleccionada con esmero para complementar y realzar cada plato de nuestra cocina gourmet. Contamos con una cuidada colección de etiquetas nacionales e internacionales, que abarca desde vinos clásicos hasta joyas únicas, ideales para maridar y vivir una experiencia sensorial completa. Nuestro equipo está siempre dispuesto a guiar y recomendar la opción perfecta para cada gusto y ocasión, haciendo que cada copa en Bruma sea el cierre ideal para una experiencia inolvidable."""

# (slug, nombre, subtítulo, intro, [(nombre, descripción, detalle, precio, unidad, alérgenos, autor)])
MENU = [
    ('crudos-y-bruma', 'Crudos y Bruma', 'El mar en su estado más puro', '', [
        ('Ostra Gillardeau nº2', 'Yodada y carnosa, con granizado de pepino, lima kaffir y perlas de manzana verde.', '', '6.50', '/ud', ['moluscos', 'sulfitos'], False),
        ('Carpaccio de gamba roja de Dénia', 'Láminas translúcidas, aceite de sus cabezas, cítricos y flor de sal de Santa Pola.', '', '28.00', '', ['crustaceos'], True),
        ('Ceviche mediterráneo de corvina', 'Leche de tigre de tomate valenciano, hinojo encurtido y aceite de albahaca.', '', '22.00', '', ['pescado', 'apio'], False),
        ('Tartar de atún rojo de almadraba', 'Ajoblanco de almendra marcona, yema curada y crujiente de alga nori.', '', '26.00', '', ['pescado', 'frutos-cascara', 'huevos', 'soja', 'sesamo'], False),
        ('Quisquilla de Motril', 'Cocida al momento en agua de mar, servida tibia con sal de humo.', '100 g', '24.00', '', ['crustaceos'], False),
    ]),
    ('entrantes-de-lonja', 'Entrantes de Lonja', 'Selección diaria de la lonja local', LONJA_INTRO, [
        ('Pulpo a la brasa de sarmiento', 'Patata ahumada, pimentón de la Vera y emulsión de su propio jugo.', '', '24.00', '', ['moluscos', 'sulfitos'], True),
        ('Sepia de trasmallo a la plancha', 'Con su tinta, all i oli de ajo negro y brotes de la huerta.', '', '19.00', '', ['moluscos', 'huevos'], False),
        ('Buñuelos de bacalao y algas', 'Esponjosos y salinos, con mayonesa cítrica de yuzu.', '6 uds', '14.00', '', ['pescado', 'gluten', 'huevos', 'lacteos'], False),
        ('Verduras de la huerta a la llama', 'Alcachofa, espárrago y cebolla tierna con romesco de avellana.', '', '16.00', '', ['frutos-cascara', 'gluten', 'sulfitos'], False),
        ('Clóchinas al vapor de hierbas', 'Mejillón valenciano de temporada con limón asado y laurel.', '', '15.00', '', ['moluscos'], False),
    ]),
    ('arroces-y-calderetas', 'Arroces y Calderetas', 'Cocinados al momento · mínimo 2 personas', '', [
        ('Arroz a banda', 'Fumet de roca tostado, sepia y all i oli suave de ajo asado.', '', '24.00', 'por persona', ['pescado', 'moluscos', 'crustaceos', 'huevos', 'apio'], False),
        ('Meloso de bogavante azul', 'Cremoso, intenso y marino, terminado con coral y estragón.', '', '38.00', 'por persona', ['crustaceos', 'pescado', 'apio', 'lacteos'], True),
        ('Arroz negro de calamar de potera', 'Tinta fresca, calamar en dos texturas y alioli de limón.', '', '25.00', 'por persona', ['moluscos', 'pescado', 'huevos'], False),
        ('Caldereta de langosta', 'Guiso tradicional menorquín con sopas de pan payés.', '', '62.00', 'por persona', ['crustaceos', 'gluten', 'apio', 'sulfitos'], False),
    ]),
    ('pescados-de-costera', 'Pescados de Costera', 'Pesca salvaje según disponibilidad', '', [
        ('Lubina salvaje a la sal', 'Horneada entera en costra de sal marina y hierbas, con aceite de olivo arbequina.', 'Para 2', '78.00', '', ['pescado'], True),
        ('Rodaballo salvaje a la brasa', 'Pil-pil de sus pieles, ajos tiernos y patata nueva.', '', '36.00', '', ['pescado'], False),
        ('Lomo de dentón', 'Velouté de azafrán de La Mancha, mejillón y hinojo marino.', '', '32.00', '', ['pescado', 'moluscos', 'lacteos', 'sulfitos'], False),
        ('Salmonete de roca', 'Escamas crujientes, suquet ligero de patata y alioli de azafrán.', '', '29.00', '', ['pescado', 'huevos', 'crustaceos'], False),
    ]),
    ('postres-de-sal-y-citricos', 'Postres de Sal y Cítricos', 'Final fresco, salino y luminoso', '', [
        ('Sorbete de limón y albahaca', 'Limón de Murcia, albahaca fresca y espuma de cava brut nature.', '', '9.00', '', ['sulfitos'], False),
        ('Texturas de almendra', 'Helado de turrón, bizcocho aireado, praliné y leche de almendra salada.', '', '11.00', '', ['frutos-cascara', 'lacteos', 'huevos', 'gluten'], True),
        ('Naranja, aceite y sal', 'Cremoso de naranja sanguina, crumble de aceite de oliva y escamas de sal.', '', '10.00', '', ['lacteos', 'huevos', 'gluten'], False),
        ('Quesos artesanos del Mediterráneo', 'Selección de tres quesos con membrillo de higo y picos de aceite.', '', '16.00', '', ['lacteos', 'gluten', 'frutos-cascara'], False),
    ]),
]

# (nombre, tipo_vino, zona_vinicola, varietal, descripción, notas_de_cata, precio, unidad_precio, alérgenos, selección_sumiller)
WINES = [
    (
        'Albariño «Pazo Señorans»',
        Wine.WineType.WHITE,
        'D.O. Rías Baixas',
        '100 % Albariño',
        'Blanco atlántico criado sobre lías en acero inoxidable, procedente de viñedos históricos del Valle del Salnés.',
        'Intenso y floral en nariz con fruta de hueso blanca y cítricos; boca salina, vibrante y de final mineral persistente.',
        '34.00',
        'Botella',
        ['sulfitos'],
        True,
    ),
    (
        'Malvasía de Sitges «Aiguadolç»',
        Wine.WineType.WHITE,
        'D.O. Penedès',
        '100 % Malvasía de Sitges',
        'Blanco mediterráneo de viñas costeras acariciadas por la brisa marina del macizo del Garraf.',
        'Aromático y envolvente, con notas de flor de azahar, melocotón blanco y un recuerdo yodado ideal para crudos y ostras.',
        '29.00',
        'Botella',
        ['sulfitos'],
        False,
    ),
    (
        'Merseguera «El Sequé»',
        Wine.WineType.WHITE,
        'D.O. Alicante',
        '100 % Merseguera',
        'Variedad autóctona levantina cultivada en secano sobre suelos calcáreos y arenosos.',
        'Hierbas de monte bajo, hinojo fresco, almendra tierna y cítricos maduros; paso seco, equilibrado y refrescante.',
        '7.50',
        'Copa / Botella',
        ['sulfitos'],
        False,
    ),
    (
        'Godello «Louro do Bolo»',
        Wine.WineType.WHITE,
        'D.O. Valdeorras',
        'Godello y Treixadura',
        'Fermentado con sus lías en fudres de roble francés de laderas graníticas de alta montaña.',
        'Fruta blanca madura, hinojo silvestre y sutiles notas tostadas; entrada amplia, cremosa y gran tensión ácida.',
        '36.00',
        'Botella',
        ['sulfitos'],
        False,
    ),
    (
        'Garnacha «Les Terrasses»',
        Wine.WineType.RED,
        'D.O.Q. Priorat',
        'Garnacha Negra y Cariñena',
        'Tinto de laderas escarpadas de pizarra licorella trabajadas de forma tradicional.',
        'Fruta roja silvestre, violetas y grafito mineral; tanino sedoso, buena acidez y un fondo balsámico largo.',
        '48.00',
        'Botella',
        ['sulfitos'],
        True,
    ),
    (
        'Giró «Parotet»',
        Wine.WineType.RED,
        'D.O. Alicante',
        'Giró y Mandó',
        'Tinto mediterráneo criado en ánfora de barro, fresco y ligero, ideal para pescados a la brasa y arroces.',
        'Granada, cereza crujiente, monte mediterráneo y pimienta rosa; paso fluido, jugoso y muy gastronómico.',
        '35.00',
        'Botella',
        ['sulfitos'],
        False,
    ),
    (
        'Cava Gran Reserva Brut Nature',
        Wine.WineType.SPARKLING,
        'D.O. Cava',
        'Xarel·lo, Macabeo y Parellada',
        'Espumoso de larga crianza en rima superior a 48 meses sin adición de licor de expedición.',
        'Burbuja finísima e integrada, notas de manzana asada, brioche, frutos secos tostados y final seco y salino.',
        '42.00',
        'Botella',
        ['sulfitos'],
        True,
    ),
    (
        'Champagne Blanc de Blancs',
        Wine.WineType.SPARKLING,
        'A.O.C. Champagne',
        '100 % Chardonnay',
        'Cuvée parcelaria de suelos calcáreos de la Côte des Blancs con crianza prolongada sobre lías.',
        'Tiza húmeda, corteza de limón confitado, flores blancas y avellana; vertical, vibrante y de elegancia cristalina.',
        '95.00',
        'Botella',
        ['sulfitos'],
        False,
    ),
    (
        'Rosado de Lágrima «Casta Diva»',
        Wine.WineType.ROSE,
        'D.O. Alicante',
        'Monastrell y Garnacha',
        'Rosado pálido obtenido por sangrado directo de viñedos próximos a la costa alicantina.',
        'Pétalos de rosa, pomelo rosado y fresa blanca; boca fresca, sedosa y con sutil salinidad final.',
        '27.00',
        'Botella',
        ['sulfitos'],
        False,
    ),
]

AREAS = [
    # nombre, tipo, zona, capacidad (comensales/turno), máx por reserva, prioridad
    ('Mesa · Salón Interior', SeatingArea.Kind.TABLE, SeatingArea.Zone.INTERIOR, 40, 10, 10),
    ('Mesa · Terraza Bruma', SeatingArea.Kind.TABLE, SeatingArea.Zone.TERRACE, 28, 8, 20),
    ('Barra', SeatingArea.Kind.BAR, SeatingArea.Zone.INTERIOR, 8, 2, 30),
]

GALLERY_SEED_DIR = Path(settings.BASE_DIR) / 'static' / 'img' / 'gallery-seed'
STATIC_IMG_DIR = Path(settings.BASE_DIR) / 'static' / 'img'

CATEGORY_SEED_IMAGES = {
    'crudos-y-bruma': [
        GALLERY_SEED_DIR / 'galeria-ostras.webp',
        STATIC_IMG_DIR / 'identidad-plato.webp',
        STATIC_IMG_DIR / 'identidad-lonja.webp',
    ],
    'entrantes-de-lonja': [
        STATIC_IMG_DIR / 'identidad-lonja.webp',
        STATIC_IMG_DIR / 'identidad-plato.webp',
        GALLERY_SEED_DIR / 'galeria-ostras.webp',
    ],
    'arroces-y-calderetas': [
        GALLERY_SEED_DIR / 'galeria-arroz.webp',
        STATIC_IMG_DIR / 'identidad-plato.webp',
    ],
    'pescados-de-costera': [
        STATIC_IMG_DIR / 'identidad-plato.webp',
        STATIC_IMG_DIR / 'identidad-lonja.webp',
    ],
    'postres-de-sal-y-citricos': [
        GALLERY_SEED_DIR / 'galeria-postre.webp',
    ],
}
GALLERY = [
    ('galeria-salon', 'Salón interior', 'Comedor de Bruma con mesas vestidas de lino frente a grandes ventanales al mar en calma.'),
    ('galeria-ostras', 'Ostras del día', 'Ostras frescas sobre hielo picado con limón y sal marina.'),
    ('galeria-arroz', 'Arroz a banda', 'Arroz a banda en paella fina con all i oli, visto desde arriba.'),
    ('galeria-terraza', 'Terraza Bruma', 'Terraza junto al mar al atardecer con mesas preparadas y bruma ligera.'),
    ('galeria-postre', 'Sorbete de limón y albahaca', 'Quenelle de sorbete de limón y albahaca con texturas de almendra.'),
    ('galeria-vino', 'Blancos salinos', 'Dos copas de vino blanco con el mar desenfocado al fondo.'),
]


class Command(BaseCommand):
    help = 'Carga alérgenos, carta, zonas de sala y galería de ejemplo para Bruma.'

    def add_arguments(self, parser):
        parser.add_argument('--reset-menu', action='store_true', help='Borra y recrea los platos de la carta.')

    @transaction.atomic
    def handle(self, *args, reset_menu=False, **options):
        allergens = self._seed_allergens()
        self._seed_menu(allergens, reset=reset_menu)
        self._seed_wines(allergens, reset=reset_menu)
        self._seed_areas()
        self._seed_gallery()
        self.stdout.write(self.style.SUCCESS('Datos de Bruma cargados correctamente.'))

    def _seed_allergens(self):
        result = {}
        for order, (code, name, abbr) in enumerate(ALLERGENS):
            obj, _ = Allergen.objects.update_or_create(
                code=code, defaults={'name': name, 'abbreviation': abbr, 'order': order},
            )
            if not obj.image:
                png_bytes = self._build_allergen_png(code)
                obj.image.save(f'alergeno-{code}.png', ContentFile(png_bytes), save=True)
            result[code] = obj
        self.stdout.write(f'  · {len(result)} alérgenos')
        return result

    @staticmethod
    def _build_allergen_png(code):
        """Genera un icono PNG (128x128 con supersampling 2x) para cada uno de los 14 alérgenos."""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        palettes = {
            'gluten': ((217, 155, 67, 255), (253, 246, 233, 255)),
            'crustaceos': ((209, 84, 66, 255), (253, 239, 236, 255)),
            'huevos': ((224, 169, 62, 255), (254, 248, 234, 255)),
            'pescado': ((30, 78, 104, 255), (235, 244, 248, 255)),
            'cacahuetes': ((166, 112, 65, 255), (249, 241, 234, 255)),
            'soja': ((94, 138, 97, 255), (238, 246, 239, 255)),
            'lacteos': ((72, 126, 168, 255), (237, 245, 251, 255)),
            'frutos-cascara': ((143, 94, 62, 255), (247, 239, 234, 255)),
            'apio': ((82, 148, 95, 255), (236, 247, 238, 255)),
            'mostaza': ((199, 152, 38, 255), (252, 246, 230, 255)),
            'sesamo': ((158, 134, 94, 255), (247, 244, 237, 255)),
            'sulfitos': ((134, 68, 112, 255), (246, 236, 243, 255)),
            'altramuces': ((212, 148, 42, 255), (253, 245, 231, 255)),
            'moluscos': ((46, 107, 138, 255), (235, 244, 248, 255)),
        }
        fg, bg = palettes.get(code, ((94, 113, 106, 255), (242, 245, 243, 255)))

        # Círculo base y borde
        draw.ellipse((12, 12, size - 12, size - 12), fill=bg, outline=fg, width=10)

        if code == 'gluten':
            draw.line((128, 196, 128, 64), fill=fg, width=10)
            for y in (156, 124, 92):
                draw.ellipse((88, y - 18, 124, y + 6), fill=fg)
                draw.ellipse((132, y - 18, 168, y + 6), fill=fg)
            draw.ellipse((114, 52, 142, 82), fill=fg)
        elif code == 'crustaceos':
            draw.ellipse((78, 92, 178, 182), fill=fg)
            draw.arc((54, 52, 120, 122), start=140, end=340, fill=fg, width=12)
            draw.arc((136, 52, 202, 122), start=200, end=40, fill=fg, width=12)
            for y in (122, 148, 172):
                draw.line((52, y, 82, y - 8), fill=fg, width=8)
                draw.line((174, y - 8, 204, y), fill=fg, width=8)
        elif code == 'huevos':
            draw.ellipse((80, 62, 176, 196), outline=fg, width=10)
            draw.ellipse((104, 118, 152, 166), fill=fg)
        elif code == 'pescado':
            draw.ellipse((60, 92, 168, 164), fill=fg)
            draw.polygon([(158, 128), (202, 92), (202, 164)], fill=fg)
            draw.ellipse((80, 116, 96, 132), fill=bg)
        elif code == 'cacahuetes':
            draw.ellipse((86, 62, 170, 134), fill=fg)
            draw.ellipse((82, 118, 174, 196), fill=fg)
            draw.ellipse((104, 80, 152, 118), fill=bg)
            draw.ellipse((102, 136, 154, 178), fill=bg)
        elif code == 'soja':
            draw.rounded_rectangle((74, 88, 182, 168), radius=40, outline=fg, width=10)
            for x in (100, 128, 156):
                draw.ellipse((x - 12, 116, x + 12, 140), fill=fg)
        elif code == 'lacteos':
            draw.polygon([(98, 66), (158, 66), (172, 104), (172, 192), (84, 192), (84, 104)], outline=fg, width=10)
            draw.rectangle((94, 54, 162, 70), fill=fg)
            draw.rectangle((94, 136, 162, 182), fill=fg)
        elif code == 'frutos-cascara':
            draw.chord((76, 84, 180, 196), start=0, end=180, fill=fg)
            draw.rounded_rectangle((72, 78, 184, 116), radius=16, outline=fg, width=10, fill=bg)
            draw.line((128, 56, 128, 78), fill=fg, width=10)
        elif code == 'apio':
            draw.line((128, 192, 128, 76), fill=fg, width=12)
            draw.line((128, 176, 94, 96), fill=fg, width=10)
            draw.line((128, 176, 162, 96), fill=fg, width=10)
            for cx, cy in ((94, 84), (128, 68), (162, 84)):
                draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=fg)
        elif code == 'mostaza':
            draw.rounded_rectangle((84, 96, 172, 192), radius=20, outline=fg, width=10)
            draw.rectangle((96, 72, 160, 96), fill=fg)
            draw.ellipse((108, 126, 148, 166), fill=fg)
        elif code == 'sesamo':
            for cx, cy in ((102, 92), (154, 96), (88, 140), (132, 132), (166, 146), (114, 174), (148, 178)):
                draw.ellipse((cx - 12, cy - 18, cx + 12, cy + 18), fill=fg)
        elif code == 'sulfitos':
            draw.chord((82, 64, 174, 152), start=0, end=180, fill=fg)
            draw.line((82, 108, 174, 108), fill=fg, width=10)
            draw.line((128, 150, 128, 192), fill=fg, width=10)
            draw.line((96, 192, 160, 192), fill=fg, width=10)
        elif code == 'altramuces':
            for angle_offset, (cx, cy) in enumerate(((128, 78), (170, 108), (154, 158), (102, 158), (86, 108))):
                draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=fg)
            draw.ellipse((114, 114, 142, 142), fill=bg)
        elif code == 'moluscos':
            draw.polygon([(128, 186), (68, 112), (96, 76), (128, 68), (160, 76), (188, 112)], fill=fg)
            for x in (96, 116, 136, 156):
                draw.line((128, 182, x, 82), fill=bg, width=5)

        final_img = img.resize((128, 128), resample=Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        final_img.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

    def _seed_menu(self, allergens, *, reset):
        if reset:
            Dish.objects.all().delete()
        # Si quedaba alguna categoría antigua de bodega en Dish/Category, se limpia
        Dish.objects.filter(category__slug='bodega-mediterranea').delete()
        Category.objects.filter(slug='bodega-mediterranea').delete()

        created = 0
        for c_order, (slug, name, tagline, intro, dishes) in enumerate(MENU):
            category, _ = Category.objects.update_or_create(
                slug=slug, defaults={'name': name, 'tagline': tagline, 'intro': intro, 'order': c_order},
            )
            for d_order, (d_name, desc, detail, price, unit, codes, signature) in enumerate(dishes):
                dish, was_created = Dish.objects.update_or_create(
                    category=category, name=d_name,
                    defaults={
                        'description': desc, 'detail': detail, 'price': Decimal(price),
                        'price_unit': unit, 'is_signature': signature, 'order': d_order,
                    },
                )
                dish.allergens.set([allergens[c] for c in codes])
                if not dish.image:
                    self._attach_dish_seed_image(dish, category_slug=slug, index=d_order)
                created += was_created
        self.stdout.write(f'  · carta: {len(MENU)} categorías, {created} platos nuevos')

    def _seed_wines(self, allergens, *, reset):
        if reset:
            Wine.objects.all().delete()
        created = 0
        for w_order, (
            w_name, w_type, w_region, varietal, desc, tasting_notes, price, unit, codes, signature
        ) in enumerate(WINES):
            wine, was_created = Wine.objects.update_or_create(
                name=w_name,
                defaults={
                    'wine_type': w_type,
                    'wine_region': w_region,
                    'varietal': varietal,
                    'description': desc,
                    'tasting_notes': tasting_notes,
                    'price': Decimal(price),
                    'price_unit': unit,
                    'is_signature': signature,
                    'order': w_order,
                },
            )
            wine.allergens.set([allergens[c] for c in codes])
            if not wine.image:
                svg = self._build_wine_label_svg(wine)
                wine.image.save(
                    f'etiqueta-{slugify(wine.name)}.svg',
                    ContentFile(svg.encode('utf-8')),
                    save=True,
                )
            created += was_created
        self.stdout.write(f'  · bodega: {len(WINES)} referencias ({created} vinos nuevos)')

    def _attach_dish_seed_image(self, dish, *, category_slug, index):
        candidates = CATEGORY_SEED_IMAGES.get(category_slug, [])
        if not candidates:
            return
        source = candidates[index % len(candidates)]
        if not source.exists():
            return
        with source.open('rb') as fh:
            dish.image.save(f'plato-{slugify(dish.name)}.webp', File(fh), save=True)

    @staticmethod
    def _build_wine_label_svg(wine):
        title = escape(wine.name)
        region = escape(wine.wine_region or 'Selección Bruma')
        varietal = escape(wine.varietal or '')
        type_label = escape(wine.get_wine_type_display().upper())
        notes_src = wine.tasting_notes or wine.description or ''
        notes = escape(notes_src[:72] + ('…' if len(notes_src) > 72 else ''))
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 800" width="640" height="800">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0F1E2E"/>
      <stop offset="100%" stop-color="#1A324A"/>
    </linearGradient>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#FAF7F0"/>
      <stop offset="100%" stop-color="#EFE8D5"/>
    </linearGradient>
  </defs>
  <rect width="640" height="800" fill="url(#bg)"/>
  <circle cx="320" cy="140" r="220" fill="#C2B280" fill-opacity="0.08"/>
  <rect x="76" y="76" width="488" height="648" rx="18" fill="url(#paper)" stroke="#C2B280" stroke-width="3"/>
  <rect x="96" y="96" width="448" height="608" rx="10" fill="none" stroke="#0F1E2E" stroke-opacity="0.22" stroke-width="1.5"/>
  <text x="320" y="155" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="12" font-weight="600" letter-spacing="5" fill="#5E716A">BRUMA · {type_label}</text>
  <line x1="230" y1="180" x2="410" y2="180" stroke="#C2B280" stroke-width="1.5"/>
  <path d="M295 235 C310 220, 330 220, 345 235 C360 250, 380 250, 395 235" fill="none" stroke="#1E4E68" stroke-width="2" stroke-linecap="round"/>
  <path d="M275 253 C295 238, 315 238, 335 253 C355 268, 375 268, 395 253" fill="none" stroke="#C2B280" stroke-width="1.5" stroke-linecap="round"/>
  <text x="320" y="340" text-anchor="middle" font-family="Cormorant Garamond, Georgia, serif" font-size="33" font-weight="600" fill="#0F1E2E">{title}</text>
  <text x="320" y="390" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="13" font-weight="600" letter-spacing="3" fill="#1E4E68">{region.upper()}</text>
  <text x="320" y="422" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="12" font-weight="500" letter-spacing="1.5" fill="#5E716A">{varietal}</text>
  <line x1="260" y1="452" x2="380" y2="452" stroke="#C2B280" stroke-width="1"/>
  <text x="320" y="505" text-anchor="middle" font-family="Cormorant Garamond, Georgia, serif" font-style="italic" font-size="20" fill="#2B343B">{notes}</text>
  <rect x="245" y="585" width="150" height="44" rx="22" fill="#0F1E2E"/>
  <text x="320" y="613" text-anchor="middle" font-family="Cormorant Garamond, Georgia, serif" font-size="22" font-weight="600" fill="#FAF7F0">{wine.price:.2f} €</text>
  <text x="320" y="675" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="10" letter-spacing="4" fill="#5E716A">COSECHA SELECCIONADA · SERVICIO EN SALA</text>
</svg>"""

    def _seed_areas(self):
        for name, kind, zone, capacity, max_party, order in AREAS:
            SeatingArea.objects.get_or_create(
                name=name,
                defaults={'kind': kind, 'zone': zone, 'capacity': capacity,
                          'max_party_size': max_party, 'order': order},
            )
        self.stdout.write(f'  · {len(AREAS)} zonas de sala')

    def _seed_gallery(self):
        if GalleryImage.objects.exists():
            self.stdout.write('  · galería ya tiene imágenes, se omite')
            return
        added = 0
        for order, (stem, title, alt) in enumerate(GALLERY):
            source = GALLERY_SEED_DIR / f'{stem}.webp'
            if not source.exists():
                continue
            with source.open('rb') as fh:
                item = GalleryImage(title=title, alt_text=alt, order=order)
                item.image.save(source.name, File(fh), save=True)
            added += 1
        self.stdout.write(f'  · galería: {added} imágenes')
