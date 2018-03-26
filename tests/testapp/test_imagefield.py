import io
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils.translation import deactivate_all

from PIL import Image

from .models import Model  # , ModelWithOptional


def openimage(path):
    return io.open(os.path.join(settings.MEDIA_ROOT, path), 'rb')


class Test(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            'admin', 'admin@test.ch', 'blabla')
        deactivate_all()

        shutil.rmtree(
            os.path.join(settings.MEDIA_ROOT, '__processed__'),
            ignore_errors=True,
        )
        shutil.rmtree(
            os.path.join(settings.MEDIA_ROOT, 'images'),
            ignore_errors=True,
        )

    def login(self):
        client = Client()
        client.force_login(self.user)
        return client

    def test_modules(self):
        """Admin modules are present, necessary JS too"""

        client = self.login()
        response = client.get('/admin/')
        self.assertContains(
            response,
            '<a href="/admin/testapp/model/">Models</a>',
            1,
        )

    def test_model(self):
        m = Model.objects.create()

        client = self.login()
        response = client.get('/admin/testapp/model/%s/change/' % m.id)

        print(response.content.decode('utf-8'))

    def test_model_with_optional(self):
        client = self.login()
        response = client.get('/admin/testapp/modelwithoptional/add/')

        print(response.content.decode('utf-8'))

    def test_upload(self):
        client = self.login()
        with openimage('python-logo.png') as f:
            response = client.post(
                '/admin/testapp/model/add/',
                {
                    'image': f,
                    'ppoi': '0.5x0.5',
                },
            )
            self.assertRedirects(response, '/admin/testapp/model/')

        m = Model.objects.get()
        self.assertTrue(m.image.name)
        self.assertEqual(
            m.image.thumbnail,
            '/media/__processed__/Aq/qeyFxGp-gwNJbrT9WyBNu93Jk_JPhwI4PndMFMtagIW3tLVD17vWk.png',  # noqa
        )
        self.assertRaises(
            AttributeError,
            lambda: m.image.not_exists,
        )

    def test_autorotate(self):
        for image in ['Landscape_3.jpg', 'Landscape_6.jpg', 'Landscape_8.jpg']:
            with self.subTest(image=image):
                m = Model(
                    image='exif-orientation-examples/%s' % image,
                    ppoi='0.5x0.5',
                )
                m.image.process('desktop')

                path = os.path.join(settings.MEDIA_ROOT, m.image.desktop[7:])
                with Image.open(path) as image:
                    self.assertEqual(
                        image.size,
                        (300, 225),
                    )
