.. _changelog:

Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE**: Changed the filename generation method to
  preserve the filename part of the original file for SEO purposes etc.
  You should run ``process_imagefields --all``, and optionally empty the
  ``__processed__`` folder before doing that if you do not want to keep
  old images around.
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
.. _Next version: https://github.com/matthiask/django-imagefield/compare/0.2...master
