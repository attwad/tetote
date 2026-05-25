from wagtail.test.utils import WagtailPageTestCase
from wagtail.models import Page
from .models import NewsIndexPage, NewsItem


class NewsTests(WagtailPageTestCase):
    def setUp(self):
        self.root_page = Page.objects.get(id=2)
        self.index_page = NewsIndexPage(title="News", slug="news")
        self.root_page.add_child(instance=self.index_page)

    def test_news_index_page_can_be_created(self):
        self.assertCanCreateAt(Page, NewsIndexPage)

    def test_news_item_can_be_created_under_index(self):
        self.assertCanCreateAt(NewsIndexPage, NewsItem)

    def test_news_item_cannot_be_created_under_root(self):
        self.assertCanNotCreateAt(Page, NewsItem)

    def test_news_index_context_limits_to_5_items(self):
        for i in range(10):
            item = NewsItem(title=f"News {i}", slug=f"news-{i}")
            self.index_page.add_child(instance=item)

        context = self.index_page.get_context(None)
        self.assertEqual(len(context["newsitems"]), 5)

    def test_news_item_rendering(self):
        item = NewsItem(
            title="Test News", slug="test-news", paragraph="<p>Test content</p>"
        )
        self.index_page.add_child(instance=item)
        response = self.client.get(item.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test News")
        self.assertContains(response, "Test content")
