from __future__ import unicode_literals

import io
import os
import re
import sys
import time
from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client
from django.test.utils import override_settings

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from imagefield.fields import IMAGEFIELDS
from PIL import Image

from .models import (
    Model,
    ModelWithOptional,
    NullableImage,
    SlowStorageImage,
    WebsafeImage,
    slow_storage,
)
from .utils import BaseTest, openimage, contents


class Test(BaseTest):
    def login(self):
        self.user = User.objects.create_superuser("admin", "admin@test.ch", "blabla")
        client = Client()
        client.login(username="admin", password="blabla")
        # client.force_login(self.user)
        return client

    def test_model(self):
        """Behavior of model with ImageField(blank=False)"""
        m = Model.objects.create(image="python-logo.png")

        client = self.login()
        response = client.get(reverse("admin:testapp_model_change", args=(m.id,)))

        self.assertContains(response, 'value="0.5x0.5"')
        self.assertContains(response, 'src="/static/imagefield/ppoi.js"')
        self.assertContains(response, '<div class="imagefield" data-ppoi-id="id_ppoi">')

        self.assertContains(
            response,
            '<img class="imagefield-preview-image"'
            ' src="/media/__processed__/beb/python-logo-6e3df744dc82.png"'
            ' alt=""/>',
        )

    def test_no_ppoi_admin(self):
        client = self.login()
        m = NullableImage.objects.create(image="python-logo.png")
        response = client.get(
            reverse("admin:testapp_nullableimage_change", args=(m.id,))
        )
        self.assertContains(response, 'data-ppoi-id=""')

    def test_model_with_optional(self):
        """Behavior of model with ImageField(blank=True)"""
        client = self.login()
        response = client.get("/admin/testapp/modelwithoptional/add/")
        self.assertContains(response, 'src="/static/imagefield/ppoi.js"')

        m = ModelWithOptional.objects.create()
        response = client.get(
            reverse("admin:testapp_modelwithoptional_change", args=(m.id,))
        )
        self.assertContains(
            response,
            '<input type="file" name="image" id="id_image" accept="image/*"/>',
            html=True,
        )

    def test_upload(self):
        """Adding and updating images does not leave old thumbs around"""
        client = self.login()
        self.assertEqual(contents("__processed__"), [])

        with openimage("python-logo.png") as f:
            response = client.post(
                "/admin/testapp/model/add/", {"image": f, "ppoi": "0.5x0.5"}
            )
            self.assertRedirects(response, "/admin/testapp/model/")

        self.assertEqual(
            contents("__processed__"),
            ["python-logo-24f8702383e7.png", "python-logo-e6a99ea713c8.png"],
        )

        m = Model.objects.get()
        self.assertTrue(m.image.name)
        self.assertEqual(
            m.image.thumb, "/media/__processed__/02a/python-logo-24f8702383e7.png"
        )
        with self.assertRaises(AttributeError):
            m.image.not_exists

        response = client.post(
            reverse("admin:testapp_model_change", args=(m.pk,)),
            {"image": "", "ppoi": "0x0"},
        )
        self.assertRedirects(response, "/admin/testapp/model/")
        self.assertEqual(
            contents("__processed__"),
            ["python-logo-096bade32f42.png", "python-logo-2f5189af7eb3.png"],
        )

    def test_autorotate(self):
        """Images are automatically rotated according to EXIF data"""
        field = Model._meta.get_field("image")

        for image in ["Landscape_3.jpg", "Landscape_6.jpg", "Landscape_8.jpg"]:
            m = Model(image="exif-orientation-examples/%s" % image, ppoi="0.5x0.5")
            m.image.process("desktop")

            path = os.path.join(settings.MEDIA_ROOT, m.image.desktop[7:])
            with Image.open(path) as image:
                self.assertEqual(image.size, (300, 225))

            self.assertEqual(len(contents("__processed__")), 1)
            field._clear_generated_files(m)
            self.assertEqual(contents("__processed__"), [])

    def test_cmyk(self):
        """JPEG in CMYK is converted to RGB"""
        field = Model._meta.get_field("image")

        m = Model(image="cmyk.jpg", ppoi="0.5x0.5")
        m.image.process("desktop")

        path = os.path.join(settings.MEDIA_ROOT, m.image.desktop[7:])
        with Image.open(path) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.mode, "RGB")

        self.assertEqual(contents("__processed__"), ["cmyk-e6a99ea713c8.jpg"])
        field._clear_generated_files(m)
        self.assertEqual(contents("__processed__"), [])

    def test_empty(self):
        """Model without an imagefield does not crash when accessing props"""
        m = Model()
        self.assertEqual(m.image.name, "")
        self.assertEqual(m.image.desktop, "")

    def test_ppoi_reset(self):
        """PPOI field reverts to default when image field is cleared"""
        client = self.login()
        with openimage("python-logo.png") as f:
            response = client.post(
                "/admin/testapp/modelwithoptional/add/",
                {"image": f, "image_ppoi": "0.25x0.25"},
            )
            self.assertRedirects(response, "/admin/testapp/modelwithoptional/")

        m = ModelWithOptional.objects.get()
        self.assertEqual(m.image._ppoi(), [0.25, 0.25])

        response = client.post(
            reverse("admin:testapp_modelwithoptional_change", args=(m.pk,)),
            {"image-clear": "1", "image_ppoi": "0.25x0.25"},
        )

        self.assertRedirects(response, "/admin/testapp/modelwithoptional/")

        m = ModelWithOptional.objects.get()
        self.assertEqual(m.image.name, "")
        self.assertEqual(m.image_ppoi, "0.5x0.5")

    def test_broken(self):
        """Broken images are rejected early"""
        exceptions = (IOError, OSError)
        import django

        if django.VERSION < (1, 11):
            exceptions += (TypeError,)

        with self.assertRaises(exceptions):
            Model.objects.create(image="broken.png")

        client = self.login()
        with openimage("broken.png") as f:
            response = client.post(
                "/admin/testapp/model/add/", {"image": f, "ppoi": "0.5x0.5"}
            )

        self.assertContains(
            response,
            "Upload a valid image. The file you uploaded was either"
            " not an image or a corrupted image.",
        )

        with openimage("python-logo.jpg") as f:
            response = client.post(
                "/admin/testapp/model/add/", {"image": f, "ppoi": "0.5x0.5"}
            )
            self.assertRedirects(response, "/admin/testapp/model/")

            f.seek(0)
            with io.BytesIO(f.read()[:-1000]) as buf:
                buf.name = "python-logo.jpg"
                response = client.post(
                    "/admin/testapp/model/add/", {"image": buf, "ppoi": "0.5x0.5"}
                )
                self.assertTrue(
                    re.search(
                        r"image file is truncated \([0-9]+ bytes not processed\)",
                        response.content.decode("utf-8"),
                    )
                )

        with openimage("smallliz.tif") as f:
            response = client.post(
                "/admin/testapp/model/add/", {"image": f, "ppoi": "0.5x0.5"}
            )

        self.assertContains(response, "This field cannot be blank.")
        self.assertContains(
            response,
            "Error while handling image, maybe the file"
            " is corrupt or the image format is unsupported.",
        )

    def test_silent_failure(self):
        Model.objects.create(image="python-logo.jpg")
        Model.objects.update(image="smallliz.tif")
        m = Model.objects.get()

        with self.assertRaises(Exception):
            m.image.process("desktop")

        with override_settings(IMAGEFIELD_SILENTFAILURE=True):
            self.assertEqual(m.image.process("desktop"), "smallliz.tif")

    def test_cmyk_validation(self):
        """
        Test that the image verification can handle CMYK images.
        """
        client = self.login()
        with openimage("preview_LoxdQ3U.jpg") as f:
            response = client.post(
                "/admin/testapp/model/add/", {"image": f, "ppoi": "0.5x0.5"}
            )

        self.assertRedirects(response, "/admin/testapp/model/")

    def test_adhoc(self):
        """Ad-hoc processing pipelines may be built and executed"""
        m = Model.objects.create(image="python-logo.jpg")
        self.assertEqual(
            contents("__processed__"),
            ["python-logo-24f8702383e7.jpg", "python-logo-e6a99ea713c8.jpg"],
        )
        self.assertEqual(
            m.image.process([("thumbnail", (20, 20))]),
            "__processed__/d00/python-logo-43feb031c1be.jpg",
        )

        # Same result when using a callable as processor spec:
        def spec(fieldfile, context):
            context.processors = [("thumbnail", (20, 20))]

        self.assertEqual(
            m.image.process(spec), "__processed__/d00/python-logo-43feb031c1be.jpg"
        )
        self.assertEqual(
            contents("__processed__"),
            [
                "python-logo-24f8702383e7.jpg",
                "python-logo-43feb031c1be.jpg",
                "python-logo-e6a99ea713c8.jpg",
            ],
        )
        m.delete()
        self.assertEqual(contents("__processed__"), [])

    def test_adhoc_lowlevel(self):
        """Low-level processing pipelines; no saving of generated images"""
        m = Model.objects.create(image="python-logo.jpg")
        m.image._process(processors=[("thumbnail", (20, 20))])
        # New thumb is not saved; still only "desktop" and "thumbnail" images
        self.assertEqual(
            contents("__processed__"),
            ["python-logo-24f8702383e7.jpg", "python-logo-e6a99ea713c8.jpg"],
        )

    @skipIf(sys.version_info[0] < 3, "time.monotonic only with Python>=3.3")
    def test_fast(self):
        """Loading models and generating URLs is not slowed by storages"""
        # Generate thumbs, cache width/height in DB fields
        SlowStorageImage.objects.create(image="python-logo.jpg")

        slow_storage.slow = True

        start = time.monotonic()
        m = SlowStorageImage.objects.get()
        self.assertEqual(
            m.image.thumb, "/media/__processed__/d00/python-logo-10c070f1761f.jpg"
        )
        duration = time.monotonic() - start
        # No opens, no saves
        self.assertTrue(duration < 0.1)

    def test_imagefields(self):
        self.assertEqual(
            set(f.field_label for f in IMAGEFIELDS),
            {
                "testapp.model.image",
                "testapp.slowstorageimage.image",
                "testapp.modelwithoptional.image",
                "testapp.nullableimage.image",
                "testapp.websafeimage.image",
            },
        )

    def test_versatileimageproxy(self):
        m = Model.objects.create(image="python-logo.jpg")
        thumb = m.image.thumbnail["20x20"]
        self.assertEqual(
            contents("__processed__"),
            ["python-logo-24f8702383e7.jpg", "python-logo-e6a99ea713c8.jpg"],
        )
        self.assertEqual(thumb.items, ["thumbnail", "20x20"])
        self.assertEqual(
            "{}".format(thumb), "/media/__processed__/d00/python-logo-f26eb6811b04.jpg"
        )
        self.assertEqual(
            contents("__processed__"),
            [
                "python-logo-24f8702383e7.jpg",
                "python-logo-e6a99ea713c8.jpg",
                "python-logo-f26eb6811b04.jpg",
            ],
        )

    def test_nullableimage(self):
        m = NullableImage.objects.create()
        m.image.process("thumb")

    def test_already_websafe(self):
        # Same as above!
        WebsafeImage.objects.create(image="python-logo.jpg")
        self.assertEqual(contents("__processed__"), ["python-logo-24f8702383e7.jpg"])

    def test_websafe_force_jpeg(self):
        WebsafeImage.objects.create(image="python-logo.tiff")
        self.assertEqual(contents("__processed__"), ["python-logo-2ebc6e32bcdb.jpg"])

    def test_completely_bogus(self):
        client = self.login()
        buf = io.BytesIO(b"anything")
        buf.name = "bogus.jpg"
        response = client.post(
            "/admin/testapp/model/add/", {"image": buf, "ppoi": "0.5x0.5"}
        )
        self.assertContains(response, "Upload a valid image.")

    def test_wrong_extension(self):
        client = self.login()
        self.assertEqual(contents("__processed__"), [])

        with openimage("python-logo.png") as f, io.BytesIO() as buf:
            buf.write(f.read())
            buf.seek(0)
            buf.name = "python-logo.gif"
            response = client.post(
                "/admin/testapp/model/add/", {"image": buf, "ppoi": "0.5x0.5"}
            )
            self.assertRedirects(response, "/admin/testapp/model/")

        self.assertEqual(
            contents("__processed__"),
            ["python-logo-24f8702383e7.png", "python-logo-e6a99ea713c8.png"],
        )
