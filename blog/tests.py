from wagtail.test.utils import WagtailPageTestCase
from wagtail.models import Page
from django.utils import timezone
from .models import BlogIndexPage, BlogPage


class BlogTests(WagtailPageTestCase):
    def setUp(self):
        self.root_page = Page.objects.get(id=2)
        self.index_page = BlogIndexPage(title="Blog", slug="blog")
        self.root_page.add_child(instance=self.index_page)

    def test_blog_index_page_can_be_created(self):
        self.assertCanCreateAt(Page, BlogIndexPage)

    def test_blog_page_can_be_created_under_index(self):
        self.assertCanCreateAt(BlogIndexPage, BlogPage)

    def test_blog_page_cannot_be_created_under_root(self):
        self.assertCanNotCreateAt(Page, BlogPage)

    def test_blog_page_rendering(self):
        post = BlogPage(
            title="Test Post",
            slug="test-post",
            date=timezone.now().date(),
            body=[{"type": "paragraph", "value": "Test content"}],
        )
        self.index_page.add_child(instance=post)
        response = self.client.get(post.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")
        self.assertContains(response, "Test content")
