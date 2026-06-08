from modeltranslation.translator import register, TranslationOptions
from .models import NewsItem


@register(NewsItem)
class NewsItemTranslationOptions(TranslationOptions):
    fields = ("title", "content")
