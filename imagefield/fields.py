import hashlib
import io
import logging
import os
from types import SimpleNamespace

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import signals
from django.db.models.fields import files
from django.forms import ClearableFileInput
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_encode

from PIL import Image

from .processing import build_handler
from .widgets import PPOIWidget, with_preview_and_ppoi


logger = logging.getLogger(__name__)
#: Imagefield instances
IMAGEFIELDS = set()


class ImageFieldFile(files.ImageFieldFile):
    def __getattr__(self, item):
        if item in self.field.formats:
            if self.name:
                url = self.storage.url(
                    self._processed_name(self.field.formats[item]),
                )
            else:
                url = ''
            setattr(self, item, url)
            return url
        raise AttributeError

    def _ppoi(self):
        if self.field.ppoi_field:
            return [
                float(coord) for coord in
                getattr(self.instance, self.field.ppoi_field).split('x')
            ]
        return [0.5, 0.5]

    def _urlhash(self, str):
        digest = hashlib.sha1(str.encode('utf-8')).digest()
        return urlsafe_base64_encode(digest).decode('ascii')

    def _processed_name(self, processors):
        p1 = self._urlhash(self.name)
        p2 = self._urlhash(
            '|'.join(str(p) for p in processors) + '|' + str(self._ppoi()),
        )
        _, ext = os.path.splitext(self.name)

        return '__processed__/%s/%s_%s%s' % (p1[:2], p1[2:], p2, ext)

    def _processed_base(self):
        p1 = self._urlhash(self.name)
        return '__processed__/%s' % p1[:2], '%s_' % p1[2:]

    def process(self, item, force=False):
        processors = self.field.formats[item]
        target = self._processed_name(processors)
        logger.debug(
            'Processing image %(image)s as "%(key)s" with target %(target)s'
            ' and pipeline %(processors)s',
            {
                'image': self,
                'key': item,
                'target': target,
                'processors': processors,
            },
        )
        if not force and self.storage.exists(target):
            return

        try:
            buf = self._process(processors)
        except Exception:
            logger.exception('Exception while processing')
            raise

        self.storage.delete(target)
        self.storage.save(target, ContentFile(buf))

        logger.info(
            'Saved processed image %(target)s',
            {'target': target},
        )

    def _process(self, processors):
        self.open('rb')
        image = Image.open(self.file)
        context = SimpleNamespace(
            ppoi=self._ppoi(),
            save_kwargs={},
        )
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
        self._auto_add_fields = kwargs.pop('auto_add_fields', False)
        self._formats = kwargs.pop('formats', {})
        self.ppoi_field = kwargs.pop('ppoi_field', None)

        # TODO implement this? Or handle this outside? Maybe as an image
        # processor? I fear that otherwise we have to reimplement parts of the
        # ImageFileDescriptor (not hard, but too much copy paste for my taste)
        # self.placeholder = kwargs.pop('placeholder', None)

        super().__init__(verbose_name, **kwargs)

        IMAGEFIELDS.add(self)

    @cached_property
    def formats(self):
        setting = getattr(settings, 'IMAGEFIELD_FORMATS', {})
        return setting.get(
            ('%s.%s' % (self.model._meta.label_lower, self.name)).lower(),
            self._formats,
        )

    def contribute_to_class(self, cls, name, **kwargs):
        if self._auto_add_fields:
            if self.width_field is None:
                self.width_field = '%s_width' % name
                models.PositiveIntegerField(
                    blank=True, null=True, editable=False,
                ).contribute_to_class(cls, self.width_field)
            if self.height_field is None:
                self.height_field = '%s_height' % name
                models.PositiveIntegerField(
                    blank=True, null=True, editable=False,
                ).contribute_to_class(cls, self.height_field)
            if self.ppoi_field is None:
                self.ppoi_field = '%s_ppoi' % name
                PPOIField().contribute_to_class(cls, self.ppoi_field)

        super().contribute_to_class(cls, name, **kwargs)

        if not cls._meta.abstract:
            # TODO Avoid calling process() too often?
            # signals.post_init.connect(self.cache_values, sender=cls)

            # TODO Allow deactivating this by to move it out of the
            # request-response cycle.
            signals.post_save.connect(
                self._generate_files,
                sender=cls,
            )
            signals.post_delete.connect(
                self._clear_generated_files,
                sender=cls,
            )

    def formfield(self, **kwargs):
        kwargs['widget'] = with_preview_and_ppoi(
            kwargs.get('widget', ClearableFileInput),
            ppoi_field=self.ppoi_field,
        )
        return super().formfield(**kwargs)

    def save_form_data(self, instance, data):
        super().save_form_data(instance, data)

        # Reset PPOI field if image field is cleared
        if data is not None and not data:
            if self.ppoi_field:
                setattr(instance, self.ppoi_field, '0.5x0.5')

        elif data is not None:
            f = getattr(instance, self.name)
            if f.name:
                try:
                    # Anything which exercises the machinery so that we may
                    # find out whether the image works at all (or not)
                    f._process(['default', ('thumbnail', (20, 20))])
                except Exception as exc:
                    raise ValidationError(str(exc))

    def _generate_files(self, instance, **kwargs):
        f = getattr(instance, self.name)
        if f.name:
            for item in f.field.formats:
                f.process(item)

    def _clear_generated_files(self, instance, **kwargs):
        f = getattr(instance, self.name)
        folder, startswith = f._processed_base()

        folders, files = f.storage.listdir(folder)
        for file in files:
            if file.startswith(startswith):
                f.storage.delete(os.path.join(folder, file))


class PPOIField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', '0.5x0.5')
        kwargs.setdefault('max_length', 20)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = PPOIWidget
        return super().formfield(**kwargs)
