from django.test import TestCase
from django.urls import reverse
from .models import Post


class BlogViewTests(TestCase):
    def setUp(self):
        self.post = Post.objects.create(
            title="Test Post", slug="test-post", content="Hello **world**"
        )

    def test_post_list_view(self):
        url = reverse("blog:post_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")

    def test_post_list_view_empty(self):
        Post.objects.all().delete()
        url = reverse("blog:post_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We are sorry, there are no blog posts yet.")

    def test_post_detail_view(self):
        url = reverse("blog:post_detail", kwargs={"slug": self.post.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")
        self.assertContains(response, "<strong>world</strong>")
