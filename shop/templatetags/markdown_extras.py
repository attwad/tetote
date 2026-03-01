from django import template
from django.utils.safestring import mark_safe
import markdown

register = template.Library()


@register.filter(name="markdownify")
def markdownify(value):
    return mark_safe(markdown.markdown(value, extensions=["fenced_code", "tables"]))
