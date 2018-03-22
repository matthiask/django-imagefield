=================
django-imagefield
=================

.. image:: https://travis-ci.org/matthiask/django-imagefield.svg?branch=master
    :target: https://travis-ci.org/matthiask/django-imagefield

.. image:: https://readthedocs.org/projects/django-imagefield/badge/?version=latest
    :target: https://django-imagefield.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status


Heavily based on `django-versatileimagefield <https://github.com/respondcreate/django-versatileimagefield>`_.


Development
===========

django-imagefield uses both flake8 and isort to check for style violations. It is
recommended to add the following git hook as an executable file at
``.git/hooks/pre-commit``::

    #!/bin/bash
    set -ex
    export PYTHONWARNINGS=ignore
    tox -e style

The easiest way to build the documentation and run the test suite is
using tox_::

    tox -e docs  # Open docs/build/html/index.html
    tox -e tests


.. _documentation: https://django-imagefield.readthedocs.io/en/latest/
.. _tox: https://tox.readthedocs.io/
