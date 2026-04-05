import os
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from shop.models import Brand


class BrandDetailViewTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(
            name="Test Brand",
            slug="test-brand",
            content_slug="brands/test-brand",
        )
        # Create a dummy markdown file for testing
        templates_dir = settings.TEMPLATES[0]["DIRS"][0]
        self.content_dir = os.path.join(
            templates_dir, "shop", "content", "brands", "test-brand"
        )
        os.makedirs(self.content_dir, exist_ok=True)
        self.en_file = os.path.join(self.content_dir, "en.md")
        with open(self.en_file, "w", encoding="utf-8") as f:
            f.write("# Test Brand Content\nThis is a test description.")

    def tearDown(self):
        # Clean up dummy markdown file
        if os.path.exists(self.en_file):
            os.remove(self.en_file)
        if os.path.exists(self.content_dir):
            os.removedirs(self.content_dir)

    def test_brand_detail_view_status_code(self):
        url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_brand_detail_view_template(self):
        url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        response = self.client.get(url)
        self.assertTemplateUsed(response, "shop/brand_detail.html")

    def test_brand_detail_view_context(self):
        url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        response = self.client.get(url)
        self.assertEqual(response.context["brand"], self.brand)

    def test_brand_detail_view_content(self):
        url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        response = self.client.get(url)
        self.assertContains(response, self.brand.name)
        self.assertContains(response, "Test Brand Content")
        self.assertContains(response, "This is a test description.")

    def test_brand_detail_view_404(self):
        url = reverse("shop:brand_detail", kwargs={"brand_slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_product_list_links_to_brand(self):
        """Test that the product list page contains a link to the brand story."""
        from .models import Product

        Product.objects.create(
            stripe_product_id="prod_link_test",
            stripe_price_id="price_link_test",
            name="Linked Product",
            slug="linked-product",
            price=1000,
            stock_quantity=5,
            brand=self.brand,
            public=True,
        )
        url = reverse("shop:product_list")
        response = self.client.get(url)
        brand_url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        self.assertContains(response, f'href="{brand_url}"')

    def test_product_detail_links_to_brand(self):
        """Test that the product detail page contains a link to the brand story."""
        from .models import Product

        product = Product.objects.create(
            stripe_product_id="prod_detail_link_test",
            stripe_price_id="price_detail_link_test",
            name="Detail Linked Product",
            slug="detail-linked-product",
            price=1000,
            stock_quantity=5,
            brand=self.brand,
            public=True,
        )
        url = reverse("shop:product_detail", kwargs={"product_slug": product.slug})
        response = self.client.get(url)
        brand_url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        self.assertContains(response, f'href="{brand_url}"')

    def test_brand_detail_view_collection_link(self):
        """Test that the 'View the Collection' button links to the filtered product list."""
        url = reverse("shop:brand_detail", kwargs={"brand_slug": self.brand.slug})
        response = self.client.get(url)
        filter_url = reverse("shop:product_list") + f"?brand={self.brand.slug}"
        self.assertContains(response, f'href="{filter_url}"')
