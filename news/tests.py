from django.test import TestCase
from django.utils import timezone
from .models import NewsItem


class NewsTests(TestCase):
    def test_news_item_creation(self):
        item = NewsItem.objects.create(
            title="News", content="Content", date=timezone.now().date()
        )
        self.assertEqual(str(item), "News")
