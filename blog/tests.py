from wagtail.test.utils import WagtailPageTestCase
from wagtail.models import Page
from .models import BlogIndexPage, BlogPage
import datetime


class BlogTests(WagtailPageTestCase):
    def setUp(self):
        # Get the root page
        # In a standard Wagtail setup, the root page is created by migrations
        self.root = Page.objects.get(id=1).get_first_child()

        # Create Blog Index Page
        self.index = BlogIndexPage(title="Blog", slug="blog")
        self.root.add_child(instance=self.index)

        # Create Blog Page
        self.post = BlogPage(
            title="Test Post",
            slug="test-post",
            date=datetime.date.today(),
            body=[("paragraph", "Hello world")],
        )
        self.index.add_child(instance=self.post)

    def test_blog_index_view(self):
        response = self.client.get(self.index.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")

    def test_blog_page_view(self):
        response = self.client.get(self.post.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")
        self.assertContains(response, "Hello world")
