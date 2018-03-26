from django.db import models
from django.utils.translation import ugettext_lazy as _

from imagefield.fields import ImageField, PPOIField


class Model(models.Model):
    image = ImageField(
        _('image'),
        upload_to='images',
        width_field='width',
        height_field='height',
        ppoi_field='ppoi',
        formats={
            'thumbnail': ['default', ('crop', (300, 300))],
            'desktop': ['default', ('thumbnail', (300, 225))],
        },

        # Should have no effect, but not hurt either:
        auto_add_fields=True,
    )
    width = models.PositiveIntegerField(
        _('image width'),
        blank=True,
        null=True,
        editable=False,
    )
    height = models.PositiveIntegerField(
        _('image height'),
        blank=True,
        null=True,
        editable=False,
    )
    ppoi = PPOIField(_('primary point of interest'))


class ModelWithOptional(models.Model):
    image = ImageField(
        _('image'),
        upload_to='images',
        blank=True,
        auto_add_fields=True,
    )


class Image(models.Model):
    image = ImageField(
        _('image'),
        upload_to='images',
    )
