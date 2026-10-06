from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from shop.models import Brand, Glaze, Product, ProductType


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
            public=True,
        )

    def test_price_in_chf(self):
        self.assertEqual(self.product.price_in_chf, 100.0)

    def test_is_in_stock(self):
        self.assertTrue(self.product.is_in_stock)
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_in_stock)


class SoonInStockTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")

        # Product 1: In Stock
        self.p_in_stock = Product.objects.create(
            stripe_product_id="prod_in",
            stripe_price_id="price_in",
            name="In Stock Product",
            slug="in-stock",
            price=1000,
            stock_quantity=5,
            brand=self.brand,
            public=True,
        )

        # Product 2: Out of Stock
        self.p_out_stock = Product.objects.create(
            stripe_product_id="prod_out",
            stripe_price_id="price_out",
            name="Out of Stock Product",
            slug="out-of-stock",
            price=1000,
            stock_quantity=0,
            brand=self.brand,
            public=True,
        )

        # Product 3: Soon in Stock
        self.p_soon = Product.objects.create(
            stripe_product_id="prod_soon",
            stripe_price_id="price_soon",
            name="Soon in Stock Product",
            slug="soon-in-stock",
            price=1000,
            stock_quantity=0,
            soon_in_stock=True,
            brand=self.brand,
            public=True,
        )

    def test_product_list_filter_soon(self):
        # Test the 'soon' filter
        response = self.client.get(reverse("shop:product_list") + "?stock=soon")
        self.assertEqual(len(response.context["products"]), 1)
        self.assertEqual(response.context["products"][0].id, self.p_soon.id)

    def test_product_list_display(self):
        response = self.client.get(reverse("shop:product_list"))
        content = response.content.decode()

        # Check for badges
        self.assertIn("Soon in stock", content)
        self.assertIn("Out of Stock", content)

        # Switch to Japanese
        with translation.override("ja"):
            response = self.client.get(reverse("shop:product_list"))
            content = response.content.decode()
            self.assertIn("入荷予定", content)

    def test_product_detail_display(self):
        # Detail view for Soon in Stock
        response = self.client.get(
            reverse("shop:product_detail", kwargs={"product_slug": self.p_soon.slug})
        )
        content = response.content.decode()
        self.assertIn("Soon in stock", content)
        self.assertNotIn("Out of Stock", content)

        # Switch to Japanese
        with translation.override("ja"):
            response = self.client.get(
                reverse(
                    "shop:product_detail", kwargs={"product_slug": self.p_soon.slug}
                )
            )
            content = response.content.decode()
            self.assertIn("入荷予定", content)
