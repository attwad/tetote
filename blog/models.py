from django.db import models
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.models import register_snippet
from django.urls import reverse


@register_snippet
class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    date = models.DateField("Post date")
    body = StreamField(
        [
            (
                "heading",
                blocks.CharBlock(
                    form_template="wagtailadmin/block_forms/heading.html", icon="title"
                ),
            ),
            ("paragraph", blocks.RichTextBlock(icon="pilcrow")),
            ("image", ImageChooserBlock(icon="image")),
        ],
        use_json_field=True,
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("date"),
        FieldPanel("body"),
    ]

    def __str__(self):
        return self.title

    def get_admin_display_title(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})

    class Meta:
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
        ordering = ["-date"]
