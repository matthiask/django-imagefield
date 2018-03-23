from django.db import models
from django.db.models.fields import files
from django.forms import ClearableFileInput

from .processing import get_processed_image_url, process_image
from .widgets import PPOIWidget, with_preview_and_ppoi


IMAGE_FIELDS = []


class ImageFieldFile(files.ImageFieldFile):
    def __getattr__(self, key):
        if key in self.field.formats:
            url = get_processed_image_url(
                self,
                processors=self.field.formats[key],
                ppoi=self.ppoi(),
            )

            setattr(self, key, url)
            return url
        raise AttributeError('Unknown attribute %r' % key)

    def process(self, key, force=False):
        process_image(
            self,
            processors=self.field.formats[key],
            ppoi=self.ppoi(),
            force=force,
        )

    def ppoi(self):
        if self.field.ppoi_field:
            return [
                float(coord) for coord in
                getattr(self.instance, self.field.ppoi_field).split('x')
            ]
        return [0.5, 0.5]


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
        # from pprint import pprint
        # pprint(('in image field', self, self.__dict__, kwargs))
        return super().formfield(**kwargs)

    # TODO reset PPOI when file is empty on save


class PPOIField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', '0.5x0.5')
        kwargs.setdefault('max_length', 20)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = PPOIWidget
        return super().formfield(**kwargs)
