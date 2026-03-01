from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import Post


@admin.register(Post)
class PostAdmin(MarkdownxModelAdmin):
    list_display = ("title", "slug", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "content")
