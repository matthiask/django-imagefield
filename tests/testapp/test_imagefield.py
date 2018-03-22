from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils.translation import deactivate_all

from .models import Model, ModelWithOptional


class Test(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            'admin', 'admin@test.ch', 'blabla')
        deactivate_all()

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
