from django.test import TestCase
from django.urls import reverse
from .models import NewsItem


class NewsSnippetTests(TestCase):
    def setUp(self):
        self.item = NewsItem.objects.create(
            title="Test News", slug="test-news", paragraph="<p>Test content</p>"
        )

    def test_news_list_view(self):
        url = reverse("news_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test News")

    def test_news_detail_view(self):
        url = self.item.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test News")
        self.assertContains(response, "Test content")

    def test_admin_display_title(self):
        self.assertEqual(self.item.get_admin_display_title(), "Test News")
