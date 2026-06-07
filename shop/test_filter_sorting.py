from django.test import TestCase
from shop.models import Product, Glaze, ProductType, Brand
from django.urls import reverse


class FilterSortingTests(TestCase):
    def setUp(self):
        # Clear existing data from migrations
        Glaze.objects.all().delete()
        ProductType.objects.all().delete()

        # Create a brand
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")

        # Create Glazes
        Glaze.objects.create(name="Z-Last", slug="z-last")
        Glaze.objects.create(name="A-First", slug="a-first")
        Glaze.objects.create(name="Other", slug="other")

        # Create Product Types
        ProductType.objects.create(name="Z-Last Type", slug="z-last-type")
        ProductType.objects.create(name="A-First Type", slug="a-first-type")
        ProductType.objects.create(name="Others", slug="others")

        # Create products to make filters show up (distinct() filter used in view)
        for glaze in Glaze.objects.all():
            Product.objects.create(
                stripe_product_id=f"prod_{glaze.slug}",
                stripe_price_id=f"price_{glaze.slug}",
                name=f"Product {glaze.slug}",
                slug=f"product-{glaze.slug}",
                price=1000,
                brand=self.brand,
                glaze=glaze,
                public=True,
            )

        for ptype in ProductType.objects.all():
            Product.objects.create(
                stripe_product_id=f"prod_{ptype.slug}",
                stripe_price_id=f"price_{ptype.slug}",
                name=f"Product {ptype.slug}",
                slug=f"product-{ptype.slug}",
                price=1000,
                brand=self.brand,
                product_type=ptype,
                public=True,
            )

    def test_glaze_sorting(self):
        response = self.client.get(reverse("shop:product_list"))
        glazes = list(response.context["glazes"])

        # Expected order: A-First, Z-Last, Other
        self.assertEqual(glazes[0].slug, "a-first")
        self.assertEqual(glazes[1].slug, "z-last")
        self.assertEqual(glazes[2].slug, "other")

    def test_product_type_sorting(self):
        response = self.client.get(reverse("shop:product_list"))
        ptypes = list(response.context["product_types"])

        # Expected order: A-First Type, Z-Last Type, Others
        self.assertEqual(ptypes[0].slug, "a-first-type")
        self.assertEqual(ptypes[1].slug, "z-last-type")
        self.assertEqual(ptypes[2].slug, "others")
