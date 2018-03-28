=================
django-imagefield
=================

Version |release|

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
  in the database.
- django-imagefield fails early when image data is incomplete or not
  processable by Pillow_ for some reason.

Replacing existing uses of django-versatileimagefield requires the
following steps:

- ``from imagefield.fields import ImageField as VersatileImageField, PPOIField``
- Specify the image sizes by either providing ``ImageField(formats=...)`` or
  adding the ``IMAGEFIELD_FORMATS`` setting.
- Convert template code to access the new properties.
- When using django-imagefield with a PPOI, make sure that the PPOI
  field is also added to ``ModelAdmin`` or ``InlineModelAdmin``
  fieldsets, otherwise you'll just see the image, but no PPOI picker.

If you used e.g. ``instance.image.crop.200x200`` and
``instance.image.thumbnail.800x500`` before, you should add the
following setting::

    IMAGEFIELD_FORMATS = {
        # image field path, lowercase
        'yourapp.yourmodel.image': {
            'square': ['default', ('crop', (200, 200))],
            'full': ['default', ('thumbnail', (800, 500))],
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
- ``process_gif``: Preserves transparency and palette data in resized
  images.
- ``preserve_icc_profile``: As the name says.
- ``thumbnail``: Resizes images to fit a bounding box.
- ``crop``: Crops an image to the given dimensions, also takes the PPOI
  (primary point of interest) information into account if provided.
- ``default``: The combination of ``autorotate``, ``process_jpeg``,
  ``process_gif`` and ``preserve_icc_profile``. Additional default
  processors may be added in the future. It is recommended to use
  ``default`` instead of adding the processors one-by-one.

Processors can be specified either using their name alone, or if they
take arguments, using a tuple ``(processor_name, args...)``.

You can easily register your own processors or even override built-in
processors if you want to::

    from imagefield.processing import register

    # You could also write a class with a __call__ method, but I really
    # like the simplicity of functions.

    @register
    def my_processor(get_image, args):
        # args is either a list of arguments to the processor or an
        # empty list
        def processor(image, context):
            # read some information from the image...
            # or maybe modify it, but it's mostly recommended to modify
            # the image after calling get_image

            image, context = get_image(image, context)

            # modify the image, and return it...
            modified_image = ...
            # maybe modify the context...
            return modified_image, context
        return processor

The processor's name is taken directly from the registered object.

The ``context`` is a ``types.SimpleNamespace`` containing the following
variables (but feel free to add your own):

- ``ppoi``: The primary point of interest as a list of two floats
  between 0 and 1.
- ``save_kwargs``: A dictionary of keyword arguments to pass to
  ``PIL.Image.save``.

.. include:: ../CHANGELOG.rst

.. _Pillow: https://pillow.readthedocs.io/en/latest/
