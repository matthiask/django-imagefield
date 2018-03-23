import io
import os
from collections import deque
from hashlib import sha1
from types import SimpleNamespace

from PIL import Image

from django.core.files.base import ContentFile


PROCESSORS = {}


def register(fn):
    PROCESSORS[fn.__name__] = fn
    return fn


@register
def autorotate(context):
    return context.image


@register
def thumbnail(context):
    dimensions = context.processors.popleft()
    # return context.image.resize(dimensions, Image.BICUBIC)
    image = context.image.copy()
    image.thumbnail(dimensions, Image.BICUBIC)
    return image


@register
def crop(context):
    dimensions = context.processors.popleft()
    return context.image


# TODO: How to specify the placeholder image?
# @register
# def placeholder(get_image):
#     def processor(context):
#         pass
#
#     return processor


def get_processed_image_base(file):
    hd = sha1(file.name.encode('utf-8')).hexdigest()
    return '__processed__/%s/%s/%s' % (hd[:2], hd[2:4], hd[4:])


def get_processed_image_name(processors, ppoi_value):
    s = '|'.join(str(p) for p in processors)
    s += '|' + str(ppoi_value)
    return sha1(s.encode('utf-8')).hexdigest()


def get_processed_image_url(file, processors, ppoi_value):
    _, ext = os.path.splitext(file.name)
    return file.storage.url('%s/%s%s' % (
        get_processed_image_base(file),
        get_processed_image_name(processors, ppoi_value),
        ext,
    ))


def process_image(file, processors, ppoi_value):
    image = Image.open(file.open('rb'))
    format = image.format
    _, ext = os.path.splitext(file.name)

    context = SimpleNamespace(
        file=file,
        image=image,
        ppoi_value=ppoi_value,
        processors=deque(processors),
        save_kwargs={},
    )

    while context.processors:
        context.image = PROCESSORS[context.processors.popleft()](context)

    with io.BytesIO() as buf:
        context.image.save(buf, format=format, **context.save_kwargs)

        filename = '%s/%s%s' % (
            get_processed_image_base(file),
            get_processed_image_name(processors, ppoi_value),
            ext,
        )
        file.storage.delete(filename)
        file.storage.save(filename, ContentFile(buf.getvalue()))
