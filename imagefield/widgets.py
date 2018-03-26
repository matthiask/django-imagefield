import inspect

from django import forms
from django.utils.html import format_html


class PPOIWidget(forms.HiddenInput):
    class Media:
        css = {'screen': ('imagefield/ppoi.css',)}
        js = ('imagefield/ppoi.js',)


class PreviewAndPPOIMixin(object):
    def render(self, name, value, attrs=None, renderer=None):
        widget = super().render(name, value, attrs=attrs, renderer=renderer)
        if not value:
            return widget

        # find our BoundField so that we may access the form etc.
        for frameinfo in inspect.stack():
            self_ = frameinfo.frame.f_locals.get('self')
            if isinstance(self_, forms.BoundField):
                boundfield = self_
                break

        else:  # pragma: no cover
            # Bail out. I have absolutely no idea why this would ever happen.
            return widget

        try:
            ppoi = boundfield.form[boundfield.field.widget.ppoi_field].auto_id
        except (AttributeError, KeyError, TypeError):
            ppoi = ''

        return format_html(
            '<div class="imagefield" data-ppoi-id="{ppoi}">'
            '<div class="imagefield-preview">'
            '<img class="imagefield-preview-image" src="{url}" alt=""/>'
            '</div>'
            '<div class="imagefield-widget">{widget}</div>'
            '</div>',
            widget=widget,
            url=getattr(value, 'url', ''),
            ppoi=ppoi,
        )


def with_preview_and_ppoi(widget, **attrs):
    return type(
        '%sWithPreviewAndPPOI' % widget.__name__,
        (PreviewAndPPOIMixin, widget),
        {
            '__module__': 'imagefield.widgets',
            **attrs,
        },
    )
