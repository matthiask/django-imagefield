from __future__ import unicode_literals

from collections import namedtuple
import hashlib
import io
import logging
import os
import re

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


class _SealableAttribute(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        if obj._is_sealed:
            raise AttributeError("Sealed attribute")
        obj.__dict__[self.name] = value


class Context(object):
    ppoi = _SealableAttribute("ppoi")
    extension = _SealableAttribute("extension")
    processors = _SealableAttribute("processors")
    name = _SealableAttribute("name")

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._is_sealed = False

    def __repr__(self):
        # From https://docs.python.org/3/library/types.html#types.SimpleNamespace
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def seal(self):
        self._is_sealed = True


logger = logging.getLogger(__name__)
#: Imagefield instances
IMAGEFIELDS = []


def hashdigest(str):
    return hashlib.sha1(str.encode("utf-8")).hexdigest()


class VersatileImageProxy(object):
    def __init__(self, file, item):
        self.file = file
        self.items = [item]

    def __getattr__(self, item):
        self.items.append(item)
        return self

    def __getitem__(self, item):
        self.items.append(item)
        return self

    def __str__(self):
        processors = [
            "default",
            (self.items[0], tuple(map(int, self.items[1].split("x")))),
        ]
        url = self.file.storage.url(self.file._process_context(processors).name)
        key = "v-i-p:{}".format(url)
        if not cache.get(key):
            self.file.process(processors)
            cache.set(key, 1, timeout=None)
        return url


_ProcessBase = namedtuple("_ProcessBase", "path basename")


class ImageFieldFile(files.ImageFieldFile):
    def __getattr__(self, item):
        # The "field" attribute is not there after unpickling, and
        # FileDescriptor checks for its presence before re-assigning the field
        # instance...
        if not hasattr(self, "field"):
            raise AttributeError
        if item in self.field.formats:
            if self.name:
                url = self.storage.url(
                    self._process_context(self.field.formats[item]).name
                )
            else:
                url = ""
            setattr(self, item, url)
            return url
        elif getattr(settings, "IMAGEFIELD_VERSATILEIMAGEPROXY", False) and item in {
            "thumbnail",
            "crop",
        }:
            return VersatileImageProxy(self, item)
        raise AttributeError

    def _ppoi(self):
        if self.field.ppoi_field:
            return [
                float(coord)
                for coord in getattr(self.instance, self.field.ppoi_field).split("x")
            ]
        return [0.5, 0.5]

    def _process_base(self, name):
        p1 = hashdigest(name)
        filename, _ = os.path.splitext(os.path.basename(name))
        return _ProcessBase("__processed__/%s" % p1[:3], "%s-" % filename)

    def _process_context(self, processors):
        context = Context(
            ppoi=self._ppoi(), save_kwargs={}, extension=os.path.splitext(self.name)[1]
        )
        if callable(processors):
            processors(self, context)
        else:
            context.processors = processors
        base = self._process_base(self.name)
        spec = "|".join(str(p) for p in context.processors) + "|" + str(context.ppoi)
        spec = re.sub(r"\bu('|\")", "\\1", spec)  # Strip u"" prefixes on PY2
        p2 = hashdigest(spec)
        context.name = "%s/%s%s%s" % (
            base.path,
            base.basename,
            p2[:12],
            context.extension,
        )
        context.seal()
        return context

    def process(self, spec, force=False):
        if isinstance(spec, (list, tuple)):
            processors = spec
            spec = "<ad hoc>"
        elif callable(spec):
            processors = spec  # Evaluated in _process_context
            spec = "<callable>"
        else:
            processors = self.field.formats[spec]

        context = self._process_context(processors)
        logger.debug(
            'Processing image "%(image)s" as "%(key)s" with context %(context)s',
            {"image": self, "key": spec, "context": context},
        )
        if not force and self.storage.exists(context.name):
            return context.name

        try:
            buf = self._process(context=context)
        except Exception:
            logger.exception(
                'Exception while processing "%(context)s"', {"context": context}
            )
            raise

        self.storage.delete(context.name)
        self.storage.save(context.name, ContentFile(buf))

        logger.info('Saved "%(name)s" successfully', {"name": context.name})
        return context.name

    def _process(self, processors=None, context=None):
        assert bool(processors) != bool(context), "Pass exactly one, not both"

        if context is None:
            context = Context(ppoi=self._ppoi(), save_kwargs={}, processors=processors)
            context.seal()

        self.open("rb")
        image = Image.open(self.file)
        context.save_kwargs.setdefault("format", image.format)

        handler = build_handler(context.processors)
        image = handler(image, context)

        with io.BytesIO() as buf:
            image.save(buf, **context.save_kwargs)
            return buf.getvalue()


class ImageField(models.ImageField):
    attr_class = ImageFieldFile

    def __init__(self, *args, **kwargs):
        self._auto_add_fields = kwargs.pop("auto_add_fields", False)
        self._formats = kwargs.pop("formats", {})
        self.ppoi_field = kwargs.pop("ppoi_field", None)
        super(ImageField, self).__init__(*args, **kwargs)

    @cached_property
    def field_label(self):
        return (
            "%s.%s.%s"
            % (self.model._meta.app_label, self.model._meta.model_name, self.name)
        ).lower()

    @property
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
        try:
            super(ImageField, self).save_form_data(instance, data)
        except Exception as exc:
            # The image was either of an unknown type or so corrupt Django
            # couldn't even begin to process it.
            super(ImageField, self).save_form_data(instance, "")
            raise ValidationError({self.name: "%s" % exc})

        if data is not None:
            f = getattr(instance, self.name)
            if f.name:
                try:
                    # Anything which exercises the machinery so that we may
                    # find out whether the image works at all (or not)
                    f._process(processors=["default", ("thumbnail", (20, 20))])
                except Exception as exc:
                    raise ValidationError({self.name: "%s" % exc})

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
            for spec in f.field.formats:
                f.process(spec)

    def _clear_generated_files(self, instance, **kwargs):
        self._clear_generated_files_for(getattr(instance, self.name), None)

    def _clear_generated_files_for(self, fieldfile, filename):
        filename = fieldfile.name if filename is None else filename

        key = "imagefield-admin-thumb:%s" % filename
        cache.delete(key)

        base = fieldfile._process_base(filename)

        try:
            folders, files = fieldfile.storage.listdir(base.path)
        except EnvironmentError:  # FileNotFoundError on PY3
            # Fine!
            return

        for file in files:
            if file.startswith(base.basename):
                fieldfile.storage.delete(os.path.join(base.path, file))

    def check(self, **kwargs):
        errors = super(ImageField, self).check(**kwargs)
        if not self.width_field or not self.height_field:
            errors.append(
                checks.Error(
                    "ImageField without width_field/height_field is slow!",
                    hint="auto_add_fields=True automatically adds the fields.",
                    obj=self,
                    id="imagefield.E001",
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
