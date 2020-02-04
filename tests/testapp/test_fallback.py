import os

from django.conf import settings

from .models import WebsafeImage
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

    def test_no_fallback(self):
        m2 = WebsafeImage.objects.create(image="python-logo.tiff")
        self.assertEqual(
            m2.image.thumb, "/media/__processed__/639/python-logo-2ebc6e32bcdb.jpg"
        )
        self.assertEqual(contents("__processed__"), ["python-logo-2ebc6e32bcdb.jpg"])

    def test_delete_fallback(self):
        m1 = WebsafeImage.objects.create()
        path = os.path.join(settings.MEDIA_ROOT, m1._meta.get_field("image")._fallback)
        m1.image.delete()
        self.assertTrue(os.path.exists(path))
