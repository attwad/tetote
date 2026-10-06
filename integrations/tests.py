from io import StringIO
from unittest.mock import MagicMock, patch

import requests
import stripe
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from integrations.views import (
    get_attr_or_key,
    handle_checkout_completed,
    sync_price,
    sync_product,
)
from shop.models import Product, ProductImage


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

    @patch("integrations.views.sync_product")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_server_error(
        self, mock_construct, mock_sync_product, mock_requests_get
    ):
        mock_construct.return_value = {
            "type": "product.created",
            "data": {"object": {"id": "prod_err"}},
        }
        mock_sync_product.side_effect = RuntimeError("Database connection failed")
        url = reverse("stripe_webhook")
        response = self.client.post(
            url,
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 500)

    def test_get_attr_or_key(self, mock_requests_get):
        self.assertEqual(get_attr_or_key(None, "foo", default="default"), "default")
        self.assertEqual(get_attr_or_key({"foo": "bar"}, "foo"), "bar")
        self.assertEqual(get_attr_or_key({"other": "bar"}, "foo", default="def"), "def")
        self.assertEqual(get_attr_or_key(MockObject({"foo": "bar"}), "foo"), "bar")

        class SimpleObj:
            foo = "attr_val"

        self.assertEqual(get_attr_or_key(SimpleObj(), "foo"), "attr_val")
        self.assertEqual(
            get_attr_or_key(SimpleObj(), "missing", default="none"), "none"
        )

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_unconfigured_secret(
        self, mock_construct, mock_requests_get
    ):
        mock_construct.return_value = {
            "type": "unhandled.event",
            "data": {"object": {}},
        }
        with self.settings(STRIPE_WEBHOOK_SECRET=""):
            response = self.client.post(
                reverse("stripe_webhook"),
                data=b"payload",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig",
            )
            self.assertEqual(response.status_code, 200)

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_unexpected_construction_error(
        self, mock_construct, mock_requests_get
    ):
        mock_construct.side_effect = RuntimeError("Crypto failed")
        response = self.client.post(
            reverse("stripe_webhook"),
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 500)

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_price_events(self, mock_construct, mock_requests_get):
        product = Product.objects.create(
            stripe_product_id="prod_webhook_price",
            stripe_price_id="price_old",
            name="Prod Price",
            slug="prod-price",
            price=1000,
            public=True,
        )
        mock_construct.return_value = {
            "type": "price.created",
            "data": {
                "object": {
                    "id": "price_new",
                    "product": "prod_webhook_price",
                    "unit_amount": 4500,
                    "active": True,
                }
            },
        }
        response = self.client.post(
            reverse("stripe_webhook"),
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.price, 4500)
        self.assertEqual(product.stripe_price_id, "price_new")

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_unhandled_event(self, mock_construct, mock_requests_get):
        mock_construct.return_value = {
            "type": "customer.created",
            "data": {"object": {}},
        }
        response = self.client.post(
            reverse("stripe_webhook"),
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, 200)

    def test_sync_product_missing_id(self, mock_requests_get):
        self.assertIsNone(sync_product({}))
        self.assertIsNone(sync_product({"name": "No ID"}))

    def test_sync_product_missing_created_fallback_to_now(self, mock_requests_get):
        product_data = {
            "id": "prod_no_created",
            "name": "No Created",
        }
        sync_product(product_data)
        prod = Product.objects.get(stripe_product_id="prod_no_created")
        self.assertIsNotNone(prod.date_added)

    def test_sync_product_image_name_fallback_without_extension(
        self, mock_requests_get
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"image bytes"
        mock_requests_get.return_value = mock_response

        product_data = {
            "id": "prod_no_ext",
            "name": "No Ext",
            "images": ["http://test.com/no-extension-url"],
        }
        sync_product(product_data)
        prod = Product.objects.get(stripe_product_id="prod_no_ext")
        img = prod.images.first()
        self.assertIsNotNone(img)
        self.assertTrue(img.image_file.name.endswith(".jpg"))

    def test_sync_product_image_download_exception_handled(self, mock_requests_get):
        mock_requests_get.side_effect = requests.RequestException("Network timeout")

        product_data = {
            "id": "prod_img_exc",
            "name": "Img Exc",
            "images": ["http://test.com/fail.jpg"],
        }
        # Should not raise exception
        sync_product(product_data)
        prod = Product.objects.get(stripe_product_id="prod_img_exc")
        self.assertEqual(prod.images.count(), 1)
        self.assertFalse(prod.images.first().image_file)

    def test_sync_price_missing_product_or_price_id(self, mock_requests_get):
        self.assertIsNone(sync_price({}))
        self.assertIsNone(sync_price({"id": "pr_1"}))
        self.assertIsNone(sync_price({"product": "prod_1"}))

    def test_sync_price_unit_amount_is_none(self, mock_requests_get):
        product = Product.objects.create(
            stripe_product_id="prod_none_amt",
            stripe_price_id="pr_old",
            name="None Amt",
            slug="none-amt",
            price=2500,
            public=True,
        )
        sync_price(
            {
                "id": "pr_new_free",
                "product": "prod_none_amt",
                "unit_amount": None,
                "active": True,
            }
        )
        product.refresh_from_db()
        self.assertEqual(product.stripe_price_id, "pr_new_free")
        self.assertEqual(product.price, 2500)

    def test_sync_price_product_does_not_exist(self, mock_requests_get):
        sync_price(
            {
                "id": "pr_orphan",
                "product": "prod_nonexistent",
                "unit_amount": 5000,
                "active": True,
            }
        )
        self.assertFalse(
            Product.objects.filter(stripe_product_id="prod_nonexistent").exists()
        )

    def test_sync_price_unexpected_exception(self, mock_requests_get):
        with patch("shop.models.Product.objects.get") as mock_get:
            mock_get.side_effect = RuntimeError("DB error")
            with self.assertRaises(RuntimeError):
                sync_price(
                    {
                        "id": "pr_err",
                        "product": "prod_err",
                        "unit_amount": 1000,
                        "active": True,
                    }
                )

    @patch("stripe.checkout.Session.list_line_items")
    def test_handle_checkout_completed_list_items_exception(
        self, mock_list_items, mock_requests_get
    ):
        mock_list_items.side_effect = stripe.error.APIError("Stripe unavailable")
        with self.assertRaises(stripe.error.APIError):
            handle_checkout_completed({"id": "cs_err"})

    @patch("stripe.checkout.Session.list_line_items")
    def test_handle_checkout_completed_missing_price_id(
        self, mock_list_items, mock_requests_get
    ):
        mock_item = MagicMock()
        mock_item.price = None
        mock_item.quantity = 1
        mock_list_items.return_value.data = [mock_item]

        handle_checkout_completed({"id": "cs_no_price"})

    @patch("stripe.checkout.Session.list_line_items")
    def test_handle_checkout_completed_product_not_found(
        self, mock_list_items, mock_requests_get
    ):
        mock_item = MagicMock()
        mock_item.price.id = "price_unmatched"
        mock_item.quantity = 2
        mock_list_items.return_value.data = [mock_item]

        handle_checkout_completed({"id": "cs_unmatched"})

    @patch("stripe.checkout.Session.list_line_items")
    def test_handle_checkout_completed_update_exception(
        self, mock_list_items, mock_requests_get
    ):
        mock_item = MagicMock()
        mock_item.price.id = "price_err"
        mock_item.quantity = 1
        mock_list_items.return_value.data = [mock_item]

        with patch("shop.models.Product.objects.filter") as mock_filter:
            mock_filter.side_effect = RuntimeError("Update failure")
            with self.assertRaises(RuntimeError):
                handle_checkout_completed({"id": "cs_fail"})

    @patch("stripe.Price.list")
    @patch("stripe.Product.list")
    def test_sync_stripe_command_retry_and_failure(
        self, mock_product_list, mock_price_list, mock_requests_get
    ):
        mock_product_list.side_effect = stripe.error.APIConnectionError("Conn failed")
        out = StringIO()
        with patch("time.sleep"):
            with self.assertRaises(stripe.error.APIConnectionError):
                call_command("sync_stripe", stdout=out)
        self.assertIn("Stripe API error after 3 attempts", out.getvalue())
