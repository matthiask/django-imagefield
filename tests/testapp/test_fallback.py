from django.test.utils import override_settings

from imagefield.websafe import websafe

from .models import Model
from .utils import BaseTest


def fallback(fallback, processors):
    def fallback_spec(fieldfile, context):
        context.fallback = fallback
        context.processors = processors

    return fallback_spec


class FallbackTest(BaseTest):
    @override_settings(
        IMAGEFIELD_FORMATS={
            "testapp.model.image": {"test": fallback("blub.jpg", ["default"])}
        }
    )
    def test_fallback(self):
        m = Model()
        self.assertEqual(m.image.test, "/media/blub.jpg")

        m = Model.objects.create(image="python-logo.png")
        self.assertEqual(
            m.image.test, "/media/__processed__/beb/python-logo-916e1cf9dc6f.png"
        )

    @override_settings(
        IMAGEFIELD_FORMATS={
            "testapp.model.image": {"test": fallback("blab.jpg", websafe(["default"]))}
        }
    )
    def test_websafe_fallback(self):
        m = Model()
        self.assertEqual(m.image.test, "/media/blab.jpg")

        m = Model.objects.create(image="python-logo.tiff")
        self.assertEqual(
            m.image.test, "/media/__processed__/639/python-logo-f3e0804b47bb.jpg"
        )
