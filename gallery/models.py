from django.db import models


class GalleryImageQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class GalleryImage(models.Model):
    image = models.ImageField('imagen', upload_to='galeria/%Y/')
    title = models.CharField('título', max_length=120)
    alt_text = models.CharField(
        'texto alternativo', max_length=200,
        help_text='Descripción de la imagen para lectores de pantalla y SEO.',
    )
    caption = models.CharField('pie de foto', max_length=200, blank=True)
    order = models.PositiveSmallIntegerField('orden', default=0)
    is_published = models.BooleanField('publicada', default=True)
    created_at = models.DateTimeField('creada', auto_now_add=True)

    objects = GalleryImageQuerySet.as_manager()

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'imagen de galería'
        verbose_name_plural = 'galería'

    def __str__(self):
        return self.title
