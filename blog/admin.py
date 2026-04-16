from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin
from .models import Post


@admin.register(Post)
class PostAdmin(TabbedTranslationAdmin):
    list_display = ("title", "slug", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "content")
