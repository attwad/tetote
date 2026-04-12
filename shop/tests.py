from django.test import TestCase
from django.urls import reverse
from django.utils import translation
from unittest.mock import patch
import json
from .models import Brand, Product, Glaze, ProductType, StoreSettings


class LanguageSwitcherTests(TestCase):
    def test_language_switcher_presence(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for desktop switcher (uppercase current language)
        self.assertContains(response, "EN")
        # Check for form action
        self.assertContains(response, reverse("set_language"))
        # Check for other languages in the switcher
        for lang_code, lang_name in [
            ("de", "German"),
            ("fr", "French"),
            ("ja", "Japanese"),
        ]:
            self.assertContains(response, lang_code.upper())

    def test_language_switch_en_to_fr(self):
        # When prefix_default_language=False, English is / and French is /fr/
        url = "/i18n/setlang/"
        data = {"language": "fr", "next": "/"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        # Django's set_language should use translate_url to change / to /fr/
        self.assertEqual(response.url, "/fr/")

    def test_language_switch_fr_to_en(self):
        url = "/fr/i18n/setlang/"
        data = {"language": "en", "next": "/fr/"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        # Django's set_language should use translate_url to change /fr/ to /
        self.assertEqual(response.url, "/")


class ProductModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Bizen", slug="bizen")
        self.glaze = Glaze.objects.create(name="Glaze 1", slug="g1")
        self.type = ProductType.objects.create(name="Type 1", slug="t1")
        self.product = Product.objects.create(
            stripe_product_id="prod_123",
            stripe_price_id="price_123",
            name="Vase",
            slug="vase",
            price=10000,
            stock_quantity=5,
            brand=self.brand,
            glaze=self.glaze,
            product_type=self.type,
        )

    def test_price_in_chf(self):
        self.assertEqual(self.product.price_in_chf, 100.0)

    def test_is_in_stock(self):
        self.assertTrue(self.product.is_in_stock)
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_in_stock)


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

    def test_product_list_filter_glaze(self):
        g = Glaze.objects.create(name="Special", slug="special")
        Product.objects.create(
            stripe_product_id="prod_g",
            stripe_price_id="price_g",
            name="Glaze Product",
            slug="g-prod",
            price=100,
            stock_quantity=1,
            glaze=g,
        )
        url = reverse("shop:product_list") + "?glaze=special"
        response = self.client.get(url)
        self.assertContains(response, "Glaze Product")
        self.assertNotContains(response, "Brand Product")

    def test_admin_help_view_restricted(self):
        url = reverse("shop:admin_help")
        # Non-logged in - should redirect to login
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Logged in as non-staff - should return 403
        from django.contrib.auth.models import User

        User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_help_view_staff(self):
        url = reverse("shop:admin_help")
        from django.contrib.auth.models import User

        User.objects.create_superuser(
            username="admin", password="password", email="admin@test.com"
        )
        self.client.login(username="admin", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Documentation")
        self.assertContains(response, "Quick Links")

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

    def test_brand_filter_only_shows_brands_with_public_products(self):
        # Create a brand with only a private product
        private_brand = Brand.objects.create(name="Private Brand", slug="private-brand")
        Product.objects.create(
            stripe_product_id="prod_private_brand",
            stripe_price_id="price_pb",
            name="Private Brand Product",
            slug="pb-prod",
            price=100,
            stock_quantity=1,
            brand=private_brand,
            public=False,
        )

        # Create a brand with no products at all
        Brand.objects.create(name="Empty Brand", slug="empty-brand")

        url = reverse("shop:product_list")
        response = self.client.get(url)

        self.assertContains(response, "Bizen")  # Has a public product
        self.assertNotContains(response, "Private Brand")
        self.assertNotContains(response, "Empty Brand")

    def test_glaze_filter_only_shows_glazes_with_public_products(self):
        private_glaze = Glaze.objects.create(name="Private Glaze", slug="private-glaze")
        Product.objects.create(
            stripe_product_id="prod_pg",
            stripe_price_id="price_pg",
            name="Private Glaze Product",
            slug="pg-prod",
            price=100,
            stock_quantity=1,
            glaze=private_glaze,
            public=False,
        )
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertNotContains(response, "Private Glaze")

    def test_type_filter_only_shows_types_with_public_products(self):
        private_type = ProductType.objects.create(
            name="Private Type", slug="private-type"
        )
        Product.objects.create(
            stripe_product_id="prod_pt",
            stripe_price_id="price_pt",
            name="Private Type Product",
            slug="pt-prod",
            price=100,
            stock_quantity=1,
            product_type=private_type,
            public=False,
        )
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertNotContains(response, "Private Type")

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
            + "?brand=bizen&brand=seto&glaze=g1&stock=in_stock"
        )
        response = self.client.get(url)
        self.assertEqual(response.context["active_brands"], ["bizen", "seto"])
        self.assertEqual(response.context["active_glazes"], ["g1"])
        self.assertEqual(response.context["total_active_filters"], 4)

    def test_product_list_secondary_image(self):
        from .models import ProductImage

        # Create a product with a main photo and two additional images
        product = Product.objects.create(
            stripe_product_id="prod_with_img",
            stripe_price_id="price_with_img",
            name="Image Product",
            slug="img-prod",
            main_photo="https://example.com/main.jpg",
            price=100,
            stock_quantity=1,
            public=True,
        )
        ProductImage.objects.create(
            product=product, url="https://example.com/main.jpg", order=0
        )
        ProductImage.objects.create(
            product=product, url="https://example.com/secondary.jpg", order=1
        )

        # Create a product without a secondary image
        Product.objects.create(
            stripe_product_id="prod_no_img",
            stripe_price_id="price_no_img",
            name="No Image Product",
            slug="no-img-prod",
            main_photo="https://example.com/only-one.jpg",
            price=100,
            stock_quantity=1,
            public=True,
        )

        url = reverse("shop:product_list")
        response = self.client.get(url)
        content = response.content.decode()

        self.assertContains(response, "product-image-primary")
        self.assertContains(response, "product-image-secondary")

        # Verify that only the product with a secondary image has the class
        # We expect exactly one occurrence of the class in the entire HTML
        self.assertEqual(content.count("has-secondary-image"), 1)


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
        self.assertNotIn("locale", kwargs)

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_locale_japanese(self, mock_create):
        from django.utils import translation

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
