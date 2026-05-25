from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import BlogPost


class BlogSnippetTests(TestCase):
    def setUp(self):
        self.post = BlogPost.objects.create(
            title="Test Post",
            slug="test-post",
            date=timezone.now().date(),
            body=[{"type": "paragraph", "value": "Test content"}],
        )

    def test_blog_list_view(self):
        url = reverse("blog_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")

    def test_blog_detail_view(self):
        url = self.post.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")
        self.assertContains(response, "Test content")

    def test_admin_display_title(self):
        self.assertEqual(self.post.get_admin_display_title(), "Test Post")
