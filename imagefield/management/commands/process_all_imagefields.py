from django.core.management.base import BaseCommand

from imagefield.fields import IMAGE_FIELDS


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

    def handle(self, **options):
        filter = None
        if options['field']:
            filter = {}
            for field in options['field']:
                parts = field.lower().split('.')
                filter['.'.join(parts[:2])] = parts[2:]

        for field in IMAGE_FIELDS:
            if filter:
                fields = filter.get(field.model._meta.label_lower)
                if fields is None:
                    continue
                if fields and field.name not in fields:
                    continue

            self.stdout.write('%s: %s' % (
                field.model._meta.label,
                field.name,
            ))

            queryset = field.model._default_manager.all()
            count = queryset.count()
            for index, instance in enumerate(queryset):
                fieldfile = getattr(instance, field.name)
                if fieldfile and fieldfile.name:
                    for key in field.formats:
                        try:
                            fieldfile.process(key, force=options.get('force'))
                        except Exception:
                            pass

                if index % 10 == 0:
                    progress = '*' * int(index / count * 50)
                    self.stdout.write('\r|%s|' % progress.rjust(50), ending='')
            self.stdout.write('\r|%s|' % ('*' * 50,))
