from imagefield.processing import register


@register
def force_jpeg(get_image):
    def processor(image, context):
        context.save_kwargs["format"] = "JPEG"
        image = get_image(image, context)
        context.save_kwargs["quality"] = 95
        return image

    return processor


def websafe(processors, extensions={".png", ".gif", ".jpg", ".jpeg"}):
    def spec(fieldfile, context):
        # XXX image type match would be SO much better instead of checking extensions
        if context.extension.lower() in extensions:
            context.processors = processors
        else:
            context.extension = ".jpg"
            context.processors = ["force_jpeg"]
            context.processors.extend(processors)

    return spec
