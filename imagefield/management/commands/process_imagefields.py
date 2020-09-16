from __future__ import division, unicode_literals

import sys

from django.core.management.base import BaseCommand, CommandError

from imagefield.fields import IMAGEFIELDS


def iterator(queryset):
    # Relatively low chunk_size to avoid slowness when having to load
    # width and height for images when instantiating models.
    try:
        return queryset.iterator(chunk_size=100)
    except TypeError:  # Older versions of Django
        return queryset.iterator()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true", dest="all", help="Process all fields."
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Force processing of images even if they exist already.",
        )
        parser.add_argument(
            "--housekeep",
            choices=["blank-on-failure"],
            default="",
            help="Run house-keeping tasks.",
        )
        parser.add_argument(
            "field",
            nargs="*",
            type=str,
            help="Fields to process:\n%s"
            % (", ".join(sorted(f.field_label for f in IMAGEFIELDS)),),
        )

        # TODO --clear for removing previously generated images.

    def handle(self, **options):
        self._fields = self._compile_imagefield_labels(options)

        for field in sorted(IMAGEFIELDS, key=lambda f: f.field_label):
            if field.field_label in self._fields:
                self._process_field(field, options)

    def _compile_imagefield_labels(self, options):
        if options["all"]:
            return type(str("c"), (), {"__contains__": lambda *a: True})()
        elif options["field"]:
            unknown = set(options["field"]).difference(
                f.field_label for f in IMAGEFIELDS
            )
            if unknown:
                raise CommandError(
                    "Unknown imagefields: %s" % (", ".join(sorted(unknown)),)
                )
            return options["field"]
        else:
            self.print_help(sys.argv[0], sys.argv[1])
            sys.exit(1)

    def _process_field(self, field, options):
        queryset = field.model._default_manager.exclude(**{field.name: ""}).order_by(
            "-pk"
        )
        count = queryset.count()
        self.stdout.write(
            "%s - %s objects - %s"
            % (
                field.field_label,
                count,
                ", ".join(sorted(field.formats.keys())) or "<no formats!>",
            )
        )
        self.stdout.write("\r|%s| %s/%s" % (" " * 50, 0, count), ending="")

        if field._fallback:
            self._process_instance(
                field.model(),
                field,
                housekeep=None,
                force=options.get("force"),
            )

        for index, instance in enumerate(iterator(queryset)):
            self._process_instance(
                instance,
                field,
                housekeep=options.get("housekeep"),
                force=options.get("force"),
            )
            progress = "*" * (50 * index // count)
            self.stdout.write(
                "\r|%s| %s/%s" % (progress.ljust(50), index + 1, count), ending=""
            )

            # Save instance once for good measure; fills in width/height
            # if not done already
            instance._skip_generate_files = True
            instance.save()

        self.stdout.write("\r|%s| %s/%s" % ("*" * 50, count, count))

    def _process_instance(self, instance, field, housekeep, **kwargs):
        fieldfile = getattr(instance, field.name)
        for key in field.formats:
            try:
                fieldfile.process(key, **kwargs)
            except Exception as exc:
                self.stderr.write(
                    "Error while processing {} ({}, #{}):\n{}\n".format(
                        fieldfile.name, field.field_label, instance.pk, exc
                    )
                )
                if housekeep == "blank-on-failure":
                    field.save_form_data(instance, "")
