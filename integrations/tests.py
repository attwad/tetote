import stripe
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from shop.models import Product
from integrations.views import sync_product, sync_price


from django.core.management import call_command
from io import StringIO


# ...
class MockObject(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class StripeIntegrationTest(TestCase):
    # ...
    @patch("stripe.Price.list")
    @patch("stripe.Product.list")
    def test_sync_stripe_command(self, mock_product_list, mock_price_list):
        # Mock product list
        mock_p1 = MockObject(
            {
                "id": "prod_1",
                "name": "Stripe Product 1",
                "images": [],
                "metadata": {},
                "created": 1700000000,
            }
        )

        mock_product_list.return_value.auto_paging_iter.return_value = [mock_p1]

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
        product_data = {
            "id": "prod_test",
            "name": "Test Product",
            "description": "Test Desc",
            "images": ["http://test.com/img1.jpg"],
            "metadata": {"glaze": "bizen", "product_type": "vase"},
            "created": 1700000000,
        }

        sync_product(product_data)

        product = Product.objects.get(stripe_product_id="prod_test")
        self.assertEqual(product.stripe_name, "Test Product")
        self.assertEqual(product.images.count(), 1)
        self.assertEqual(product.images.first().url, "http://test.com/img1.jpg")

    def test_sync_product_does_not_overwrite_price(self):
        # Create product with existing price
        Product.objects.create(
            stripe_product_id="prod_overwrite_test",
            stripe_price_id="price_fixed",
            name="Original",
            stripe_name="Original",
            slug="original",
            price=9900,
            stock_quantity=5,
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

    def test_sync_price(self):
        Product.objects.create(
            stripe_product_id="prod_test",
            name="Test",
            slug="test",
            price=0,
            stock_quantity=0,
        )

        price_data = {"id": "price_test", "product": "prod_test", "unit_amount": 5000}

        sync_price(price_data)

        product = Product.objects.get(stripe_product_id="prod_test")
        self.assertEqual(product.price, 5000)
        self.assertEqual(product.stripe_price_id, "price_test")

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_product_updated(self, mock_construct):
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
    def test_stripe_webhook_checkout_completed(self, mock_construct, mock_list_items):
        product = Product.objects.create(
            stripe_product_id="prod_test",
            stripe_price_id="price_test",
            name="Test",
            slug="test",
            price=1000,
            stock_quantity=10,
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
    def test_stripe_webhook_invalid_payload(self, mock_construct):
        mock_construct.side_effect = ValueError()
        url = reverse("stripe_webhook")
        response = self.client.post(
            url, data=b"invalid", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_invalid_signature(self, mock_construct):
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "msg", "sig"
        )
        url = reverse("stripe_webhook")
        response = self.client.post(
            url, data=b"payload", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
