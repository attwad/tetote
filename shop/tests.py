from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation
from unittest.mock import patch
import datetime
import json
from .models import Brand, Product, Yakikata, ProductType, StoreSettings


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
        url = reverse("shop:create_checkout_session")
        data = {"items": [{"price_id": "price_test", "qty": 1}]}
        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Checkout is temporarily disabled")

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
        url = reverse("shop:cart")
        response = self.client.get(url)
        self.assertContains(response, "Checkout Paused")
        self.assertContains(
            response,
            "We have temporarily paused online sales. Please check back later!",
        )

    def test_cart_page_shows_checkout_when_not_paused(self):
        self.settings.sales_paused = False
        self.settings.save()
        url = reverse("shop:cart")
        response = self.client.get(url)
        self.assertContains(response, "Checkout")
        self.assertNotContains(response, "Checkout Paused")


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

    def test_product_list_filter_yakikata(self):
        y = Yakikata.objects.create(name="Special", slug="special")
        Product.objects.create(
            stripe_product_id="prod_y",
            stripe_price_id="price_y",
            name="Yakikata Product",
            slug="y-prod",
            price=100,
            stock_quantity=1,
            yakikata=y,
            public=True,
        )
        url = reverse("shop:product_list") + "?yakikata=special"
        response = self.client.get(url)
        self.assertContains(response, "Yakikata Product")
        self.assertNotContains(response, "Brand Product")

    def test_product_list_filter_type(self):
        t = ProductType.objects.create(name="Bowl", slug="bowl")
        Product.objects.create(
            stripe_product_id="prod_t",
            stripe_price_id="price_t",
            name="Type Product",
            slug="t-prod",
            price=100,
            stock_quantity=1,
            product_type=t,
            public=True,
        )
        url = reverse("shop:product_list") + "?type=bowl"
        response = self.client.get(url)
        self.assertContains(response, "Type Product")
        self.assertNotContains(response, "Brand Product")

    def test_product_detail_private(self):
        Product.objects.create(
            stripe_product_id="prod_private",
            stripe_price_id="price_p",
            name="Private",
            slug="private",
            price=100,
            stock_quantity=1,
            public=False,
        )
        url = reverse("shop:product_detail", kwargs={"product_slug": "private"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_product_list_filter_stock(self):
        # Create out of stock product
        Product.objects.create(
            stripe_product_id="prod_oos",
            stripe_price_id="price_oos",
            name="Out of Stock Prod",
            slug="oos-prod",
            price=100,
            stock_quantity=0,
            public=True,
        )
        url = reverse("shop:product_list") + "?stock=in_stock"
        response = self.client.get(url)
        self.assertContains(response, "Brand Product")
        self.assertNotContains(response, "Out of Stock Prod")

    def test_product_list_filter_new(self):
        # Create old product (70 days ago)
        old_p = Product.objects.create(
            stripe_product_id="prod_old",
            stripe_price_id="price_old",
            name="Old Product",
            slug="old-prod",
            price=100,
            stock_quantity=1,
            public=True,
        )
        old_p.date_added = timezone.now() - datetime.timedelta(days=70)
        old_p.save()

        # Test filter
        url = reverse("shop:product_list") + "?new=true"
        response = self.client.get(url)
        self.assertContains(response, "Brand Product")
        self.assertNotContains(response, "Old Product")

    def test_product_list_multi_filter(self):
        b2 = Brand.objects.create(name="Seto", slug="seto")
        Product.objects.create(
            stripe_product_id="prod_b2",
            stripe_price_id="price_b2",
            name="Seto Product",
            slug="seto-prod",
            price=100,
            stock_quantity=1,
            brand=b2,
            public=True,
        )
        # Filter for both brands
        url = reverse("shop:product_list") + "?brand=bizen&brand=seto"
        response = self.client.get(url)
        self.assertContains(response, "Brand Product")
        self.assertContains(response, "Seto Product")

    def test_product_list_context_active_filters(self):
        url = (
            reverse("shop:product_list")
            + "?brand=bizen&brand=seto&yakikata=y1&stock=in_stock&new=true"
        )
        response = self.client.get(url)
        self.assertEqual(response.context["active_brands"], ["bizen", "seto"])
        self.assertEqual(response.context["active_yakikatas"], ["y1"])
        self.assertEqual(response.context["total_active_filters"], 5)


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
        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], "https://checkout.stripe.com/test")

        # Verify that allow_promotion_codes is True
        args, kwargs = mock_create.call_args
        self.assertTrue(kwargs.get("allow_promotion_codes"))

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

    def test_create_checkout_session_aggregate_quantities(self):
        # Product has 10 in stock. Request 6 + 6 of the same product.
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
