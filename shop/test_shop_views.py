from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from shop.models import Brand, Glaze, Product, ProductImage, ProductType


class ShopViewTests(TestCase):
    def setUp(self):
        self.client.cookies.clear()
        with translation.override("en"):
            self.brand = Brand.objects.create(name="Bizen", slug="bizen")
            self.product = Product.objects.create(
                stripe_product_id="prod_1",
                stripe_price_id="price_1",
                name="Brand Product",
                slug="brand-product",
                price=1000,
                stock_quantity=5,
                brand=self.brand,
                public=True,
            )
            self.unbranded_product = Product.objects.create(
                stripe_product_id="prod_2",
                stripe_price_id="price_2",
                name="Unbranded Product",
                slug="unbranded-product",
                price=2000,
                stock_quantity=2,
                public=True,
            )

    def test_product_list_view(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brand Product")
        self.assertContains(response, "Unbranded Product")

    def test_product_detail_view(self):
        with translation.override("en"):
            self.product.description = "Main description"
            self.product.details = "Extra details"
            self.product.save()

            url = reverse(
                "shop:product_detail", kwargs={"product_slug": self.product.slug}
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Brand Product")
            self.assertContains(response, "Description")
            self.assertContains(response, "Main description")
            self.assertContains(response, "Details")
            self.assertContains(response, "Extra details")

    def test_product_detail_view_no_details(self):
        with translation.override("en"):
            self.product.description = "Main description"
            self.product.details = ""
            self.product.save()

            url = reverse(
                "shop:product_detail", kwargs={"product_slug": self.product.slug}
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Description")
            self.assertContains(response, "Main description")
            self.assertNotContains(response, "Details")

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
            public=True,
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
        User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_help_view_staff(self):
        url = reverse("shop:admin_help")
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
        # Create a product with a main photo and two additional images
        product = Product.objects.create(
            stripe_product_id="prod_with_img",
            stripe_price_id="price_with_img",
            name="Image Product",
            slug="img-prod",
            price=100,
            stock_quantity=1,
            public=True,
        )
        ProductImage.objects.create(
            product=product,
            url="https://example.com/main.jpg",
            image_file="product_images/main.jpg",
            order=0,
        )
        ProductImage.objects.create(
            product=product,
            url="https://example.com/secondary.jpg",
            image_file="product_images/secondary.jpg",
            order=1,
        )

        # Create a product without a secondary image
        product_no_img = Product.objects.create(
            stripe_product_id="prod_no_img",
            stripe_price_id="price_no_img",
            name="No Image Product",
            slug="no-img-prod",
            price=100,
            stock_quantity=1,
            public=True,
        )
        ProductImage.objects.create(
            product=product_no_img, url="https://example.com/only-one.jpg", order=0
        )

        url = reverse("shop:product_list")
        response = self.client.get(url)
        content = response.content.decode()

        self.assertContains(response, "product-image-primary")
        self.assertContains(response, "product-image-secondary")

        # Verify that only the product with a secondary image has the class
        self.assertEqual(content.count("has-secondary-image"), 1)
