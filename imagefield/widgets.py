from django import forms
from django.utils.html import format_html


class PPOIWidget(forms.HiddenInput):
    class Media:
        css = {'screen': ('imagefield/ppoi.css',)}
        js = ('imagefield/ppoi.js',)


class PreviewMixin(object):
    def render(self, name, value, attrs=None, renderer=None):
        widget = super().render(name, value, attrs=attrs, renderer=renderer)

        print(self, self.field_instance, self.field_instance.ppoi_field)

        template = (
            '<div class="imagefield" data-ppoi-id="{ppoi}">'
            '<div class="imagefield-preview">'
            '<img class="imagefield-preview-image" src="{url}" alt=""/>'
            '</div>'
            '<div class="imagefield-widget">{widget}</div>'
            '</div>'
        ) if value else (
            '{widget}'
        )
        return format_html(
            template,
            widget=widget,
            url=value and value.url,
            ppoi=self.field_instance.ppoi_field or '',  # TODO @id, not @name
        )


def with_preview(widget, **attrs):
    return type(
        '%sWithPreview' % widget.__name__,
        (PreviewMixin, widget),
        {
            '__module__': 'imagefield.widgets',
            **attrs,
        },
    )
