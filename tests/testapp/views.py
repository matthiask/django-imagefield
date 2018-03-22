from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html

from feincms3 import plugins
from feincms3.renderer import TemplatePluginRenderer

from .models import HTML, External, Image, Page, RichText, Snippet


renderer = TemplatePluginRenderer()
renderer.register_string_renderer(
    RichText,
    plugins.render_richtext,
)
renderer.register_string_renderer(
    Image,
    lambda plugin: format_html(
        '<figure><img src="{}" alt=""/><figcaption>{}</figcaption></figure>',
        plugin.image.url,
        plugin.caption,
    ),
)
renderer.register_template_renderer(
    Snippet,
    lambda plugin: plugin.template_name,
    lambda plugin, context: {'additional': 'context'},
)
renderer.register_string_renderer(
    External,
    plugins.render_external,
)
renderer.register_string_renderer(
    HTML,
    plugins.render_html,
)


def page_detail(request, path=None):
    page = get_object_or_404(
        Page.objects.active(),
        path=('/%s/' % path) if path else '/',
    )
    page.activate_language(request)

    if page.redirect_to_url or page.redirect_to_page:
        return redirect(page.redirect_to_url or page.redirect_to_page)
    return render(request, page.template.template_name, {
        'page': page,
        'regions': renderer.regions(
            page,
            inherit_from=page.ancestors().reverse(),
        ),
    })
