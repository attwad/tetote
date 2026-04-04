import os
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
import markdown

register = template.Library()


@register.simple_tag
def include_content(slug):
    """
    Includes a Markdown content fragment based on the current language.
    Searches for templates/shop/content/<slug>/<lang>.md
    """
    lang = get_language()
    templates_dir = settings.TEMPLATES[0]["DIRS"][0]

    # Primary path: e.g. shop/content/about_us/ja.md
    filepath = os.path.join(templates_dir, "shop", "content", slug, f"{lang}.md")

    # Fallback to English if the specific language file doesn't exist
    if not os.path.exists(filepath) and lang != "en":
        filepath = os.path.join(templates_dir, "shop", "content", slug, "en.md")

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            html_content = markdown.markdown(
                content, extensions=["fenced_code", "tables"]
            )
            return mark_safe(html_content)

    return f"Content not found for {slug} ({lang})"
