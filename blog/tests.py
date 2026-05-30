from django.test import TestCase, Client
from django.utils import timezone, translation
from wagtail.models import Page, Locale
from .models import BlogPage


class BlogViewTests(TestCase):
    def setUp(self):
        # Wagtail default root
        self.root_page = Page.objects.get(id=1)

        # Locales
        self.en_locale = Locale.objects.get(language_code="en")
        self.ja_locale, _ = Locale.objects.get_or_create(language_code="ja")

        # Create an English blog post
        self.en_post = BlogPage(
            title="English Post",
            slug="en-post",
            date=timezone.now().date(),
            body=[{"type": "paragraph", "value": "English content"}],
            locale=self.en_locale,
        )
        self.root_page.add_child(instance=self.en_post)
        self.en_post.save_revision().publish()

        # Create a Japanese translation for the same post
        self.ja_post = self.en_post.copy_for_translation(self.ja_locale)
        self.ja_post.title = "Japanese Post"
        self.ja_post.slug = "ja-post"
        self.ja_post.body = [{"type": "paragraph", "value": "Japanese content"}]
        self.ja_post.save_revision().publish()

        # Create a post that only exists in English
        self.en_only_post = BlogPage(
            title="English Only",
            slug="en-only",
            date=timezone.now().date(),
            body=[{"type": "paragraph", "value": "Only EN content"}],
            locale=self.en_locale,
        )
        self.root_page.add_child(instance=self.en_only_post)
        self.en_only_post.save_revision().publish()

        self.client = Client()

    def test_blog_list_en(self):
        """In English, we should see the EN version of both posts."""
        translation.activate("en")
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)
        # Should contain English versions
        self.assertContains(response, "English Post")
        self.assertContains(response, "English Only")
        # Should NOT contain the Japanese version of the first post
        self.assertNotContains(response, "Japanese Post")

    def test_blog_list_ja_fallback(self):
        """In Japanese, we should see the JA version of post 1 and fallback EN version of post 2."""
        translation.activate("ja")
        # Standard Django I18n test client doesn't automatically prepend lang to URL
        # unless we use the prefixed URL.
        response = self.client.get("/ja/blog/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Japanese Post")
        self.assertContains(response, "English Only")
        self.assertNotContains(response, "English Post")

    def test_blog_detail_en(self):
        translation.activate("en")
        response = self.client.get("/blog/en-post/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "English content")

    def test_blog_detail_ja_fallback(self):
        """Requesting the EN slug in JA should still show the JA content."""
        translation.activate("ja")
        response = self.client.get("/ja/blog/en-post/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Japanese content")

    def test_blog_detail_en_only_fallback(self):
        """Requesting the EN-only post in JA should show the EN content."""
        translation.activate("ja")
        response = self.client.get("/ja/blog/en-only/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only EN content")

    def test_draft_visibility(self):
        """Drafts should not be listed."""
        draft_post = BlogPage(
            title="Draft Post",
            slug="draft-post",
            date=timezone.now().date(),
            body=[{"type": "paragraph", "value": "Draft content"}],
            locale=self.en_locale,
            live=False,
        )
        self.root_page.add_child(instance=draft_post)

        translation.activate("en")
        response = self.client.get("/blog/")
        self.assertNotContains(response, "Draft Post")

        # Detail view should 404 for drafts
        response = self.client.get("/blog/draft-post/")
        self.assertEqual(response.status_code, 404)
