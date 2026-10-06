import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from shop.models import Product, StoreSettings


class StoreSettingsTests(TestCase):
    def setUp(self):
        self.settings = StoreSettings.objects.create(sales_paused=True)
        self.product = Product.objects.create(
            stripe_product_id="prod_test",
            stripe_price_id="price_test",
            name="Test Product",
            slug="test-product",
            price=1000,
            stock_quantity=10,
            public=True,
        )

    def test_sales_paused_prevents_checkout(self):
        with translation.override("en"):
            url = reverse("shop:create_checkout_session")
            data = {"items": [{"price_id": "price_test", "qty": 1}]}
            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                response.json()["error"], "Checkout is temporarily disabled"
            )

    def test_sales_not_paused_allows_checkout(self):
        self.settings.sales_paused = False
        self.settings.save()

        with patch("stripe.checkout.Session.create") as mock_create:
            mock_create.return_value.url = "https://checkout.stripe.com/test"
            url = reverse("shop:create_checkout_session")
            data = {"items": [{"price_id": "price_test", "qty": 1}]}
            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)

    def test_cart_page_shows_paused_message(self):
        with translation.override("en"):
            url = reverse("shop:cart")
            response = self.client.get(url)
            self.assertContains(response, "Checkout Paused")
            self.assertContains(
                response,
                "We have temporarily paused online sales. Please check back later.",
            )

    def test_cart_page_shows_checkout_when_not_paused(self):
        with translation.override("en"):
            self.settings.sales_paused = False
            self.settings.save()
            url = reverse("shop:cart")
            response = self.client.get(url)
            self.assertContains(response, "Checkout")
            self.assertNotContains(response, "Checkout Paused")
