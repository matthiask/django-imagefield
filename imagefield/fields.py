import hashlib
import os

from django.db import models
from django.db.models.fields import files
from django.forms import ClearableFileInput
from django.utils.http import urlsafe_base64_encode

from .processing import process_image
from .widgets import PPOIWidget, with_preview_and_ppoi


IMAGE_FIELDS = []


def urlhash(str):
    digest = hashlib.sha1(str.encode('utf-8')).digest()
    return urlsafe_base64_encode(digest).decode('ascii')


class ImageFieldFile(files.ImageFieldFile):
    def __getattr__(self, key):
        if key in self.field.formats:
            url = self.storage.url(self._processed_name(key))
            setattr(self, key, url)
            return url
        raise AttributeError('Unknown attribute %r' % key)

    def process(self, key, force=False):
        process_image(
            self,

            target=self._processed_name(key),
            processors=self.field.formats[key],
            ppoi=self._ppoi(),

            force=force,
        )

    def _ppoi(self):
        if self.field.ppoi_field:
            return [
                float(coord) for coord in
                getattr(self.instance, self.field.ppoi_field).split('x')
            ]
        return [0.5, 0.5]

    def _processed_name(self, key):
        p1 = urlhash(self.name)
        p2 = urlhash(
            '|'.join(str(p) for p in self.field.formats[key]) + '|' +
            str(self._ppoi()))
        _, ext = os.path.splitext(self.name)

        return '__processed__/%s/%s_%s%s' % (p1[:2], p1[2:], p2, ext)


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

    # TODO reset PPOI when file is empty on save?


class PPOIField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', '0.5x0.5')
        kwargs.setdefault('max_length', 20)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = PPOIWidget
        return super().formfield(**kwargs)
