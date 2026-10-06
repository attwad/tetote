import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from shop.models import Product


class CartViewTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            stripe_product_id="prod_cart",
            stripe_price_id="price_cart",
            name="Cart Product",
            slug="cart-product",
            price=1000,
            stock_quantity=10,
            public=True,
        )

    def test_cart_page_view(self):
        url = reverse("shop:cart")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shop/cart.html")

    def test_checkout_success_page_view(self):
        url = reverse("shop:checkout_success")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shop/checkout_success.html")

    def test_product_info_api(self):
        url = reverse("shop:product_info") + "?price_ids[]=price_cart"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()["products"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Cart Product")
        self.assertEqual(data[0]["stock"], 10)


class CheckoutViewTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            stripe_product_id="prod_test",
            stripe_price_id="price_test",
            name="Test Product",
            slug="test-product",
            price=1000,
            stock_quantity=10,
            public=True,
        )

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_success(self, mock_create):
        mock_create.return_value.url = "https://checkout.stripe.com/test"
        url = reverse("shop:create_checkout_session")
        data = {"items": [{"price_id": "price_test", "qty": 2}]}

        with self.settings(STRIPE_SHIPPING_RATES=["shr_test"]):
            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], "https://checkout.stripe.com/test")

        # Verify kwargs
        args, kwargs = mock_create.call_args
        self.assertTrue(kwargs.get("allow_promotion_codes"))
        self.assertEqual(kwargs.get("payment_method_types"), ["card"])
        self.assertNotIn("automatic_payment_methods", kwargs)
        self.assertEqual(
            kwargs.get("shipping_address_collection"), {"allowed_countries": ["CH"]}
        )
        self.assertEqual(
            kwargs.get("shipping_options"), [{"shipping_rate": "shr_test"}]
        )
        self.assertNotIn("locale", kwargs)

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_locale_japanese(self, mock_create):
        mock_create.return_value.url = "https://checkout.stripe.com/test"
        data = {"items": [{"price_id": "price_test", "qty": 1}]}

        with translation.override("ja"):
            url = reverse("shop:create_checkout_session")
            self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )

        args, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get("locale"), "ja")

    def test_create_checkout_session_out_of_stock(self):
        with translation.override("en"):
            url = reverse("shop:create_checkout_session")
            data = {"items": [{"price_id": "price_test", "qty": 11}]}
            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("Only 10 left", response.json()["error"])

    def test_create_checkout_session_empty_cart(self):
        url = reverse("shop:create_checkout_session")
        data = {"items": []}
        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_create_checkout_session_invalid_json(self):
        url = reverse("shop:create_checkout_session")
        response = self.client.post(
            url, data="invalid", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_create_checkout_session_aggregate_quantities(self):
        # Product has 10 in stock. Request 6 + 6 of the same product.
        with translation.override("en"):
            url = reverse("shop:create_checkout_session")
            data = {
                "items": [
                    {"price_id": "price_test", "qty": 6},
                    {"price_id": "price_test", "qty": 6},
                ]
            }
            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("Only 10 left", response.json()["error"])
