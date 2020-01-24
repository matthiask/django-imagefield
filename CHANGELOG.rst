.. _changelog:

Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

`0.10`_ (2020-01-24)
~~~~~~~~~~~~~~~~~~~~

- Added an experimental fallback facility for optional image fields.
- Allowed processor specs to return another processor spec in turn. This
  allows layering processor specs.
- Changed the image field to set image file's extensions depending on
  their image type. For example, a GIF uploaded as ``example.png`` will
  automatically be saved as ``example.gif``.
- Improved test coverage a bit.


`0.9`_ (2020-01-22)
~~~~~~~~~~~~~~~~~~~

- Fixed crashes because of image fields with ``None`` values.
- Fixed a case where an unsupported image was not detected early enough.
- Added a ``IMAGEFIELD_SILENTFAILURE`` setting for silent failure when
  processing images crashes. The default value of this setting is
  obviously ``False``. This is mostly useful when adding
  ``django-imagefield`` to a project which already has images (which may
  not be processible by Pillow).
- Fixed the image verification to accept CMYK images again.
- Added Django 3.0 to the test matrix.
- Removed Python 3.4 from the test matrix.
- Ensure that ``icc_profile`` isn't passed if it is falsy. The WebP
  encoder didn't like ``icc_profile=None``.
- Stopped including image fields of swapped models in ``IMAGEFIELDS``.
- Replaced ``ugettext*`` with ``gettext*``.
- Added an experimental websafe processor spec.


`0.8`_ (2019-06-21)
~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE**: Changed processing to pass additional
  processors' arguments as positional arguments instead of as a single
  list. This change only affects custom processors, no changes are
  necessary for users of the library, except if for example you passed
  arguments to processors such as ``default``, ``autorotate`` etc.
- Fixed a test to assume less about the error message for corrupt
  images.
- Localize the corrupt image validation errors.
- Stopped calling the storage's ``delete()`` method for non-existing
  images.
- Made the field resilient against NULL values from the database.


`0.7`_ (2018-10-18)
~~~~~~~~~~~~~~~~~~~

- Made error reporting in ``process_imagefields`` include more info.
- Made image field validation catch errors while determining the image
  dimension too.
- Fixed a problem where older versions of Django didn't allow specifying
  the chunk size for iterating over querysets.
- Modified django-imagefield's internals to allow changing the type and
  extension of generated images by way of dynamically specifying the
  processing pipeline.
- Changed the API of the ``get_image`` callable in processors to only
  return the image without the context (since the context is mutable and
  available already).


`0.6`_ (2018-09-13)
~~~~~~~~~~~~~~~~~~~

- Fixed a crash where unpickling image fields would fail.
- Changed ``process_imagefields`` to skip exclude model instances with
  an empty image field.
- Changed the ``thumbnail`` processor to not upscale images.
- Made ``process_imagefields`` not load the whole queryset at once to
  avoid massive slowdowns while determining the width and height of
  images (if those fields aren't filled in yet).
- Added housekeeping options to ``process_imagefields``. The only method
  implemented right now is ``--housekeep blank-on-failure`` which
  empties image fields where processing fails.
- Changed ``process_imagefields`` to process items in a deterministic
  order.
- Clarified the processors spec documentation a bit and added an example
  how to write a processor of your own.


`0.5`_ (2018-08-15)
~~~~~~~~~~~~~~~~~~~

- Dropped support for using image fields without associated height and
  width fields, because it is almost (?) always a really bad idea
  performance-wise.
- Fixed a bug where processed image names on Python 2 were different
  than those generated using Python 3. This bug affects only
  installations still using Python 2. Rerun ``./manage.py
  process_imagefields --all`` after upgrading.


`0.4`_ (2018-08-13)
~~~~~~~~~~~~~~~~~~~

- Added compatibility with Django 1.8 for prehistoric projects.
- Polished tests and docs a bit.


`0.3`_ (2018-05-29)
~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE**: Changed the filename generation method to
  preserve the filename part of the original file for SEO purposes etc.
  You should run ``./manage.py process_imagefields --all``, and
  optionally empty the ``__processed__`` folder before doing that if you
  do not want to keep old images around.
- Improved progress reporting in ``process_imagefields``.
- Added a call to ``instance.save()`` in ``process_imagefields`` so that
  width and height fields are saved (if any).
- Added ``accept="image/*"`` attribute to the file upload widget.
- Replaced the full image in the admin widget with an ad-hoc thumbnail.
- Fixed a bug where blank imagefields would not work correctly in the
  administration interface.
- Switched the preferred quote to ``"`` and started using `black
  <https://pypi.org/project/black/>`_ to automatically format Python
  code.


`0.2`_ (2018-03-28)
~~~~~~~~~~~~~~~~~~~

- Rename management command to ``process_imagefields``, and add
  ``--all`` option to process all imagefields.
- Fixed a bug where not all image fields from base classes were picked
  up for processing by ``process_imagefields``.
- Added the ``IMAGEFIELD_AUTOGENERATE`` setting, which can be set to a
  list of image fields (in ``app.model.field`` notation, lowercased) to
  only activate automatic processing of images upon model creation and
  update for a few specific fields, or to ``False`` to disable this
  functionality for all fields.
- Added system checks which warn when ``width_field`` and
  ``height_field`` are not used.
- Changed ``process_imagefields`` to process image fields in
  alphabetic order. Also, made cosmetic changes to the progress output.
- Added a test which verifies that generating processed image URLs is
  not slowed down by potentially slow storages (e.g. cloud storage)
- Fixed the PPOI JavaScript to not crash when some imagefields have no
  corresponding PPOI input.


`0.1`_ (2018-03-27)
~~~~~~~~~~~~~~~~~~~

- First release that should be fit for public consumption.


.. _0.1: https://github.com/matthiask/django-imagefield/commit/013b9a810fa6
.. _0.2: https://github.com/matthiask/django-imagefield/compare/0.1...0.2
.. _0.3: https://github.com/matthiask/django-imagefield/compare/0.2...0.3
.. _0.4: https://github.com/matthiask/django-imagefield/compare/0.3...0.4
.. _0.5: https://github.com/matthiask/django-imagefield/compare/0.4...0.5
.. _0.6: https://github.com/matthiask/django-imagefield/compare/0.5...0.6
.. _0.7: https://github.com/matthiask/django-imagefield/compare/0.6...0.7
.. _0.8: https://github.com/matthiask/django-imagefield/compare/0.7...0.8
.. _0.9: https://github.com/matthiask/django-imagefield/compare/0.8...0.9
.. _0.10: https://github.com/matthiask/django-imagefield/compare/0.9...0.10
.. _Next version: https://github.com/matthiask/django-imagefield/compare/0.10...master
