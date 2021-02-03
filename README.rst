=================
django-imagefield
=================

.. image:: https://github.com/matthiask/django-imagefield/workflows/Tests/badge.svg
    :target: https://github.com/matthiask/django-imagefield

.. image:: https://readthedocs.org/projects/django-imagefield/badge/?version=latest
    :target: https://django-imagefield.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

Heavily based on `django-versatileimagefield
<https://github.com/respondcreate/django-versatileimagefield>`_, but
with a few important differences:

- The amount of code is kept at a minimum. django-versatileimagefield
  has several times as much code (without tests).
- Generating images on-demand inside rendering code is made hard on
  purpose. Instead, images are generated when models are saved and also
  by running the management command ``process_imagefields``.
- django-imagefield does not depend on a fast storage or a cache to be
  and stay fast, at least as long as the image width and height is saved
  in the database. An important part of this is never determining
  whether a processed image exists in the hot path at all (except if you
  ``force`` it).
- django-imagefield fails early when image data is incomplete or not
  processable by Pillow_ for some reason.
- django-imagefield allows adding width, height and PPOI (primary point
  of interest) fields to the model by adding ``auto_add_fields=True`` to
  the field instead of boringly and verbosingly adding them yourself.

Replacing existing uses of django-versatileimagefield requires the
following steps:

- ``from imagefield.fields import ImageField as VersatileImageField, PPOIField``
- Specify the image sizes by either providing ``ImageField(formats=...)`` or
  adding the ``IMAGEFIELD_FORMATS`` setting. The latter overrides the
  former if given.
- Convert template code to access the new properties (e.g.
  ``instance.image.square`` instead of ``instance.image.crop.200x200``
  when using the ``IMAGEFIELD_FORMATS`` setting below).
- When using django-imagefield with a PPOI, make sure that the PPOI
  field is also added to ``ModelAdmin`` or ``InlineModelAdmin``
  fieldsets, otherwise you'll just see the image, but no PPOI picker.
  Contrary to django-versatileimagefield the PPOI field is editable
  itself, which avoids apart from other complexities a pitfall with
  inline form change detection.
- Add ``"imagefield"`` to ``INSTALLED_APPS``.

If you used e.g. ``instance.image.crop.200x200`` and
``instance.image.thumbnail.800x500`` before, you should add the
following setting:

.. code-block:: python

    IMAGEFIELD_FORMATS = {
        # image field path, lowercase
        'yourapp.yourmodel.image': {
            'square': ['default', ('crop', (200, 200))],
            'full': ['default', ('thumbnail', (800, 500))],

            # The 'full' spec is equivalent to the following format
            # specification in terms of image file produced (the
            # resulting file name is different though):
            # 'full': [
            #     'autorotate', 'process_jpeg', 'process_png',
            #     'process_gif', 'autorotate',
            #     ('thumbnail', (800, 500)),
            # ],
            # Note that the exact list of default processors may
            # change in the future.
        },
    }

After running ``./manage.py process_imagefields`` once you can now
use use ``instance.image.square`` and ``instance.image.thumbnail`` in
templates instead. Note that the properties on the ``image`` file do by
design not check whether thumbs exist.


Image processors
================

django-imagefield uses an image processing pipeline modelled after
Django's middleware.

The following processors are available out of the box:

- ``autorotate``: Autorotates an image by reading the EXIF data.
- ``process_jpeg``: Converts non-RGB images to RGB, activates
  progressive encoding and sets quality to a higher value of 90.
- ``process_png``: Converts PNG images with palette to RGBA.
- ``process_gif``: Preserves transparency and palette data in resized
  images.
- ``preserve_icc_profile``: As the name says.
- ``thumbnail``: Resizes images to not exceed a bounding box.
- ``crop``: Crops an image to the given dimensions, also takes the PPOI
  (primary point of interest) information into account if provided.
- ``default``: The combination of ``autorotate``, ``process_jpeg``,
  ``process_gif``, ``process_png`` and ``preserve_icc_profile``.
  Additional default processors may be added in the future. It is
  recommended to use ``default`` instead of adding the processors
  one-by-one.

Processors can be specified either using their name alone, or if they
take arguments, using a tuple where the first entry is the processors'
name and the rest are positional arguments.

You can easily register your own processors or even override built-in
processors if you want to:

.. code-block:: python

    from imagefield.processing import register

    # You could also write a class with a __call__ method, but I really
    # like the simplicity of functions.

    @register
    def my_processor(get_image, ...):
        def processor(image, context):
            # read some information from the image...
            # or maybe modify it, but it's mostly recommended to modify
            # the image after calling get_image

            image = get_image(image, context)

            # modify the image, and return it...
            modified_image = ...
            # maybe modify the context...
            return modified_image
        return processor

The processor's name is taken directly from the registered object.

An example processor which converts images to grayscale would look as
follows:

.. code-block:: python

    from PIL import ImageOps
    from imagefield.processing import register

    @register
    def grayscale(get_image):
        def processor(image, context):
            image = get_image(image, context)
            return ImageOps.grayscale(image)
        return processor

Now include ``"grayscale"`` in the processing spec for the image where
you want to use it.


The processing context
======================

The ``context`` is a namespace with the following attributes (feel free
to add your own):

- ``processors``: The list of processors.
- ``name``: The name of the resulting image relative to its storages'
  root.
- ``extension``: The extension of the source and target.
- ``ppoi``: The primary point of interest as a list of two floats
  between 0 and 1.
- ``save_kwargs``: A dictionary of keyword arguments to pass to
  ``PIL.Image.save``.

The ``ppoi``, ``extension``, ``processors`` and ``name`` attributes
cannot be modified when running processors anymore. Under some
circumstances ``extension`` and ``name`` will not even be there.

If you want to modify the extension or file type, or create a different
processing pipeline depending on facts not known when configuring
settings you can use a callable instead of the list of processors. The
callable will receive the fieldfile and the context instance and must at
least set the context's ``processors`` attribute to something sensible.
Just as an example here's an image field which always returns JPEG
thumbnails:

.. code-block:: python

    from imagefield.processing import register

    @register
    def force_jpeg(get_image):
        def processor(image, context):
            image = get_image(image, context)
            context.save_kwargs["format"] = "JPEG"
            context.save_kwargs["quality"] = 90
            return image
        return processor

    def jpeg_processor_spec(fieldfile, context):
        context.extension = ".jpg"
        context.processors = [
            "force_jpeg",
            "autorotate",
            ("thumbnail", (200, 200)),
        ]

    class Model(...):
        image = ImageField(..., formats={"thumb": jpeg_processor_spec})

Of course you can also access the model instance through the field file
by way of its ``fieldfile.instance`` attribute and use those
informations to customize the pipeline.


Development
===========

django-imagefield uses flake8 and black to keep the code clean and
formatted. Run both using tox_:

.. code-block:: bash

    tox -e style

The easiest way to build the documentation and run the test suite is
also by using tox_:

.. code-block:: bash

    tox -e docs  # Open docs/build/html/index.html
    tox -e tests


.. _documentation: https://django-imagefield.readthedocs.io/en/latest/
.. _Pillow: https://pillow.readthedocs.io/en/latest/
.. _tox: https://tox.readthedocs.io/
