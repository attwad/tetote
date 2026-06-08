from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(TranslationAdmin):
    list_display = ("title", "date", "is_draft", "created_at")
    list_filter = ("is_draft", "date")
    search_fields = ("title", "content")
    date_hierarchy = "date"
