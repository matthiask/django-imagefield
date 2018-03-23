import hashlib
import io
import itertools
import os
from types import SimpleNamespace

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields import files
from django.forms import ClearableFileInput
from django.utils.http import urlsafe_base64_encode

from PIL import Image

from .processing import build_handler
from .widgets import PPOIWidget, with_preview_and_ppoi


IMAGE_FIELDS = []


def urlhash(str):
    digest = hashlib.sha1(str.encode('utf-8')).digest()
    return urlsafe_base64_encode(digest).decode('ascii')


class ImageFieldFile(files.ImageFieldFile):
    def __getattr__(self, item):
        if item in self.field.formats:
            url = self.storage.url(
                self._processed_name(self.field.formats[item]),
            )
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

    def _processed_name(self, processors):
        p1 = urlhash(self.name)
        p2 = urlhash(
            '|'.join(str(p) for p in processors) + '|' + str(self._ppoi()),
        )
        _, ext = os.path.splitext(self.name)

        return '__processed__/%s/%s_%s%s' % (p1[:2], p1[2:], p2, ext)

    def process(self, item, force=False):
        processors = self.field.formats[item]
        target = self._processed_name(processors)
        if not force and self.storage.exists(target):
            return

        always = [
            'autorotate', 'process_jpeg', 'process_gif',
            'preserve_icc_profile',
        ]

        with self.open('rb') as orig:
            image = Image.open(orig)
            context = SimpleNamespace(
                ppoi=self._ppoi(),
                save_kwargs={},
            )
            format = image.format
            _, ext = os.path.splitext(self.name)

            handler = build_handler(itertools.chain(always, processors))
            image, context = handler(image, context)

            with io.BytesIO() as buf:
                image.save(buf, format=format, **context.save_kwargs)

                self.storage.delete(target)
                self.storage.save(target, ContentFile(buf.getvalue()))

    def save(self, name, content, save=True):
        super().save(name, content, save=True)
        for key in self.field.formats:
            self.process(key)


class ImageField(models.ImageField):
    attr_class = ImageFieldFile

    def __init__(self, verbose_name=None, **kwargs):
        self.formats = kwargs.pop('formats', None) or {}
        self.ppoi_field = kwargs.pop('ppoi_field', None)

        # TODO implement this? Or handle this outside? Maybe as an image
        # processor? I fear that otherwise we have to reimplement parts of the
        # ImageFileDescriptor (not hard, but too much copy paste for my taste)
        # self.placeholder = kwargs.pop('placeholder', None)

        super().__init__(verbose_name, **kwargs)

        IMAGE_FIELDS.append(self)

    def formfield(self, **kwargs):
        kwargs['widget'] = with_preview_and_ppoi(
            kwargs.get('widget', ClearableFileInput),
            ppoi_field=self.ppoi_field,
        )
        return super().formfield(**kwargs)

    def save_form_data(self, instance, data):
        super().save_form_data(instance, data)
        if data is not None and not data:
            if self.ppoi_field:
                setattr(instance, self.ppoi_field, '0.5x0.5')


class PPOIField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', '0.5x0.5')
        kwargs.setdefault('max_length', 20)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = PPOIWidget
        return super().formfield(**kwargs)
