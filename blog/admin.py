from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from markdownx.admin import MarkdownxModelAdmin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(TranslationAdmin, MarkdownxModelAdmin):
    list_display = ("title", "date", "is_draft", "created_at")
    list_filter = ("is_draft", "date")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "date"
