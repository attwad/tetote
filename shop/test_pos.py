import json
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from integrations.views import (
    complete_pos_sale,
    extract_latest_charge_id,
    handle_payment_intent_succeeded,
    is_card_present_payment_intent,
    send_pos_receipt,
)
from shop.admin import PosSaleAdmin, PosSaleItemInline
from shop.models import Brand, Glaze, PosSale, PosSaleItem, Product, ProductType


class PosTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username="customer", password="password", is_staff=False
        )
        self.brand = Brand.objects.create(name="Bizen Studio", slug="bizen")
        self.glaze = Glaze.objects.create(name="Natural Ash", slug="ash")
        self.product_type = ProductType.objects.create(name="Mug", slug="mug")

        self.product1 = Product.objects.create(
            stripe_product_id="prod_pos_1",
            stripe_price_id="price_pos_1",
            name="Bizen Mug",
            slug="bizen-mug",
            price=4500,
            stock_quantity=5,
            public=True,
            brand=self.brand,
            glaze=self.glaze,
            product_type=self.product_type,
        )
        self.product2 = Product.objects.create(
            stripe_product_id="prod_pos_2",
            stripe_price_id="price_pos_2",
            name="Matcha Bowl",
            slug="matcha-bowl",
            price=8000,
            stock_quantity=2,
            public=True,
        )
        self.hidden_product = Product.objects.create(
            stripe_product_id="prod_pos_hidden",
            stripe_price_id="price_pos_hidden",
            name="Hidden Vase",
            slug="hidden-vase",
            price=12000,
            stock_quantity=3,
            public=False,
        )

    def test_pos_models_and_admin(self):
        sale = PosSale.objects.create(
            status=PosSale.STATUS_PENDING,
            payment_method=PosSale.METHOD_TAP_TO_PAY,
            subtotal_amount=9000,
            discount_amount=1000,
            total_amount=8000,
            customer_email="buyer@example.com",
            stripe_payment_intent_id="pi_test_123",
        )
        item = PosSaleItem.objects.create(
            sale=sale,
            product=self.product1,
            quantity=2,
            unit_price=4500,
        )

        self.assertEqual(sale.subtotal_in_chf, 90.0)
        self.assertEqual(sale.discount_in_chf, 10.0)
        self.assertEqual(sale.total_in_chf, 80.0)
        self.assertIn("POS Sale #", str(sale))
        self.assertIn("2x Bizen Mug", sale.items_summary())
        self.assertIn("Discount: CHF 10.00", sale.items_summary())

        self.assertEqual(str(item), "2x Bizen Mug")
        self.assertEqual(item.unit_price_in_chf, 45.0)
        self.assertEqual(item.line_total_in_chf, 90.0)

        site = AdminSite()
        sale_admin = PosSaleAdmin(PosSale, site)
        self.assertFalse(sale_admin.has_add_permission(None))
        self.assertEqual(sale_admin.subtotal_display(sale), "CHF 90.00")
        self.assertEqual(sale_admin.discount_display(sale), "CHF 10.00")
        self.assertEqual(sale_admin.total_display(sale), "CHF 80.00")
        self.assertIn("pi_test_123", sale_admin.stripe_payment_intent_link(sale))

        sale.stripe_payment_intent_id = None
        self.assertEqual(sale_admin.stripe_payment_intent_link(sale), "-")

        inline = PosSaleItemInline(PosSale, site)
        self.assertEqual(inline.line_total_display(item), "CHF 90.00")
        unsaved_item = PosSaleItem(product=self.product1, quantity=1, unit_price=4500)
        self.assertEqual(inline.line_total_display(unsaved_item), "-")

    def test_pos_view_permissions_and_public_only_products(self):
        url = reverse("shop:pos")
        # Anonymous user redirected to login
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

        # Non-staff user gets 403
        self.client.force_login(self.normal_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

        # Staff user gets 200 and only public products
        self.client.force_login(self.staff_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        products_data = json.loads(resp.context["pos_products_json"])
        product_ids = [p["id"] for p in products_data]
        self.assertIn(self.product1.id, product_ids)
        self.assertIn(self.product2.id, product_ids)
        self.assertNotIn(self.hidden_product.id, product_ids)

    def test_pos_create_sale_validation_errors(self):
        self.client.force_login(self.staff_user)
        url = reverse("shop:pos_create_sale")

        # Invalid JSON
        resp = self.client.post(url, data=b"bad", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

        # Empty items
        resp = self.client.post(
            url, data=json.dumps({"items": []}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

        # Invalid payment method
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "payment_method": "cash",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Invalid discount amount
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "discount_amount": "abc",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Negative discount
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "discount_amount": -100,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Invalid email
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "customer_email": "not-an-email",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Invalid item entries
        resp = self.client.post(
            url,
            data=json.dumps({"items": [{"product_id": "bad", "qty": 0}]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Non-public product rejected
        resp = self.client.post(
            url,
            data=json.dumps(
                {"items": [{"product_id": self.hidden_product.id, "qty": 1}]}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Insufficient stock rejected
        resp = self.client.post(
            url,
            data=json.dumps({"items": [{"product_id": self.product2.id, "qty": 10}]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Discount >= subtotal rejected
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "discount_amount": 4500,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Total < 50 cents rejected
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "discount_amount": 4480,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("stripe.Charge.modify")
    @patch("stripe.PaymentIntent.modify")
    @patch("stripe.Webhook.construct_event")
    def test_pos_tap_to_pay_flow_and_webhook_reconciliation(
        self, mock_construct, mock_pi_modify, mock_charge_modify
    ):
        self.client.force_login(self.staff_user)
        url = reverse("shop:pos_create_sale")

        # Create a first sale that should be auto-canceled when a new one is created
        old_sale = PosSale.objects.create(
            status=PosSale.STATUS_PENDING,
            payment_method=PosSale.METHOD_TAP_TO_PAY,
            subtotal_amount=4500,
            total_amount=4500,
        )

        # Create new Tap to Pay sale with discount and email
        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "items": [
                        {"product_id": self.product1.id, "qty": 2},
                        {"product_id": self.product2.id, "qty": 1},
                    ],
                    "discount_amount": 1000,
                    "payment_method": "tap_to_pay",
                    "customer_email": "receipt@example.com",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["subtotal_cents"], 17000)
        self.assertEqual(data["discount_cents"], 1000)
        self.assertEqual(data["total_cents"], 16000)
        self.assertEqual(data["total_chf"], "160.00")

        old_sale.refresh_from_db()
        self.assertEqual(old_sale.status, PosSale.STATUS_CANCELED)

        sale = PosSale.objects.get(id=data["sale_id"])
        self.assertEqual(sale.status, PosSale.STATUS_PENDING)

        # Simulate Stripe Dashboard App Tap to Pay webhook (card_present, matching amount 16000)
        mock_construct.return_value = {
            "id": "evt_pos_tap_1",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_tap_16000",
                    "amount": 16000,
                    "status": "succeeded",
                    "payment_method_types": ["card_present"],
                    "latest_charge": "ch_tap_16000",
                    "metadata": {},
                }
            },
        }
        webhook_resp = self.client.post(
            reverse("stripe_webhook"),
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(webhook_resp.status_code, 200)

        sale.refresh_from_db()
        self.assertEqual(sale.status, PosSale.STATUS_COMPLETED)
        self.assertEqual(sale.stripe_payment_intent_id, "pi_tap_16000")
        self.assertTrue(sale.receipt_sent)

        # Stock decremented
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 3)
        self.assertEqual(self.product2.stock_quantity, 1)

        # Stripe PaymentIntent metadata updated and Charge receipt_email modified
        mock_pi_modify.assert_called_once()
        mock_charge_modify.assert_called_once_with(
            "ch_tap_16000", receipt_email="receipt@example.com"
        )

        # Idempotency check: duplicate webhook does NOT decrement stock again
        self.client.post(
            reverse("stripe_webhook"),
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 3)

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.PaymentIntent.modify")
    def test_pos_twint_flow_and_status_polling(
        self, mock_pi_modify, mock_pi_retrieve, mock_pi_create
    ):
        self.client.force_login(self.staff_user)
        mock_pi_create.return_value = {
            "id": "pi_twint_4500",
            "status": "requires_action",
            "next_action": {
                "redirect_to_url": {"url": "https://hooks.stripe.com/redirect/twint_1"}
            },
        }

        resp = self.client.post(
            reverse("shop:pos_create_sale"),
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "payment_method": "twint",
                    "customer_email": "twint@example.com",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(
            data["twint_redirect_url"], "https://hooks.stripe.com/redirect/twint_1"
        )
        sale_id = data["sale_id"]

        # Poll status when succeeded on Stripe
        mock_pi_retrieve.return_value = {
            "id": "pi_twint_4500",
            "amount": 4500,
            "status": "succeeded",
            "latest_charge": {"id": "ch_twint_1"},
        }
        with patch("stripe.Charge.modify") as mock_charge_mod:
            status_resp = self.client.get(
                reverse("shop:pos_sale_status", kwargs={"sale_id": sale_id})
            )
            self.assertEqual(status_resp.status_code, 200)
            status_data = status_resp.json()
            self.assertEqual(status_data["status"], "completed")
            self.assertTrue(status_data["receipt_sent"])
            self.assertEqual(status_data["updated_stocks"][str(self.product1.id)], 4)
            mock_charge_mod.assert_called_once_with(
                "ch_twint_1", receipt_email="twint@example.com"
            )

    @patch("stripe.PaymentIntent.create")
    def test_pos_twint_stripe_error_cancels_sale(self, mock_pi_create):
        self.client.force_login(self.staff_user)
        mock_pi_create.side_effect = RuntimeError("Stripe down")

        resp = self.client.post(
            reverse("shop:pos_create_sale"),
            data=json.dumps(
                {
                    "items": [{"product_id": self.product1.id, "qty": 1}],
                    "payment_method": "twint",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 500)
        sale = PosSale.objects.first()
        self.assertEqual(sale.status, PosSale.STATUS_CANCELED)

    @patch("stripe.PaymentIntent.list")
    @patch("stripe.PaymentIntent.modify")
    def test_pos_tap_to_pay_polling_fallback_and_late_receipt(
        self, mock_pi_modify, mock_pi_list
    ):
        self.client.force_login(self.staff_user)
        sale = PosSale.objects.create(
            status=PosSale.STATUS_PENDING,
            payment_method=PosSale.METHOD_TAP_TO_PAY,
            subtotal_amount=4500,
            total_amount=4500,
        )
        PosSaleItem.objects.create(
            sale=sale, product=self.product1, quantity=1, unit_price=4500
        )

        # Save email while still pending
        status_url = reverse("shop:pos_sale_status", kwargs={"sale_id": sale.id})
        resp = self.client.post(
            status_url,
            data=json.dumps(
                {"action": "send_receipt", "customer_email": "early@example.com"}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        sale.refresh_from_db()
        self.assertEqual(sale.customer_email, "early@example.com")

        # Now clear email to test late receipt after completion
        sale.customer_email = ""
        sale.save()

        mock_pi_list.return_value = {
            "data": [
                {
                    "id": "pi_polled_tap",
                    "status": "succeeded",
                    "amount": 4500,
                    "charges": {
                        "data": [
                            {
                                "id": "ch_polled_tap",
                                "payment_method_details": {"type": "card_present"},
                            }
                        ]
                    },
                }
            ]
        }

        poll_resp = self.client.get(status_url)
        self.assertEqual(poll_resp.status_code, 200)
        self.assertEqual(poll_resp.json()["status"], "completed")

        # Now send receipt after completion
        with (
            patch("stripe.PaymentIntent.retrieve") as mock_retrieve,
            patch("stripe.Charge.modify") as mock_charge_mod,
        ):
            mock_retrieve.return_value = {
                "id": "pi_polled_tap",
                "latest_charge": "ch_polled_tap",
            }
            late_resp = self.client.post(
                status_url,
                data=json.dumps(
                    {"action": "send_receipt", "customer_email": "late@example.com"}
                ),
                content_type="application/json",
            )
            self.assertEqual(late_resp.status_code, 200)
            self.assertTrue(late_resp.json()["receipt_sent"])
            mock_charge_mod.assert_called_once_with(
                "ch_polled_tap", receipt_email="late@example.com"
            )

    @patch("stripe.PaymentIntent.cancel")
    def test_pos_sale_status_cancel_and_invalid_actions(self, mock_pi_cancel):
        self.client.force_login(self.staff_user)
        sale = PosSale.objects.create(
            status=PosSale.STATUS_PENDING,
            payment_method=PosSale.METHOD_TWINT,
            subtotal_amount=4500,
            total_amount=4500,
            stripe_payment_intent_id="pi_to_cancel",
        )
        status_url = reverse("shop:pos_sale_status", kwargs={"sale_id": sale.id})

        # Invalid JSON
        resp = self.client.post(
            status_url, data=b"bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

        # Invalid action
        resp = self.client.post(
            status_url,
            data=json.dumps({"action": "unknown"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Invalid email in send_receipt
        resp = self.client.post(
            status_url,
            data=json.dumps({"action": "send_receipt", "customer_email": "bad"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        # Cancel action
        resp = self.client.post(
            status_url,
            data=json.dumps({"action": "cancel"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "canceled")
        mock_pi_cancel.assert_called_once_with("pi_to_cancel")

        # Cannot send receipt for canceled sale
        resp = self.client.post(
            status_url,
            data=json.dumps(
                {"action": "send_receipt", "customer_email": "valid@example.com"}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_helper_edge_cases(self):
        # is_card_present_payment_intent
        self.assertFalse(
            is_card_present_payment_intent({"payment_method_types": ["card"]})
        )
        self.assertTrue(
            is_card_present_payment_intent({"payment_method_types": ["card_present"]})
        )

        # extract_latest_charge_id edge cases
        self.assertIsNone(extract_latest_charge_id(None, pi_id=None))
        with patch(
            "stripe.PaymentIntent.retrieve", side_effect=RuntimeError("API err")
        ):
            self.assertIsNone(extract_latest_charge_id({}, pi_id="pi_err"))

        # complete_pos_sale edge cases
        self.assertFalse(complete_pos_sale(999999))

        sale1 = PosSale.objects.create(
            status=PosSale.STATUS_COMPLETED,
            subtotal_amount=4500,
            total_amount=4500,
            stripe_payment_intent_id="pi_taken",
        )
        sale2 = PosSale.objects.create(
            status=PosSale.STATUS_PENDING,
            subtotal_amount=4500,
            total_amount=4500,
        )
        # Cannot reuse pi_taken on sale2
        self.assertFalse(complete_pos_sale(sale2.id, payment_intent={"id": "pi_taken"}))

        # send_pos_receipt edge cases
        self.assertFalse(send_pos_receipt(sale2, email=""))
        with patch("integrations.views.extract_latest_charge_id", return_value=None):
            self.assertFalse(send_pos_receipt(sale1, email="test@example.com"))
        with (
            patch(
                "integrations.views.extract_latest_charge_id", return_value="ch_fail"
            ),
            patch("stripe.Charge.modify", side_effect=RuntimeError("Charge err")),
        ):
            self.assertFalse(send_pos_receipt(sale1, email="test@example.com"))

        # handle_payment_intent_succeeded unmatched or metadata match
        handle_payment_intent_succeeded(
            {
                "id": "pi_unmatched",
                "amount": 99999,
                "metadata": {"pos_sale_id": "invalid"},
            }
        )
        with patch("stripe.PaymentIntent.modify"):
            handle_payment_intent_succeeded(
                {
                    "id": "pi_meta_match",
                    "amount": 4500,
                    "metadata": {"pos_sale_id": str(sale2.id)},
                }
            )
        sale2.refresh_from_db()
        self.assertEqual(sale2.status, PosSale.STATUS_COMPLETED)
