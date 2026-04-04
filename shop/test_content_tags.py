import os
from unittest.mock import patch, mock_open
from django.test import TestCase
from django.utils import translation
from shop.templatetags.content_tags import include_content


class ContentTagsTest(TestCase):
    def setUp(self):
        self.slug = "test_page"
        # We need to mock settings.TEMPLATES[0]["DIRS"][0]
        # but since we are mocking os.path.exists and open,
        # the actual value of templates_dir doesn't matter much for the logic.

    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="# Hello\nThis is test content.",
    )
    def test_include_content_en(self, mock_file, mock_exists):
        """Test including English content when it exists."""
        # Setup: 'en.md' exists
        mock_exists.side_effect = lambda path: path.endswith("en.md")

        with translation.override("en"):
            result = include_content(self.slug)

        self.assertIn("<h1>Hello</h1>", result)
        self.assertIn("<p>This is test content.</p>", result)
        # Verify it looked for the correct file
        expected_path = os.path.join("shop", "content", self.slug, "en.md")
        self.assertTrue(
            any(expected_path in call[0][0] for call in mock_exists.call_args_list)
        )

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="# Bonjour")
    def test_include_content_fr(self, mock_file, mock_exists):
        """Test including French content when it exists."""
        # Setup: 'fr.md' exists
        mock_exists.side_effect = lambda path: path.endswith("fr.md")

        with translation.override("fr"):
            result = include_content(self.slug)

        self.assertIn("<h1>Bonjour</h1>", result)
        expected_path = os.path.join("shop", "content", self.slug, "fr.md")
        self.assertTrue(
            any(expected_path in call[0][0] for call in mock_exists.call_args_list)
        )

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="# English Fallback")
    def test_include_content_fallback(self, mock_file, mock_exists):
        """Test fallback to English when requested language is missing."""
        # Setup: 'de.md' does NOT exist, but 'en.md' DOES exist
        mock_exists.side_effect = lambda path: path.endswith("en.md")

        with translation.override("de"):
            result = include_content(self.slug)

        self.assertIn("<h1>English Fallback</h1>", result)

        # Count calls that actually target our content directory
        content_calls = [
            call
            for call in mock_exists.call_args_list
            if os.path.join("shop", "content", self.slug) in call[0][0]
        ]
        self.assertEqual(len(content_calls), 2)

    @patch("os.path.exists")
    def test_include_content_not_found(self, mock_exists):
        """Test result when neither specific language nor English exists."""
        # Setup: Nothing exists
        mock_exists.return_value = False

        with translation.override("ja"):
            result = include_content(self.slug)

        self.assertEqual(result, f"Content not found for {self.slug} (ja)")

    def test_markdown_formatting(self):
        """Verify complex markdown renders correctly through the tag."""
        content = "## Subtitle\n- Item 1\n- Item 2\n\n**Bold**"
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=content)):
                result = include_content(self.slug)

        self.assertIn("<h2>Subtitle</h2>", result)
        self.assertIn("<ul>", result)
        self.assertIn("<li>Item 1</li>", result)
        self.assertIn("<strong>Bold</strong>", result)
