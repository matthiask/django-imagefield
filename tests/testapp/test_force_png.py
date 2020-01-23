from django.test.utils import override_settings

from imagefield.processing import register

from .models import Model
from .utils import BaseTest


@register
def force_png(get_image):
    def processor(image, context):
        image = get_image(image, context)
        # Make Pillow generate a PNG:
        context.save_kwargs["format"] = "PNG"
        return image

    return processor


@register
def too_late(get_image):
    def processor(image, context):
        context.extension = ".png"
        return get_image(image, context)

    return processor


def force_png_spec(fieldfile, context):
    # Make imagefield generate URLs and filenames with a .png extension:
    context.extension = ".png"
    context.processors = ["force_png"]


@override_settings(IMAGEFIELD_FORMATS={"testapp.model.image": {"test": force_png_spec}})
class ForcePNGTest(BaseTest):
    def test_callable_processors(self):
        m = Model.objects.create(image="python-logo.jpg")
        self.assertEqual(
            "{}".format(m.image.test),
            "/media/__processed__/d00/python-logo-5da93aa386ab.png",
        )

    def test_too_late(self):
        m = Model.objects.create(image="python-logo.jpg")
        with self.assertRaises(AttributeError) as cm:
            m.image.process(["too_late"])

        self.assertIn("Sealed attribute", str(cm.exception))
