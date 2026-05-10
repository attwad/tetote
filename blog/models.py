from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock


class BlogIndexPage(Page):
    content_panels = Page.content_panels

    def get_context(self, request):
        context = super().get_context(request)
        blogpages = self.get_children().live().order_by("-first_published_at")
        context["blogpages"] = blogpages
        return context


class BlogPage(Page):
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
