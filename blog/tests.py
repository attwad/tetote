from django.test import TestCase, Client
from django.utils import timezone, translation
from django.contrib.auth.models import User
from .models import BlogPost


class BlogViewTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username="normal", password="password"
        )

        # Create a published post with translations
        self.post1 = BlogPost.objects.create(
            title_en="English Post",
            title_ja="Japanese Post",
            slug="post-1",
            content_en="English content",
            content_ja="Japanese content",
            date=timezone.now().date(),
            is_draft=False,
        )

        # Create a draft post
        self.draft_post = BlogPost.objects.create(
            title_en="Draft Post",
            slug="draft-post",
            content_en="Draft content",
            date=timezone.now().date(),
            is_draft=True,
        )

        self.client = Client()

    def test_blog_list_anonymous(self):
        """Anonymous users should only see published posts."""
        translation.activate("en")
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "English Post")
        self.assertNotContains(response, "Draft Post")

    def test_blog_list_staff(self):
        """Staff users should see draft posts."""
        self.client.login(username="staff", password="password")
        translation.activate("en")
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "English Post")
        self.assertContains(response, "Draft Post")
        # Check for the draft badge text (wrapped in translate)
        self.assertContains(response, "Draft")

    def test_blog_detail_anonymous_published(self):
        translation.activate("en")
        response = self.client.get("/blog/post-1/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "English content")

    def test_blog_detail_anonymous_draft(self):
        translation.activate("en")
        response = self.client.get("/blog/draft-post/")
        self.assertEqual(response.status_code, 404)

    def test_blog_detail_staff_draft(self):
        self.client.login(username="staff", password="password")
        translation.activate("en")
        response = self.client.get("/blog/draft-post/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft content")

    def test_blog_translation_ja(self):
        response = self.client.get("/ja/blog/post-1/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Japanese content")

    def test_blog_excerpt(self):
        # Post with short content (no ellipses)
        short_post = BlogPost(content="Short content.")
        self.assertEqual(short_post.excerpt, "Short content.")

        # Post with long content (ellipsed at word boundary)
        long_content = "This is a very long blog post content that should definitely exceed fifty characters in length to test the truncation."
        long_post = BlogPost(content=long_content)
        self.assertEqual(
            long_post.excerpt, "This is a very long blog post content that should..."
        )

        # Post where a word is cut off in the middle
        cut_post = BlogPost(
            content="This is a very long blog post content that shoulddefinitely exceed fifty characters."
        )
        self.assertEqual(
            cut_post.excerpt, "This is a very long blog post content that..."
        )

        # Markdown elements should be stripped
        markdown_post = BlogPost(
            content="**Bold text** and a [link](http://example.com) here."
        )
        self.assertEqual(markdown_post.excerpt, "Bold text and a link here.")

        # Post with exactly 50 characters (no ellipsis)
        exact_50_content = "This string is exactly fifty characters long now!"
        exact_50_post = BlogPost(content=exact_50_content)
        self.assertEqual(exact_50_post.excerpt, exact_50_content)

        # Post with 51 characters (should add ellipsis at word boundary)
        exact_51_content = "This string is exactly fifty characters long now! A"
        exact_51_post = BlogPost(content=exact_51_content)
        self.assertEqual(
            exact_51_post.excerpt,
            "This string is exactly fifty characters long now!...",
        )

        # Post with > 50 characters but no spaces (fallback to char limit truncation + ellipsis)
        no_spaces_content = "A" * 60
        no_spaces_post = BlogPost(content=no_spaces_content)
        self.assertEqual(no_spaces_post.excerpt, ("A" * 50) + "...")
