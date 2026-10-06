from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from news.models import NewsItem
from shop.models import CarouselImage


class HomeViewTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )

    def test_home_page_rendering(self):
        # Create a news item
        NewsItem.objects.create(
            title="News 1",
            content="Content",
            date=timezone.now().date(),
            is_draft=False,
        )
        # Create a draft news item
        NewsItem.objects.create(
            title="Draft News",
            content="Draft Content",
            date=timezone.now().date(),
            is_draft=True,
        )

        # Create a carousel image with alt text and overlay
        image_content = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;"
        CarouselImage.objects.create(
            image=ContentFile(image_content, name="c1.gif"),
            alt_text_en="Beautiful Vase",
            overlay_image=ContentFile(b"<svg></svg>", name="overlay.svg"),
        )

        url = reverse("shop:home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "News 1")
        self.assertNotContains(response, "Draft News")
        self.assertContains(response, "splide__slide")
        self.assertContains(response, "carousel/c1")
        self.assertContains(response, "Beautiful Vase")
        self.assertContains(response, "overlay")
        self.assertContains(response, ".svg")
        self.assertContains(response, reverse("shop:product_list"))
        self.assertContains(response, "Enter the Shop")

    def test_home_page_staff_visibility(self):
        self.client.login(username="staff", password="password")
        NewsItem.objects.create(
            title="Draft News",
            content="Draft Content",
            date=timezone.now().date(),
            is_draft=True,
        )

        url = reverse("shop:home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft News")
        self.assertContains(response, "Draft")
