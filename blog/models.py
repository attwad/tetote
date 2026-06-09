from django.db import models
from django.urls import reverse
from markdownx.models import MarkdownxField


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = MarkdownxField(help_text="Markdown supported")
    date = models.DateField(help_text="Publication date shown on the post")
    is_draft = models.BooleanField(
        default=True, help_text="Draft posts are only visible to staff members."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})
