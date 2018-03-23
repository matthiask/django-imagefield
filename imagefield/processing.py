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
def autorotate(get_image, ppoi, args):
    def processor(image, context):
        if not hasattr(image, '_getexif'):
            return get_image(image, context)

        exif = image._getexif()
        if not exif:
            return get_image(image, context)

        orientation = dict(exif.items()).get(274)
        rotation = {
            3: Image.ROTATE_180,
            6: Image.ROTATE_270,
            8: Image.ROTATE_90,
        }.get(orientation)
        if rotation:
            return get_image(image.transpose(rotation), context)
        return get_image(image, context)
    return processor


@register
def thumbnail(get_image, ppoi, args):
    def processor(image, context):
        image = image.copy()
        image.thumbnail(args[0], Image.BICUBIC)
        return get_image(image, context)
    return processor


@register
def crop(get_image, ppoi, args):
    width, height = args[0]

    def processor(image, context):
        ppoi_x_axis = int(image.size[0] * ppoi[0])
        ppoi_y_axis = int(image.size[1] * ppoi[1])
        center_pixel_coord = (ppoi_x_axis, ppoi_y_axis)
        # Calculate the aspect ratio of `image`
        orig_aspect_ratio = float(
            image.size[0]
        ) / float(
            image.size[1]
        )
        crop_aspect_ratio = float(width) / float(height)

        # Figure out if we're trimming from the left/right or top/bottom
        if orig_aspect_ratio >= crop_aspect_ratio:
            # `image` is wider than what's needed,
            # crop from left/right sides
            orig_crop_width = int(
                (crop_aspect_ratio * float(image.size[1])) + 0.5
            )
            orig_crop_height = image.size[1]
            crop_boundary_top = 0
            crop_boundary_bottom = orig_crop_height
            crop_boundary_left = center_pixel_coord[0] - (orig_crop_width // 2)
            crop_boundary_right = crop_boundary_left + orig_crop_width
            if crop_boundary_left < 0:
                crop_boundary_left = 0
                crop_boundary_right = crop_boundary_left + orig_crop_width
            elif crop_boundary_right > image.size[0]:
                crop_boundary_right = image.size[0]
                crop_boundary_left = image.size[0] - orig_crop_width

        else:
            # `image` is taller than what's needed,
            # crop from top/bottom sides
            orig_crop_width = image.size[0]
            orig_crop_height = int(
                (float(image.size[0]) / crop_aspect_ratio) + 0.5
            )
            crop_boundary_left = 0
            crop_boundary_right = orig_crop_width
            crop_boundary_top = center_pixel_coord[1] - (orig_crop_height // 2)
            crop_boundary_bottom = crop_boundary_top + orig_crop_height
            if crop_boundary_top < 0:
                crop_boundary_top = 0
                crop_boundary_bottom = crop_boundary_top + orig_crop_height
            elif crop_boundary_bottom > image.size[1]:
                crop_boundary_bottom = image.size[1]
                crop_boundary_top = image.size[1] - orig_crop_height
        # Cropping the image from the original image
        cropped_image = image.crop(
            (
                crop_boundary_left,
                crop_boundary_top,
                crop_boundary_right,
                crop_boundary_bottom
            )
        )
        # Resizing the newly cropped image to the size specified
        # (as determined by `width`x`height`)
        return get_image(
            cropped_image.resize(
                (width, height),
                Image.BICUBIC,
            ),
            context,
        )
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


def get_processed_image_name(processors, ppoi):
    s = '|'.join(str(p) for p in processors)
    s += '|' + str(ppoi)
    return sha1(s.encode('utf-8')).hexdigest()


def get_processed_image_url(file, processors, ppoi):
    _, ext = os.path.splitext(file.name)
    return file.storage.url('%s/%s%s' % (
        get_processed_image_base(file),
        get_processed_image_name(processors, ppoi),
        ext,
    ))


def process_image(file, processors, ppoi):
    # Build the processor chain
    def handler(*args):
        return args

    args = []
    for part in reversed(processors):
        if part in PROCESSORS:
            handler = PROCESSORS[part](handler, ppoi, args[:])
            args.clear()
        else:
            args.append(part)

    # Run it
    with file.open('rb') as orig:
        image = Image.open(orig)
        format = image.format
        _, ext = os.path.splitext(file.name)

        image, context = handler(image, SimpleNamespace(save_kwargs={}))

        with io.BytesIO() as buf:
            image.save(buf, format=format, **context.save_kwargs)

            filename = '%s/%s%s' % (
                get_processed_image_base(file),
                get_processed_image_name(processors, ppoi),
                ext,
            )
            file.storage.delete(filename)
            file.storage.save(filename, ContentFile(buf.getvalue()))
