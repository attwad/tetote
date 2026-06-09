from django.db import models
from markdownx.models import MarkdownxField


class NewsItem(models.Model):
    title = models.CharField(max_length=255)
    content = MarkdownxField(help_text="Markdown supported")
    date = models.DateField(help_text="Publication date shown on the post")
    is_draft = models.BooleanField(
        default=True, help_text="Draft news items are only visible to staff members."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "News Item"
        verbose_name_plural = "News Items"

    def __str__(self):
        return self.title
