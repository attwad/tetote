from modeltranslation.translator import register, TranslationOptions
from .models import BlogPost


@register(BlogPost)
class BlogPostTranslationOptions(TranslationOptions):
    fields = ("title", "content")
