from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = MarkdownxField(help_text="Markdown supported")
    cover_image = models.ImageField(
        upload_to="blog_covers/",
        blank=True,
        null=True,
        verbose_name=_("Cover Image"),
        help_text=_("Optional cover image for the blog post"),
    )
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

    @property
    def excerpt(self):
        if not self.content:
            return ""
        import markdown
        from django.utils.html import strip_tags

        html_content = markdown.markdown(
            self.content, extensions=["fenced_code", "tables", "nl2br"]
        )
        plain_text = strip_tags(html_content)
        # Normalize whitespace
        plain_text = " ".join(plain_text.split())
        if len(plain_text) > 50:
            temp = plain_text[:50]
            last_space = temp.rfind(" ")
            if last_space != -1:
                return temp[:last_space].rstrip() + "..."
            return temp + "..."
        return plain_text
