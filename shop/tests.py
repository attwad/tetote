from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation
from unittest.mock import patch
import datetime
import json
from .models import Brand, Product, Yakikata, ProductType


class ProductModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Bizen", slug="bizen")
        self.yakikata = Yakikata.objects.create(name="Yakikata 1", slug="y1")
        self.type = ProductType.objects.create(name="Type 1", slug="t1")
        self.product = Product.objects.create(
            stripe_product_id="prod_123",
            stripe_price_id="price_123",
            name="Vase",
            slug="vase",
            price=10000,
            stock_quantity=5,
            brand=self.brand,
            yakikata=self.yakikata,
            product_type=self.type,
        )

    def test_price_in_chf(self):
        self.assertEqual(self.product.price_in_chf, 100.0)

    def test_is_in_stock(self):
        self.assertTrue(self.product.is_in_stock)
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_in_stock)

    def test_is_recently_added(self):
        self.assertTrue(self.product.is_recently_added)
        # Test 61 days ago
        self.product.date_added = timezone.now() - datetime.timedelta(days=61)
        self.product.save()
        self.assertFalse(self.product.is_recently_added)


class TranslationTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(
            name_en="Bizen English", name_fr="Bizen French", slug="bizen"
        )

    def test_brand_translation(self):
        with translation.override("en"):
            self.assertEqual(self.brand.name, "Bizen English")

        with translation.override("fr"):
            self.assertEqual(self.brand.name, "Bizen French")


class ShopViewTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Bizen", slug="bizen")
        self.product = Product.objects.create(
            stripe_product_id="prod_1",
            stripe_price_id="price_1",
            name="Brand Product",
            slug="brand-product",
            price=1000,
            stock_quantity=5,
            brand=self.brand,
        )
        self.unbranded_product = Product.objects.create(
            stripe_product_id="prod_2",
            stripe_price_id="price_2",
            name="Unbranded Product",
            slug="unbranded-product",
            price=2000,
            stock_quantity=2,
        )

    def test_product_list_view(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brand Product")
        self.assertContains(response, "Unbranded Product")

    def test_product_detail_view(self):
        url = reverse("shop:product_detail", kwargs={"product_slug": self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brand Product")

    def test_unbranded_product_detail_view(self):
        url = reverse(
            "shop:product_detail", kwargs={"product_slug": self.unbranded_product.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unbranded Product")

    def test_product_list_filter(self):
        url = reverse("shop:product_list") + "?brand=bizen"
        response = self.client.get(url)
        self.assertContains(response, "Brand Product")
        self.assertNotContains(response, "Unbranded Product")


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
        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], "https://checkout.stripe.com/test")

    def test_create_checkout_session_out_of_stock(self):
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
