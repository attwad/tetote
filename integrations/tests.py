import stripe
from django.test import TestCase
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from unittest.mock import patch, MagicMock, PropertyMock
from io import StringIO
from django.core.management import call_command

from shop.models import Product, ProductImage, Brand
from shop.admin import ProductAdmin
from integrations.views import sync_product, sync_price


class MockObject(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def to_dict(self):
        return self


@patch("integrations.views.requests.get")
class StripeIntegrationTest(TestCase):
    @patch("stripe.Price.list")
    @patch("stripe.Product.list")
    def test_sync_stripe_command(
        self, mock_product_list, mock_price_list, mock_requests_get
    ):
        # Mock product list
        mock_p1 = MockObject(
            {
                "id": "prod_1",
                "name": "Stripe Product 1",
                "images": ["http://test.com/img1.jpg"],
                "metadata": {},
                "created": 1700000000,
            }
        )

        mock_product_list.return_value.auto_paging_iter.return_value = [mock_p1]

        # Mock requests.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image content"
        mock_requests_get.return_value = mock_response

        # Mock price list
        mock_price1 = MockObject(
            {
                "id": "price_1",
                "product": "prod_1",
                "unit_amount": 1500,
            }
        )

        mock_price_list.return_value.auto_paging_iter.return_value = [mock_price1]

        out = StringIO()
        call_command("sync_stripe", stdout=out)

        self.assertIn("Stripe sync completed!", out.getvalue())

        product = Product.objects.get(stripe_product_id="prod_1")
        self.assertEqual(product.stripe_name, "Stripe Product 1")
        self.assertEqual(product.price, 1500)
        self.assertEqual(product.stripe_price_id, "price_1")

        # Verify images were downloaded
        self.assertEqual(product.images.count(), 1)
        self.assertTrue(product.images.first().image_file)
        self.assertIn("img1", product.images.first().image_file.name)
        self.assertTrue(product.images.first().image_file.name.endswith(".jpg"))

    def test_sync_product_does_not_overwrite_price(self, mock_requests_get):
        # Create product with existing price
        Product.objects.create(
            stripe_product_id="prod_overwrite_test",
            stripe_price_id="price_fixed",
            name="Original",
            stripe_name="Original",
            slug="original",
            price=9900,
            stock_quantity=5,
            public=True,
        )

        # Update product (no price info in payload)
        product_data = {
            "id": "prod_overwrite_test",
            "name": "Updated Name",
            "images": ["http://test.com/new.jpg"],
            "created": 1700000000,
        }

        sync_product(product_data)

        product = Product.objects.get(stripe_product_id="prod_overwrite_test")
        self.assertEqual(product.stripe_name, "Updated Name")
        # Price must remain unchanged
        self.assertEqual(product.price, 9900)
        self.assertEqual(product.stripe_price_id, "price_fixed")

    def test_sync_product_does_not_overwrite_manual_date(self, mock_requests_get):
        import datetime
        from django.utils import timezone

        # Create product with a specific manually set date
        manual_date = timezone.now() - datetime.timedelta(days=10)
        Product.objects.create(
            stripe_product_id="prod_date_test",
            name="Original",
            stripe_name="Original",
            slug="original",
            price=1000,
            date_added=manual_date,
            public=True,
        )

        # Update product via Stripe (simulated webhook/sync) with a different creation date
        stripe_created_date = 1700000000  # A different timestamp
        product_data = {
            "id": "prod_date_test",
            "name": "Updated Name",
            "images": [],
            "created": stripe_created_date,
        }

        sync_product(product_data)

        product = Product.objects.get(stripe_product_id="prod_date_test")
        self.assertEqual(product.stripe_name, "Updated Name")
        # date_added must remain the manual_date
        self.assertAlmostEqual(
            product.date_added.timestamp(), manual_date.timestamp(), places=0
        )

    def test_sync_product_does_not_overwrite_images(self, mock_requests_get):
        # Create product with existing images (with files)
        product = Product.objects.create(
            stripe_product_id="prod_img_test",
            name="Original",
            stripe_name="Original",
            slug="original",
            price=1000,
            public=True,
        )
        ProductImage.objects.create(
            product=product,
            url="http://test.com/original_main.jpg",
            image_file="product_images/original_main.jpg",
            order=0,
        )
        ProductImage.objects.create(
            product=product,
            url="http://test.com/original_gallery.jpg",
            image_file="product_images/original_gallery.jpg",
            order=1,
        )

        # Update product via Stripe (simulated webhook/sync)
        # Now it SHOULD NOT overwrite images if they already exist in Django
        product_data = {
            "id": "prod_img_test",
            "name": "Updated Name",
            "images": ["http://test.com/stripe_new.jpg"],
            "created": 1700000000,
        }

        sync_product(product_data)

        product.refresh_from_db()
        self.assertEqual(product.stripe_name, "Updated Name")
        # Images SHOULD NOT be updated, keeping Django's local truth
        self.assertEqual(product.images.count(), 2)
        self.assertIn("original_main.jpg", product.main_photo)

    def test_sync_price(self, mock_requests_get):
        Product.objects.create(
            stripe_product_id="prod_test",
            name="Test",
            slug="test",
            price=0,
            stock_quantity=0,
            public=True,
        )

        price_data = {"id": "price_test", "product": "prod_test", "unit_amount": 5000}

        sync_price(price_data)

        product = Product.objects.get(stripe_product_id="prod_test")
        self.assertEqual(product.stripe_price_id, "price_test")
        self.assertEqual(product.price, 5000)

    def test_sync_price_ignores_inactive(self, mock_requests_get):
        product = Product.objects.create(
            stripe_product_id="prod_test",
            name="Test",
            slug="test",
            price=1000,
            stripe_price_id="price_active",
            stock_quantity=0,
            public=True,
        )

        # Inactive price data
        price_data = {
            "id": "price_inactive",
            "product": "prod_test",
            "unit_amount": 5000,
            "active": False,
        }

        sync_price(price_data)

        product.refresh_from_db()
        self.assertEqual(product.stripe_price_id, "price_active")
        self.assertEqual(product.price, 1000)

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_product_updated(self, mock_construct, mock_requests_get):
        mock_construct.return_value = {
            "type": "product.updated",
            "data": {
                "object": {
                    "id": "prod_test",
                    "name": "Updated Name",
                    "images": [],
                    "metadata": {},
                    "created": 1700000000,
                }
            },
        }
        url = reverse("stripe_webhook")
        response = self.client.post(
            url,
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 200)
        product = Product.objects.get(stripe_product_id="prod_test")
        self.assertEqual(product.stripe_name, "Updated Name")

    @patch("stripe.checkout.Session.list_line_items")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_checkout_completed(
        self, mock_construct, mock_list_items, mock_requests_get
    ):
        product = Product.objects.create(
            stripe_product_id="prod_test",
            stripe_price_id="price_test",
            name="Test",
            slug="test",
            price=1000,
            stock_quantity=10,
            public=True,
        )

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test"}},
        }

        mock_item = MagicMock()
        mock_item.price.id = "price_test"
        mock_item.quantity = 2
        mock_list_items.return_value.data = [mock_item]

        url = reverse("stripe_webhook")
        response = self.client.post(
            url,
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 8)

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_invalid_payload(self, mock_construct, mock_requests_get):
        mock_construct.side_effect = ValueError()
        url = reverse("stripe_webhook")
        response = self.client.post(
            url, data=b"invalid", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_invalid_signature(self, mock_construct, mock_requests_get):
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "msg", "sig"
        )
        url = reverse("stripe_webhook")
        response = self.client.post(
            url, data=b"payload", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


class ProductAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.brand = Brand.objects.create(name="Bizen", slug="bizen")
        self.product = Product.objects.create(
            stripe_product_id="prod_admin_test",
            stripe_price_id="price_admin_test",
            name="Admin Product",
            slug="admin-prod",
            price=5000,
            brand=self.brand,
            public=True,
        )

    @patch("stripe.Product.modify")
    def test_save_related_syncs_only_first_image_to_stripe(self, mock_modify):
        # Add gallery images
        ProductImage.objects.create(
            product=self.product, url="http://test.com/main.jpg", order=0
        )
        ProductImage.objects.create(
            product=self.product, url="http://test.com/gallery.jpg", order=1
        )

        # Mock the form and formsets
        mock_form = MagicMock()
        mock_form.instance = self.product
        mock_formsets = []
        mock_request = MagicMock()

        # Call save_related
        self.admin.save_related(mock_request, mock_form, mock_formsets, change=True)

        # Verify stripe.Product.modify was called with ONLY the first image
        expected_images = [
            "http://test.com/main.jpg",
        ]
        mock_modify.assert_called_once_with(
            "prod_admin_test",
            images=expected_images,
        )

    @patch("stripe.Product.modify")
    @patch("stripe.FileLink.create")
    @patch("stripe.File.create")
    @patch("shop.admin.open", create=True)
    def test_save_related_uploads_first_image_to_stripe_and_keeps_local(
        self,
        mock_open,
        mock_file_create,
        mock_file_link_create,
        mock_modify,
    ):
        img = ProductImage.objects.create(
            product=self.product,
            image_file="product_images/test.jpg",
            order=0,
        )

        # Mock the form and formsets
        mock_form = MagicMock()
        mock_form.instance = self.product
        mock_request = MagicMock()

        # Mock Stripe responses
        mock_file_create.return_value = MockObject({"id": "file_123"})
        mock_file_link_create.return_value = MockObject(
            {"url": "https://files.stripe.com/test.jpg"}
        )

        with patch(
            "django.db.models.fields.files.FieldFile.path", new_callable=PropertyMock
        ) as mock_path:
            mock_path.return_value = "/fake/path/test.jpg"

            # Call save_related
            self.admin.save_related(mock_request, mock_form, [], change=True)

            # Verify Stripe File creation
            mock_file_create.assert_called_once()

            # Verify DB was updated
            img.refresh_from_db()
            self.assertEqual(img.url, "https://files.stripe.com/test.jpg")
            # Local file MUST NOT be cleared
            self.assertTrue(img.image_file)

    @patch("stripe.Product.modify")
    def test_save_related_syncs_only_first_image(self, mock_modify):
        # Add 10 gallery images
        for i in range(0, 10):
            ProductImage.objects.create(
                product=self.product, url=f"http://test.com/{i}.jpg", order=i
            )

        mock_form = MagicMock()
        mock_form.instance = self.product
        self.admin.save_related(MagicMock(), mock_form, [], change=True)

        # Verify only 1 image was sent
        args, kwargs = mock_modify.call_args
        self.assertEqual(len(kwargs["images"]), 1)
        self.assertEqual(kwargs["images"][0], "http://test.com/0.jpg")

    def test_stripe_dashboard_url_returns_link(self):
        url = self.admin.stripe_dashboard_url(self.product)
        expected_url = (
            f"https://dashboard.stripe.com/products/{self.product.stripe_product_id}"
        )
        self.assertIn(expected_url, url)
        self.assertIn('target="_blank"', url)
