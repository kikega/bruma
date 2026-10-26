"""Modelos de La Carta: categorías, platos y alérgenos."""

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
        return self.filter(is_active=True)

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
        help_text='Información secundaria: D.O., formato (copa/botella), peso, unidades…',
    )
    price = models.DecimalField('precio (€)', max_digits=7, decimal_places=2)
    price_unit = models.CharField(
        'unidad de precio', max_length=30, blank=True,
        help_text='Opcional: «/ud», «/kg», «por persona», «botella»…',
    )
    image = models.ImageField(
        'imagen del plato / etiqueta',
        upload_to='carta/%Y/',
        blank=True,
        help_text='Fotografía del plato o etiqueta de la botella de vino.',
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
