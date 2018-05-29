import hashlib
import io
import logging
import os

from django.conf import settings
from django.core import checks
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import signals
from django.db.models.fields import files
from django.forms import ClearableFileInput
from django.utils.functional import cached_property

from PIL import Image

from .processing import build_handler
from .widgets import PPOIWidget, with_preview_and_ppoi


try:
    from types import SimpleNamespace
except ImportError:  # pragma: no cover
    # Python < 3.3
    class SimpleNamespace(object):

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


logger = logging.getLogger(__name__)
#: Imagefield instances
IMAGEFIELDS = []


def hashdigest(str):
    return hashlib.sha1(str.encode("utf-8")).hexdigest()


class ImageFieldFile(files.ImageFieldFile):

    def __getattr__(self, item):
        if item in self.field.formats:
            if self.name:
                url = self.storage.url(self._processed_name(self.field.formats[item]))
            else:
                url = ""
            setattr(self, item, url)
            return url
        raise AttributeError

    def _ppoi(self):
        if self.field.ppoi_field:
            return [
                float(coord)
                for coord in getattr(self.instance, self.field.ppoi_field).split("x")
            ]
        return [0.5, 0.5]

    def _processed_base(self, name):
        p1 = hashdigest(name)
        filename, _ = os.path.splitext(os.path.basename(name))
        return "__processed__/%s" % p1[:3], "%s-" % filename

    def _processed_name(self, processors):
        path, basename = self._processed_base(self.name)
        p2 = hashdigest("|".join(str(p) for p in processors) + "|" + str(self._ppoi()))
        _, ext = os.path.splitext(self.name)
        return "%s/%s%s%s" % (path, basename, p2[:12], ext)

    def process(self, item, force=False):
        if isinstance(item, (list, tuple)):
            processors = item
            item = "<ad hoc>"
        else:
            processors = self.field.formats[item]
        target = self._processed_name(processors)
        logger.debug(
            'Processing image %(image)s as "%(key)s" with target %(target)s'
            " and pipeline %(processors)s, PPOI %(ppoi)s",
            {
                "image": self,
                "key": item,
                "target": target,
                "processors": processors,
                "ppoi": self._ppoi(),
            },
        )
        if not force and self.storage.exists(target):
            return target

        try:
            buf = self._process(processors)
        except Exception:
            logger.exception("Exception while processing")
            raise

        self.storage.delete(target)
        self.storage.save(target, ContentFile(buf))

        logger.info("Saved processed image %(target)s", {"target": target})
        return target

    def _process(self, processors):
        self.open("rb")
        image = Image.open(self.file)
        context = SimpleNamespace(ppoi=self._ppoi(), save_kwargs={})
        format = image.format
        _, ext = os.path.splitext(self.name)

        handler = build_handler(processors)
        image, context = handler(image, context)

        with io.BytesIO() as buf:
            image.save(buf, format=format, **context.save_kwargs)
            return buf.getvalue()


class ImageField(models.ImageField):
    attr_class = ImageFieldFile

    def __init__(self, verbose_name=None, **kwargs):
        self._auto_add_fields = kwargs.pop("auto_add_fields", False)
        self._formats = kwargs.pop("formats", {})
        self.ppoi_field = kwargs.pop("ppoi_field", None)
        super(ImageField, self).__init__(verbose_name, **kwargs)

    @cached_property
    def field_label(self):
        return ("%s.%s" % (self.model._meta.label_lower, self.name)).lower()

    @cached_property
    def formats(self):
        setting = getattr(settings, "IMAGEFIELD_FORMATS", {})
        return setting.get(self.field_label, self._formats)

    def contribute_to_class(self, cls, name, **kwargs):
        if self._auto_add_fields:
            if self.width_field is None:
                self.width_field = "%s_width" % name
                models.PositiveIntegerField(
                    blank=True, null=True, editable=False
                ).contribute_to_class(cls, self.width_field)
            if self.height_field is None:
                self.height_field = "%s_height" % name
                models.PositiveIntegerField(
                    blank=True, null=True, editable=False
                ).contribute_to_class(cls, self.height_field)
            if self.ppoi_field is None:
                self.ppoi_field = "%s_ppoi" % name
                PPOIField().contribute_to_class(cls, self.ppoi_field)

        super(ImageField, self).contribute_to_class(cls, name, **kwargs)

        if not cls._meta.abstract:
            IMAGEFIELDS.append(self)

            signals.post_init.connect(self._cache_previous, sender=cls)

            autogenerate = getattr(settings, "IMAGEFIELD_AUTOGENERATE", True)
            if autogenerate is True or self.field_label in autogenerate:
                signals.post_save.connect(self._generate_files, sender=cls)
                signals.post_delete.connect(self._clear_generated_files, sender=cls)

    def formfield(self, **kwargs):
        kwargs["widget"] = with_preview_and_ppoi(
            kwargs.get("widget", ClearableFileInput), ppoi_field=self.ppoi_field
        )
        return super(ImageField, self).formfield(**kwargs)

    def save_form_data(self, instance, data):
        super(ImageField, self).save_form_data(instance, data)

        if data is not None:
            f = getattr(instance, self.name)
            if f.name:
                try:
                    # Anything which exercises the machinery so that we may
                    # find out whether the image works at all (or not)
                    f._process(["default", ("thumbnail", (20, 20))])
                except Exception as exc:
                    raise ValidationError(str(exc))

            # Reset PPOI field if image field is cleared
            if not data and self.ppoi_field:
                setattr(instance, self.ppoi_field, "0.5x0.5")

    def _cache_previous(self, instance, **kwargs):
        f = getattr(instance, self.name)
        setattr(instance, "_previous_%s" % self.name, (f.name, f._ppoi()))

    def _generate_files(self, instance, **kwargs):
        # Set by the process_imagefields management command
        if getattr(instance, "_skip_generate_files", False):
            return

        f = getattr(instance, self.name)

        previous = getattr(instance, "_previous_%s" % self.name, None)
        # TODO This will not detect replaced/overwritten files.
        if previous and previous[0] and previous != (f.name, f._ppoi()):
            logger.info("Clearing generated files for %s", repr(previous))
            self._clear_generated_files_for(f, previous[0])

        if f.name:
            for item in f.field.formats:
                f.process(item)

    def _clear_generated_files(self, instance, **kwargs):
        self._clear_generated_files_for(getattr(instance, self.name), None)

    def _clear_generated_files_for(self, fieldfile, filename):
        filename = fieldfile.name if filename is None else filename

        key = "imagefield-admin-thumb:%s" % filename
        cache.delete(key)

        folder, startswith = fieldfile._processed_base(filename)

        try:
            folders, files = fieldfile.storage.listdir(folder)
        except EnvironmentError:  # FileNotFoundError on PY3
            # Fine!
            return

        for file in files:
            if file.startswith(startswith):
                fieldfile.storage.delete(os.path.join(folder, file))

    def check(self, **kwargs):
        errors = super(ImageField, self).check(**kwargs)
        if not all((self.width_field, self.height_field)):
            errors.append(
                checks.Warning(
                    "ImageField without width_field/height_field will be slow!",
                    hint="auto_add_fields=True automatically adds the fields.",
                    obj=self,
                    id="imagefield.W001",
                )
            )
        if not self.ppoi_field:
            errors.append(
                checks.Info(
                    "ImageField without ppoi_field.",
                    hint="auto_add_fields=True automatically adds the field.",
                    obj=self,
                    id="imagefield.I001",
                )
            )
        return errors


class PPOIField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", "0.5x0.5")
        kwargs.setdefault("max_length", 20)
        super(PPOIField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs["widget"] = PPOIWidget
        return super(PPOIField, self).formfield(**kwargs)
