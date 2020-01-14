from __future__ import unicode_literals

from time import sleep

from django.core.files import storage
from django.db import models
from django.utils.translation import gettext_lazy as _

from imagefield.fields import ImageField, PPOIField


class AbstractModel(models.Model):
    image = ImageField(
        _("image"),
        upload_to="images",
        width_field="width",
        height_field="height",
        ppoi_field="ppoi",
        formats={
            "thumb": ["default", ("crop", (300, 300))],
            "desktop": ["default", ("thumbnail", (300, 225))],
        },
        # Should have no effect, but not hurt either:
        auto_add_fields=True,
    )
    width = models.PositiveIntegerField(
        _("image width"), blank=True, null=True, editable=False
    )
    height = models.PositiveIntegerField(
        _("image height"), blank=True, null=True, editable=False
    )
    ppoi = PPOIField(_("primary point of interest"))

    class Meta:
        abstract = True


class Model(AbstractModel):
    pass


class ModelWithOptional(models.Model):
    image = ImageField(_("image"), upload_to="images", blank=True, auto_add_fields=True)


class SlowStorage(storage.FileSystemStorage):
    slow = False

    def _open(self, name, mode="rb"):
        if self.slow:
            sleep(1)
            import traceback

            traceback.print_stack()
        return super()._open(name, mode=mode)

    def _save(self, name, content):
        if self.slow:
            sleep(1)
            import traceback

            traceback.print_stack()
        return super()._save(name, content)


slow_storage = SlowStorage()


class SlowStorageImage(models.Model):
    image = ImageField(
        _("image"),
        upload_to="images",
        auto_add_fields=True,
        storage=slow_storage,
        formats={"thumb": ["default", ("crop", (20, 20))]},
    )


class NullableImage(models.Model):
    image = ImageField(
        _("image"),
        upload_to="images",
        auto_add_fields=True,
        blank=True,
        null=True,
        formats={"thumb": ["default", ("crop", (20, 20))]},
    )
