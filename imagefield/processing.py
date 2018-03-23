import io
import os
from hashlib import sha1
from types import SimpleNamespace

from django.core.files.base import ContentFile

from PIL import Image


PROCESSORS = {}


def register(fn):
    PROCESSORS[fn.__name__] = fn
    return fn


@register
def autorotate(get_image, ppoi_value, args):
    def processor(image, context):
        return get_image(image, context)
    return processor


@register
def thumbnail(get_image, ppoi_value, args):
    def processor(image, context):
        image = image.copy()
        image.thumbnail(args[0], Image.BICUBIC)
        return get_image(image, context)
    return processor


@register
def crop(get_image, ppoi_value, args):
    def processor(image, context):
        return get_image(image, context)
    return processor


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
    # Build the processor chain
    def handler(*args):
        return args

    args = []
    for part in reversed(processors):
        if part in PROCESSORS:
            print(PROCESSORS[part], handler, ppoi_value, args)
            handler = PROCESSORS[part](handler, ppoi_value, args[:])
            args.clear()
        else:
            args.append(part)

    # Run it
    image = Image.open(file.open('rb'))
    format = image.format
    _, ext = os.path.splitext(file.name)

    image, context = handler(image, SimpleNamespace(save_kwargs={}))

    with io.BytesIO() as buf:
        image.save(buf, format=format, **context.save_kwargs)

        filename = '%s/%s%s' % (
            get_processed_image_base(file),
            get_processed_image_name(processors, ppoi_value),
            ext,
        )
        file.storage.delete(filename)
        file.storage.save(filename, ContentFile(buf.getvalue()))
