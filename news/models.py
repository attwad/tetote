from django.db import models
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet
from django.urls import reverse


@register_snippet
class NewsItem(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    paragraph = RichTextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("paragraph"),
    ]

    def __str__(self):
        return self.title

    def get_admin_display_title(self):
        return self.title

    def get_absolute_url(self):
        return reverse("news_detail", kwargs={"slug": self.slug})

    class Meta:
        verbose_name = "News Item"
        verbose_name_plural = "News Items"
        ordering = ["-created_at"]
