from django.test.utils import override_settings

from .models import Model
from .utils import BaseTest


def fallback(processors):
    def fallback_spec(fieldfile, context):
        context.fallback = "blub.jpg"
        context.processors = processors

    return fallback_spec


@override_settings(
    IMAGEFIELD_FORMATS={"testapp.model.image": {"test": fallback(["default"])}}
)
class FallbackTest(BaseTest):
    def test_fallback(self):
        m = Model()
        self.assertEqual(m.image.test, "/media/blub.jpg")
