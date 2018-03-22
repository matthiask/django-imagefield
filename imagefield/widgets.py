from django import forms
from django.utils.html import format_html


class PPOIWidget(forms.TextInput):
    class Media:
        css = {'screen': ('imagefield/ppoi.css',)}
        js = ('imagefield/ppoi.js',)


class PreviewMixin(object):
    def render(self, name, value, attrs=None, renderer=None):
        widget = super().render(name, value, attrs=attrs, renderer=renderer)

        print(self, self.field_instance, self.field_instance.ppoi_field)

        return format_html(
            '<div class="imagefield" data-ppoi-id="{ppoi_id}">'
            '<div class="imagefield-preview">'
            '<img class="imagefield-preview-image" src="{url}" alt=""/>'
            '</div>'
            '<div class="imagefield-widget">{widget}</div>'
            '</div>',
            widget=widget,
            url=value.url,
            ppoi_id=self.field_instance.ppoi_field or '',
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
