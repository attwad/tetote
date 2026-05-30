from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock


class BlogPage(Page):
    template = "blog/blog_detail.html"
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

    content_panels = Page.content_panels + [
        FieldPanel("date"),
        FieldPanel("body"),
    ]

    # No parent restriction so it can be placed anywhere,
    # but we'll query all BlogPage objects in our Django view.
    subpage_types = []
