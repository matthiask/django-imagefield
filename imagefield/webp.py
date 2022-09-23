from imagefield.processing import register


@register
def force_webp(get_image):
    def processor(image, context):
        context.save_kwargs["format"] = "WEBP"
        image = get_image(image, context)
        context.save_kwargs["quality"] = 95
        return image

    return processor


def webp(processors):
    def spec(fieldfile, context):
        context.extension = ".webp"
        context.processors = ["force_webp"] + processors

    return spec
