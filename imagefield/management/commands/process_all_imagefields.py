from django.core.management.base import BaseCommand

from imagefield.fields import IMAGEFIELDS


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help='Force processing of images even if they exist already.',
        )
        parser.add_argument(
            'field',
            nargs='*',
            type=str,
            help='Process only some fields (app.Model.field or app.Model).',
        )

        # TODO --clear for removing previously generated images.

    def _make_filter(self, fields):
        if not fields:
            self._filter = None
        else:
            self._filter = {}
            for field in fields:
                parts = field.lower().split('.')
                self._filter['.'.join(parts[:2])] = parts[2:]

    def _skip_field(self, field):
        if self._filter is None:
            # Process all fields
            return False
        fields = self._filter.get(field.model._meta.label_lower)
        return fields is None or (fields and field.name not in fields)

    def handle(self, **options):
        self._make_filter(options['field'])

        for field in sorted(IMAGEFIELDS, key=lambda f: f.field_label):
            if self._skip_field(field):
                self.stdout.write('%s - skipped' % (
                    field.field_label,
                ))
                continue

            queryset = field.model._default_manager.all()
            count = queryset.count()
            self.stdout.write('%s - %s objects - %s' % (
                field.field_label,
                count,
                ', '.join(sorted(field.formats.keys())) or '<no formats!>',
            ))
            for index, instance in enumerate(queryset):
                fieldfile = getattr(instance, field.name)
                if fieldfile and fieldfile.name:
                    for key in field.formats:
                        try:
                            fieldfile.process(key, force=options.get('force'))
                        except Exception as exc:
                            self.stdout.write(str(exc))

                if index % 5 == 0:
                    progress = '*' * int(index / count * 50)
                    self.stdout.write(
                        '\r|%s| %s/%s' % (
                            progress.ljust(50),
                            index,
                            count,
                        ),
                        ending='',
                    )

            self.stdout.write('\r|%s| %s/%s' % (
                '*' * 50,
                count,
                count,
            ))
