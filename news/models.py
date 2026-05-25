from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel


class NewsIndexPage(Page):
    content_panels = Page.content_panels

    def get_context(self, request):
        context = super().get_context(request)
        # Limit to the latest 5 news items
        newsitems = self.get_children().live().order_by("-first_published_at")[:5]
        context["newsitems"] = newsitems
        return context

    # Restrict child page types
    subpage_types = ["news.NewsItem"]


class NewsItem(Page):
    paragraph = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("paragraph"),
    ]

    # Parent page restrictions
    parent_page_types = ["news.NewsIndexPage"]
    subpage_types = []
