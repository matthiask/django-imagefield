import io
import itertools
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils.translation import deactivate_all

from PIL import Image

from .models import Model, ModelWithOptional


def openimage(path):
    return io.open(os.path.join(settings.MEDIA_ROOT, path), 'rb')


def contents(path):
    return list(itertools.chain.from_iterable(
        i[2] for i in os.walk(os.path.join(settings.MEDIA_ROOT, path))
    ))


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
        m = Model.objects.create(
            image='python-logo.png',
        )

        client = self.login()
        response = client.get('/admin/testapp/model/%s/change/' % m.id)

        self.assertContains(
            response,
            'value="0.5x0.5"',
        )
        self.assertContains(
            response,
            'src="/static/imagefield/ppoi.js"',
        )
        self.assertContains(
            response,
            '<div class="imagefield" data-ppoi-id="id_ppoi">',
        )
        self.assertContains(
            response,
            '<img class="imagefield-preview-image"'
            ' src="/media/python-logo.png" alt=""/>',
        )
        # print(response.content.decode('utf-8'))

    def test_model_with_optional(self):
        client = self.login()
        response = client.get('/admin/testapp/modelwithoptional/add/')
        self.assertEqual(response.status_code, 200)
        # print(response.content.decode('utf-8'))

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
        field = Model._meta.get_field('image')

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

                self.assertEqual(len(contents('__processed__')), 1)
                field._clear_generated_files(m)
                self.assertEqual(contents('__processed__'), [])

    def test_empty(self):
        m = Model()
        self.assertEqual(m.image.name, '')
        self.assertEqual(m.image.desktop, '')

    def test_ppoi_clearing(self):
        client = self.login()
        with openimage('python-logo.png') as f:
            response = client.post(
                '/admin/testapp/modelwithoptional/add/',
                {
                    'image': f,
                    'ppoi': '0.25x0.25',
                },
            )
            self.assertRedirects(response, '/admin/testapp/modelwithoptional/')

        m = ModelWithOptional.objects.get()
        self.assertEqual(m.image._ppoi(), [0.25, 0.25])

        response = client.post(
            '/admin/testapp/modelwithoptional/%s/change/' % m.pk,
            {
                'image-clear': '1',
                'ppoi': '0.25x0.25',
            },
        )

        self.assertRedirects(response, '/admin/testapp/modelwithoptional/')

        m = ModelWithOptional.objects.get()
        self.assertEqual(m.image.name, '')
        self.assertEqual(m.ppoi, '0.5x0.5')
