from django import forms
from django.utils.html import format_html


class PPOIWidget(forms.HiddenInput):
    class Media:
        js = ('imagefield/ppoi.js',)


class PreviewMixin(object):
    def render(self, name, value, attrs=None, renderer=None):
        widget = super().render(name, value, attrs=attrs, renderer=renderer)

        return format_html(
            '<div class="imagefield">'
            '<div class="imagefield-preview">Preview</div>'
            '<div class="imagefield-widget">{widget}</div>'
            '</div>',
            widget=widget,
        )


def with_preview(widget):
    return type(
        '%sWithPreview' % widget.__name__,
        (PreviewMixin, widget),
        {},
    )
