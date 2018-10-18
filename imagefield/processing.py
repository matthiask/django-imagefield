from __future__ import division, unicode_literals

from PIL import Image


PROCESSORS = {}


def build_handler(processors, handler=None):
    handler = handler or (lambda image, context: image)

    for part in reversed(processors):
        if isinstance(part, (list, tuple)):
            handler = PROCESSORS[part[0]](handler, part[1:])
        else:
            handler = PROCESSORS[part](handler, [])

    return handler


def register(fn):
    PROCESSORS[fn.__name__] = fn
    return fn


@register
def default(get_image, args):
    return build_handler(
        ["preserve_icc_profile", "process_gif", "process_jpeg", "autorotate"], get_image
    )


@register
def autorotate(get_image, args):
    def processor(image, context):
        if not hasattr(image, "_getexif"):
            return get_image(image, context)

        exif = image._getexif()
        if not exif:
            return get_image(image, context)

        # Do not add no exif data to save_kwargs.
        orientation = dict(exif.items()).get(274)
        rotation = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}.get(
            orientation
        )
        if rotation:
            return get_image(image.transpose(rotation), context)
        return get_image(image, context)

    return processor


@register
def process_jpeg(get_image, args):
    def processor(image, context):
        if context.save_kwargs["format"] == "JPEG":
            context.save_kwargs["quality"] = 90
            context.save_kwargs["progressive"] = True
            if image.mode != "RGB":
                image = image.convert("RGB")
        return get_image(image, context)

    return processor


@register
def process_gif(get_image, args):
    def processor(image, context):
        if context.save_kwargs["format"] != "GIF":
            return get_image(image, context)

        if "transparency" in image.info:
            context.save_kwargs["transparency"] = image.info["transparency"]
        palette = image.getpalette()
        image = get_image(image, context)
        image.putpalette(palette)
        return image

    return processor


@register
def preserve_icc_profile(get_image, args):
    def processor(image, context):
        context.save_kwargs["icc_profile"] = image.info.get("icc_profile")
        return get_image(image, context)

    return processor


@register
def thumbnail(get_image, args):
    def processor(image, context):
        image = get_image(image, context)
        f = min(1.0, args[0][0] / image.size[0], args[0][1] / image.size[1])
        return image.resize([int(f * coord) for coord in image.size], Image.LANCZOS)

    return processor


@register
def crop(get_image, args):
    width, height = args[0]

    def processor(image, context):
        image = get_image(image, context)

        ppoi_x_axis = int(image.size[0] * context.ppoi[0])
        ppoi_y_axis = int(image.size[1] * context.ppoi[1])
        center_pixel_coord = (ppoi_x_axis, ppoi_y_axis)
        # Calculate the aspect ratio of `image`
        orig_aspect_ratio = float(image.size[0]) / float(image.size[1])
        crop_aspect_ratio = float(width) / float(height)

        # Figure out if we're trimming from the left/right or top/bottom
        if orig_aspect_ratio >= crop_aspect_ratio:
            # `image` is wider than what's needed,
            # crop from left/right sides
            orig_crop_width = int((crop_aspect_ratio * float(image.size[1])) + 0.5)
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
            orig_crop_height = int((float(image.size[0]) / crop_aspect_ratio) + 0.5)
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
                crop_boundary_bottom,
            )
        )
        # Resizing the newly cropped image to the size specified
        # (as determined by `width`x`height`)
        return cropped_image.resize((width, height), Image.LANCZOS)

    return processor
