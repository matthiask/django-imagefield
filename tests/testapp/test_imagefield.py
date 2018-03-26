import io
import itertools
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils.translation import deactivate_all

from PIL import Image

from .models import Image as Image_, Model, ModelWithOptional


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
        self._rmtree()

    def tearDown(self):
        self._rmtree()

    def _rmtree(self):
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
        self.assertContains(
            response,
            'src="/static/imagefield/ppoi.js"',
        )
        # print(response.content.decode('utf-8'))

    def test_image_model(self):
        client = self.login()
        response = client.get('/admin/testapp/image/add/')
        self.assertNotContains(
            response,
            'src="/static/imagefield/ppoi.js"',
        )

        m = Image_.objects.create(
            image='python-logo.png',
        )
        self.assertEqual(
            m.image._ppoi(),
            [0.5, 0.5],
        )

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
        with self.assertRaises(AttributeError):
            m.image.not_exists

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

    def test_cmyk(self):
        field = Model._meta.get_field('image')

        m = Model(
            image='cmyk.jpg',
            ppoi='0.5x0.5',
        )
        m.image.process('desktop')

        path = os.path.join(settings.MEDIA_ROOT, m.image.desktop[7:])
        with Image.open(path) as image:
            self.assertEqual(
                image.format,
                'JPEG',
            )
            self.assertEqual(
                image.mode,
                'RGB',
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
                    'image_ppoi': '0.25x0.25',
                },
            )
            self.assertRedirects(response, '/admin/testapp/modelwithoptional/')

        m = ModelWithOptional.objects.get()
        self.assertEqual(m.image._ppoi(), [0.25, 0.25])

        response = client.post(
            '/admin/testapp/modelwithoptional/%s/change/' % m.pk,
            {
                'image-clear': '1',
                'image_ppoi': '0.25x0.25',
            },
        )

        self.assertRedirects(response, '/admin/testapp/modelwithoptional/')

        m = ModelWithOptional.objects.get()
        self.assertEqual(m.image.name, '')
        self.assertEqual(m.image_ppoi, '0.5x0.5')

    def test_broken(self):
        with self.assertRaises(OSError):
            Model.objects.create(
                image='broken.png',
            )

        client = self.login()
        with openimage('broken.png') as f:
            response = client.post(
                '/admin/testapp/model/add/',
                {
                    'image': f,
                    'ppoi': '0.5x0.5',
                },
            )

        self.assertContains(
            response,
            'Upload a valid image. The file you uploaded was either'
            ' not an image or a corrupted image.',
        )

        with openimage('python-logo.jpg') as f:
            response = client.post(
                '/admin/testapp/model/add/',
                {
                    'image': f,
                    'ppoi': '0.5x0.5',
                },
            )
            self.assertRedirects(
                response,
                '/admin/testapp/model/',
            )

            f.seek(0)
            with io.BytesIO(f.read()[:-1000]) as buf:
                buf.name = 'python-logo.jpg'
                response = client.post(
                    '/admin/testapp/model/add/',
                    {
                        'image': buf,
                        'ppoi': '0.5x0.5',
                    },
                )
                self.assertRegex(
                    response.content.decode('utf-8'),
                    r'image file is truncated \([0-9]+ bytes not processed\)',
                )
