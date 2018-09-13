from __future__ import unicode_literals

import inspect

from django import forms
from django.core.cache import cache
from django.utils.html import format_html

try:
    from django.forms.boundfield import BoundField
except ImportError:  # pragma: no cover (Django<1.11)
    from django.forms.forms import BoundField


class PPOIWidget(forms.HiddenInput):
    class Media:
        css = {"screen": ("imagefield/ppoi.css",)}
        js = ("imagefield/ppoi.js",)


class PreviewAndPPOIMixin(object):
    def render(self, name, value, attrs=None, **kwargs):
        attrs = attrs or {}
        # Can be dropped once we drop support for Django<2.1
        attrs.setdefault("accept", "image/*")
        widget = super(PreviewAndPPOIMixin, self).render(
            name, value, attrs=attrs, **kwargs
        )

        # name does not require a file, .url does
        if not getattr(value, "name", ""):
            return widget

        # Find our BoundField so that we may access the form instance to
        # finally determine the ID attribute of our PPOI field.
        frame = inspect.currentframe()
        while frame:
            boundfield = frame.f_locals.get("self")
            if isinstance(boundfield, BoundField):
                break
            frame = frame.f_back

        if frame is None:  # pragma: no cover
            # Bail out. I have absolutely no idea why this would ever happen.
            return widget

        del frame

        try:
            ppoi = boundfield.form[boundfield.field.widget.ppoi_field].auto_id
        except (AttributeError, KeyError, TypeError) as exc:
            ppoi = ""

        key = "imagefield-admin-thumb:%s" % value.name
        url = cache.get(key, "")
        if not url:
            try:
                url = value.storage.url(
                    value.process(["default", ("thumbnail", (300, 300))])
                )
                cache.set(key, url, timeout=30 * 86400)

            except Exception:
                pass

        return format_html(
            '<div class="imagefield" data-ppoi-id="{ppoi}">'
            '<div class="imagefield-preview">'
            '<img class="imagefield-preview-image" src="{url}" alt=""/>'
            "</div>"
            '<div class="imagefield-widget">{widget}</div>'
            "</div>",
            widget=widget,
            url=url,
            ppoi=ppoi,
        )


def with_preview_and_ppoi(widget, **attrs):
    return type(
        str("%sWithPreviewAndPPOI" % widget.__name__),
        (PreviewAndPPOIMixin, widget),
        dict(attrs, __module__="imagefield.widgets"),
    )
