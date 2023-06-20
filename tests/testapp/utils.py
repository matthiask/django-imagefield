import itertools
import logging
import os
import shutil

from django.conf import settings
from django.test import TestCase
from django.utils.translation import deactivate_all


def openimage(path):
    return open(os.path.join(settings.MEDIA_ROOT, path), "rb")


def contents(path):
    return sorted(
        itertools.chain.from_iterable(
            i[2] for i in os.walk(os.path.join(settings.MEDIA_ROOT, path))
        )
    )


class BaseTest(TestCase):
    def setUp(self):
        deactivate_all()
        self._rmtree()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        self._rmtree()
        logging.disable(logging.NOTSET)

    def _rmtree(self):
        shutil.rmtree(
            os.path.join(settings.MEDIA_ROOT, "__processed__"), ignore_errors=True
        )
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "images"), ignore_errors=True)
