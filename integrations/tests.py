import stripe
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from shop.models import Product
from integrations.views import sync_product, sync_price


class StripeIntegrationTest(TestCase):
    def test_sync_product(self):
        product_data = {
            "id": "prod_test",
            "name": "Test Product",
            "description": "Test Desc",
            "images": ["http://test.com/img1.jpg"],
            "metadata": {"yakikata": "bizen", "product_type": "vase"},
            "created": 1700000000,
        }

        sync_product(product_data)

        product = Product.objects.get(stripe_product_id="prod_test")
        self.assertEqual(product.stripe_name, "Test Product")
        self.assertEqual(product.images.count(), 1)
        self.assertEqual(product.images.first().url, "http://test.com/img1.jpg")

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
