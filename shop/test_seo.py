from django.test import TestCase
from django.urls import reverse


class SEOTests(TestCase):
    def test_robots_txt(self):
        url = reverse("robots_txt")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn("User-agent: *", response.content.decode())
        self.assertIn(
            "Sitemap: http://testserver/sitemap.xml", response.content.decode()
        )

    def test_sitemap_xml(self):
        # We need at least one item to see it in the sitemap
        from .models import Product

        Product.objects.create(
            stripe_product_id="prod_seo",
            stripe_price_id="price_seo",
            name="SEO Vase",
            slug="seo-vase",
            price=1000,
            stock_quantity=1,
            public=True,
        )

        url = reverse("django.contrib.sitemaps.views.sitemap")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        content = response.content.decode()
        self.assertIn("/products/seo-vase/", content)
        self.assertIn("/fr/products/seo-vase/", content)
        self.assertIn("/de/products/seo-vase/", content)
        self.assertIn("/ja/products/seo-vase/", content)
