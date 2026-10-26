"""Modelos de La Carta y La Bodega: categorías, platos, vinos y alérgenos."""

from django.db import models


class Allergen(models.Model):
    """Uno de los 14 alérgenos de declaración obligatoria (Reglamento UE 1169/2011)."""

    code = models.SlugField('código', max_length=20, unique=True)
    name = models.CharField('nombre', max_length=60)
    abbreviation = models.CharField(
        'abreviatura', max_length=3,
        help_text='Texto corto (2-3 letras) que se muestra en el indicador del plato.',
    )
    image = models.ImageField(
        'icono (PNG)',
        upload_to='alergenos/',
        blank=True,
        help_text='Icono PNG del alérgeno que se muestra en cada plato y en la leyenda.',
    )
    order = models.PositiveSmallIntegerField('orden', default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'alérgeno'
        verbose_name_plural = 'alérgenos'

    def __str__(self):
        return self.name


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True).exclude(slug='bodega-mediterranea')

    def with_active_dishes(self):
        """Categorías activas con sus platos activos y alérgenos precargados (sin N+1)."""
        dishes = Dish.objects.active().prefetch_related('allergens')
        return self.active().prefetch_related(models.Prefetch('dishes', queryset=dishes))


class Category(models.Model):
    name = models.CharField('nombre', max_length=80)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(
        'subtítulo', max_length=140, blank=True,
        help_text='Frase breve bajo el nombre de la categoría.',
    )
    intro = models.TextField(
        'texto introductorio', blank=True,
        help_text='Párrafos opcionales (separados por una línea en blanco).',
    )
    order = models.PositiveSmallIntegerField('orden', default=0)
    is_active = models.BooleanField('activa', default=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.name

    @property
    def intro_paragraphs(self):
        return [p.strip() for p in self.intro.split('\n\n') if p.strip()]

    @property
    def landing_limit(self):
        """Espacio reservado en la landing: 4 platos (2×2) si hay intro, 6 platos (2×3) sin intro."""
        return 4 if self.intro_paragraphs else 6

    @property
    def landing_dishes(self):
        return list(self.dishes.all())[:self.landing_limit]

    @property
    def has_more_dishes(self):
        return len(self.dishes.all()) > self.landing_limit

    @property
    def extra_dishes_count(self):
        return max(0, len(self.dishes.all()) - self.landing_limit)


class DishQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Dish(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='dishes', verbose_name='categoría',
    )
    name = models.CharField('nombre', max_length=120)
    description = models.CharField('descripción sensorial', max_length=280, blank=True)
    detail = models.CharField(
        'detalle', max_length=80, blank=True,
        help_text='Información secundaria: peso, unidades, mínimo de comensales…',
    )
    price = models.DecimalField('precio (€)', max_digits=7, decimal_places=2)
    price_unit = models.CharField(
        'unidad de precio', max_length=30, blank=True,
        help_text='Opcional: «/ud», «/kg», «por persona»…',
    )
    image = models.ImageField(
        'imagen del plato',
        upload_to='carta/%Y/',
        blank=True,
        help_text='Fotografía del plato.',
    )
    allergens = models.ManyToManyField(Allergen, blank=True, related_name='dishes', verbose_name='alérgenos')
    is_signature = models.BooleanField('plato de autor', default=False)
    is_active = models.BooleanField('disponible', default=True)
    order = models.PositiveSmallIntegerField('orden', default=0)

    objects = DishQuerySet.as_manager()

    class Meta:
        ordering = ['category__order', 'order', 'name']
        verbose_name = 'plato'
        verbose_name_plural = 'platos'

    def __str__(self):
        return self.name


class WineQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_allergens(self):
        """Vinos activos con sus alérgenos precargados (sin N+1)."""
        return self.active().prefetch_related('allergens')

    def grouped_by_type(self, *, landing_limit=6):
        """Agrupa los vinos activos por tipo de vino siguiendo el orden editorial de La Bodega."""
        wines = list(self.with_allergens().order_by('order', 'name'))
        by_type = {}
        for wine in wines:
            by_type.setdefault(wine.wine_type, []).append(wine)

        groups = []
        for code, label in Wine.WineType.choices:
            items = by_type.get(code, [])
            if not items:
                continue
            meta = Wine.TYPE_EDITORIAL_META.get(code, {})
            groups.append({
                'slug': code,
                'name': meta.get('plural', str(label)),
                'singular': str(label),
                'tagline': meta.get('tagline', ''),
                'wines': items,
                'landing_wines': items[:landing_limit],
                'has_more_wines': len(items) > landing_limit,
                'extra_wines_count': max(0, len(items) - landing_limit),
            })
        return groups


class Wine(models.Model):
    """Referencia vinícola de La Bodega de Bruma, separada de los platos de La Carta."""

    class WineType(models.TextChoices):
        WHITE = 'blanco', 'Vino Blanco'
        RED = 'tinto', 'Vino Tinto'
        SPARKLING = 'espumoso', 'Espumoso y Champagne'
        ROSE = 'rosado', 'Vino Rosado'
        FORTIFIED = 'generoso', 'Generoso y Dulce'

    TYPE_EDITORIAL_META = {
        WineType.WHITE: {
            'plural': 'Blancos',
            'tagline': 'Blancos salinos, minerales y atlánticos pensados para el mar',
        },
        WineType.RED: {
            'plural': 'Tintos',
            'tagline': 'Tintos mediterráneos de finura, frescura y suelos de pizarra o arcilla',
        },
        WineType.SPARKLING: {
            'plural': 'Espumosos y Champagne',
            'tagline': 'Burbujas finas de larga crianza en rima y terruños calcáreos',
        },
        WineType.ROSE: {
            'plural': 'Rosados',
            'tagline': 'Rosados pálidos de sangrado directo y brisa mediterránea',
        },
        WineType.FORTIFIED: {
            'plural': 'Generosos y Dulces',
            'tagline': 'Vinos de velo de flor, criaderas y vendimias tardías para el cierre perfecto',
        },
    }

    name = models.CharField('nombre', max_length=120)
    wine_type = models.CharField(
        'tipo de vino',
        max_length=20,
        choices=WineType.choices,
        default=WineType.WHITE,
        db_index=True,
    )
    wine_region = models.CharField(
        'zona vinícola',
        max_length=120,
        help_text='Denominación de Origen, apelación o región vinícola (p. ej. D.O. Rías Baixas, A.O.C. Champagne).',
    )
    varietal = models.CharField(
        'varietal',
        max_length=140,
        help_text='Variedad o ensamblaje de uvas (p. ej. 100 % Albariño, Garnacha y Cariñena).',
    )
    description = models.CharField(
        'descripción',
        max_length=280,
        blank=True,
        help_text='Descripción del vino, origen del viñedo o método de elaboración.',
    )
    tasting_notes = models.TextField(
        'notas de cata',
        blank=True,
        help_text='Fase visual, aromas en nariz, paso por boca y final.',
    )
    price = models.DecimalField('precio (€)', max_digits=7, decimal_places=2)
    price_unit = models.CharField(
        'formato / unidad de precio',
        max_length=40,
        default='Botella',
        blank=True,
        help_text='Formato de servicio: «Botella», «Copa / Botella», «Copa»…',
    )
    image = models.ImageField(
        'imagen de botella o etiqueta',
        upload_to='bodega/%Y/',
        blank=True,
        help_text='Fotografía de la botella o imagen de la etiqueta del vino.',
    )
    allergens = models.ManyToManyField(
        Allergen, blank=True, related_name='wines', verbose_name='alérgenos',
    )
    is_signature = models.BooleanField(
        'selección del sumiller',
        default=False,
        help_text='Destaca este vino como recomendación especial de nuestro sumiller.',
    )
    is_active = models.BooleanField('disponible', default=True)
    order = models.PositiveSmallIntegerField('orden', default=0)

    objects = WineQuerySet.as_manager()

    class Meta:
        ordering = ['wine_type', 'order', 'name']
        verbose_name = 'vino'
        verbose_name_plural = 'vinos'

    def __str__(self):
        return f'{self.name} ({self.wine_region})' if self.wine_region else self.name

