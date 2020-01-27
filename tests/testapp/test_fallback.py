from django.test.utils import override_settings

from imagefield.fallback import fallback
from imagefield.websafe import websafe

from .models import WebsafeImage, Model
from .utils import BaseTest, contents


class FallbackTest(BaseTest):
    def test_fallback(self):
        m1 = WebsafeImage()

        # self.assertEqual(m1.image.url, "/media/python-logo.tiff")
        # self.assertEqual(m2.image.url, "/media/python-logo.tiff")

        self.assertEqual(
            m1.image.thumb, "/media/__processed__/639/python-logo-2ebc6e32bcdb.jpg"
        )

        self.assertEqual(contents("__processed__"), [])
        m1.image.process("thumb")
        self.assertEqual(contents("__processed__"), ["python-logo-2ebc6e32bcdb.jpg"])

        m2 = WebsafeImage.objects.create(image="python-logo.tiff")
        self.assertEqual(
            m2.image.thumb, "/media/__processed__/639/python-logo-2ebc6e32bcdb.jpg"
        )
        self.assertEqual(contents("__processed__"), ["python-logo-2ebc6e32bcdb.jpg"])
