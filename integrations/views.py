import datetime
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
import stripe
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from shop.models import PosSale, Product, ProductImage

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

# Type alias for Stripe webhook payloads (SDK StripeObjects, dicts, or test Mocks)
StripePayload = Union[stripe.StripeObject, Dict[str, Any], Any]


def get_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    """
    Safely retrieves a property from a Stripe SDK object (e.g. stripe.Event,
    stripe.Product), a dictionary, or a mock object.

    Stripe Python SDK objects expose properties via attribute access (obj.key)
    and dictionary key subscription (obj["key"]), but do not implement dict.get().
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        if key in obj:
            return obj[key]
    except (TypeError, KeyError, AttributeError):
        pass
    return getattr(obj, key, default)


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    if not endpoint_secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured in settings")

    try:
        event: stripe.Event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.warning(f"Invalid payload received in Stripe webhook: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Signature verification failed for Stripe webhook: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception(f"Unexpected error constructing Stripe webhook event: {e}")
        return HttpResponse(status=500)

    event_type: str = get_attr_or_key(event, "type", "unknown")
    event_id: str = get_attr_or_key(event, "id", "unknown")
    logger.info(f"Received Stripe webhook event: {event_type} (ID: {event_id})")

    try:
        data: StripePayload = get_attr_or_key(event, "data", {})
        data_object: StripePayload = get_attr_or_key(data, "object", {})

        if event_type in ["product.created", "product.updated"]:
            sync_product(data_object)
        elif event_type in ["price.created", "price.updated"]:
            sync_price(data_object)
        elif event_type == "checkout.session.completed":
            handle_checkout_completed(data_object)
        elif event_type == "payment_intent.succeeded":
            handle_payment_intent_succeeded(data_object)
        else:
            logger.info(f"Unhandled Stripe webhook event type: {event_type}")
    except Exception as e:
        logger.exception(
            f"Error processing Stripe webhook event '{event_type}' (ID: {event_id}): {e}"
        )
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def sync_product(product_data: StripePayload) -> None:
    """
    Syncs a single product from Stripe.
    Only updates fields present in the Stripe Product object.
    """
    product_id: Optional[str] = get_attr_or_key(product_data, "id")
    if not product_id:
        logger.error(f"Stripe product payload missing 'id': {product_data}")
        return

    images: List[str] = get_attr_or_key(product_data, "images", [])
    stripe_name: str = get_attr_or_key(product_data, "name", "")
    metadata: StripePayload = get_attr_or_key(product_data, "metadata", {})
    slug: str = get_attr_or_key(metadata, "slug") or slugify(stripe_name)

    created_timestamp: Optional[int] = get_attr_or_key(product_data, "created")
    if created_timestamp:
        date_added = datetime.datetime.fromtimestamp(
            created_timestamp, tz=datetime.timezone.utc
        )
    else:
        date_added = datetime.datetime.now(tz=datetime.timezone.utc)

    logger.info(f"Syncing product '{product_id}' (name: '{stripe_name}')")

    images_to_download: List[Tuple[ProductImage, str, int]] = []
    try:
        with transaction.atomic():
            product, created = Product.objects.get_or_create(
                stripe_product_id=product_id,
                defaults={
                    "name": stripe_name,  # Initial name
                    "stripe_name": stripe_name,
                    "slug": slug,
                    "price": 0,  # Placeholder until price event arrives
                    "date_added": date_added,
                },
            )

            # Surgical update: only touch fields that belong to the Stripe Product object
            # and that we WANT to keep in sync even after creation.
            product.stripe_name = stripe_name

            # Django is the source of truth for images.
            # We only pull images from Stripe if the product has NO images in Django yet
            # (e.g., during the initial sync of a new product).
            if not product.images.exists() and images:
                for i, img_url in enumerate(images):
                    new_img = ProductImage.objects.create(
                        product=product, url=img_url, order=i
                    )
                    images_to_download.append((new_img, img_url, i))

            product.save()
            logger.info(
                f"Successfully synced product '{product_id}' (created={created})"
            )
    except Exception as e:
        logger.exception(f"Error in sync_product for product '{product_id}': {e}")
        raise

    for new_img, img_url, i in images_to_download:
        # Immediately download and save locally outside of the transaction
        try:
            response = requests.get(img_url, timeout=10)
            if response.status_code == 200:
                filename = os.path.basename(img_url.split("?")[0])
                if not filename or "." not in filename:
                    filename = f"product_{new_img.product_id}_{i}.jpg"
                new_img.image_file.save(
                    filename, ContentFile(response.content), save=True
                )
            else:
                logger.warning(
                    f"Failed to download image from Stripe, status code {response.status_code}: {img_url}"
                )
        except Exception as e:
            logger.exception(f"Failed to download image from Stripe ({img_url}): {e}")


def sync_price(price_data: StripePayload) -> None:
    """
    Syncs price info for a product.
    Only updates if the price is active.
    """
    price_id: Optional[str] = get_attr_or_key(price_data, "id")
    product_id: Optional[str] = get_attr_or_key(price_data, "product")

    if not get_attr_or_key(price_data, "active", True):
        logger.info(f"Ignoring inactive price {price_id} for product {product_id}")
        return

    if not product_id or not price_id:
        logger.error(
            f"Invalid price_data payload missing product or price ID: {price_data}"
        )
        return

    logger.info(f"Syncing price '{price_id}' for product '{product_id}'")

    try:
        product = Product.objects.get(stripe_product_id=product_id)
        unit_amount: Optional[int] = get_attr_or_key(price_data, "unit_amount")
        if unit_amount is None:
            logger.warning(
                f"Price '{price_id}' unit_amount is None, updating stripe_price_id only"
            )
        else:
            product.price = unit_amount
        product.stripe_price_id = price_id
        product.save()
        logger.info(
            f"Successfully updated price for product '{product_id}' to {unit_amount} (price_id: {price_id})"
        )
    except Product.DoesNotExist:
        # Product will be created by product.created event
        logger.info(
            f"Product '{product_id}' does not exist in DB yet for price '{price_id}' sync; skipping until product event arrives"
        )
    except Exception as e:
        logger.exception(
            f"Error in sync_price for price '{price_id}', product '{product_id}': {e}"
        )
        raise


def handle_checkout_completed(session: StripePayload) -> None:
    """
    Decrement stock levels on successful checkout.
    """
    session_id: Optional[str] = get_attr_or_key(session, "id")
    logger.info(f"Handling checkout.session.completed for session: {session_id}")

    try:
        line_items = stripe.checkout.Session.list_line_items(session_id)
    except Exception as e:
        logger.exception(
            f"Failed to retrieve line items from Stripe for session '{session_id}': {e}"
        )
        raise

    with transaction.atomic():
        for item in line_items.data:
            price_obj: StripePayload = get_attr_or_key(item, "price")
            price_id: Optional[str] = get_attr_or_key(price_obj, "id")
            quantity: int = get_attr_or_key(item, "quantity", 0)

            if not price_id:
                logger.warning(
                    f"Line item missing price ID in session '{session_id}': {item}"
                )
                continue

            try:
                updated_count = Product.objects.filter(stripe_price_id=price_id).update(
                    stock_quantity=F("stock_quantity") - quantity
                )
                if updated_count == 0:
                    logger.warning(
                        f"No product found with stripe_price_id '{price_id}' when decrementing stock by {quantity} for session '{session_id}'"
                    )
                else:
                    logger.info(
                        f"Successfully decremented stock by {quantity} for stripe_price_id '{price_id}' (session: {session_id})"
                    )
            except Exception as e:
                logger.exception(
                    f"Error updating stock for price_id '{price_id}' in session '{session_id}': {e}"
                )
                raise


def is_card_present_payment_intent(payment_intent: StripePayload) -> bool:
    """
    Returns True if the PaymentIntent was processed via Tap to Pay / Terminal (card_present).
    """
    pm_types = get_attr_or_key(payment_intent, "payment_method_types", []) or []
    if "card_present" in pm_types:
        return True

    charges = get_attr_or_key(payment_intent, "charges")
    charges_data = get_attr_or_key(charges, "data", []) if charges else []
    for charge in charges_data:
        pm_details = get_attr_or_key(charge, "payment_method_details", {})
        if get_attr_or_key(pm_details, "type") == "card_present":
            return True
    return False


def extract_latest_charge_id(
    payment_intent: Optional[StripePayload], pi_id: Optional[str] = None
) -> Optional[str]:
    """
    Extracts the Charge ID from a PaymentIntent object/dict, or retrieves the PaymentIntent from Stripe.
    """
    if payment_intent is not None:
        latest_charge = get_attr_or_key(payment_intent, "latest_charge")
        if isinstance(latest_charge, str) and latest_charge:
            return latest_charge
        if latest_charge is not None:
            charge_id = get_attr_or_key(latest_charge, "id")
            if charge_id:
                return charge_id

        charges = get_attr_or_key(payment_intent, "charges")
        charges_data = get_attr_or_key(charges, "data", []) if charges else []
        if charges_data:
            first_charge_id = get_attr_or_key(charges_data[0], "id")
            if first_charge_id:
                return first_charge_id

    target_pi_id = pi_id or get_attr_or_key(payment_intent, "id")
    if target_pi_id:
        try:
            retrieved_pi = stripe.PaymentIntent.retrieve(target_pi_id)
            latest_charge = get_attr_or_key(retrieved_pi, "latest_charge")
            if isinstance(latest_charge, str) and latest_charge:
                return latest_charge
            if latest_charge is not None:
                return get_attr_or_key(latest_charge, "id")
        except Exception as e:
            logger.warning(
                f"Failed to retrieve PaymentIntent '{target_pi_id}' for charge lookup: {e}"
            )
    return None


def send_pos_receipt(
    sale: PosSale,
    email: Optional[str] = None,
    payment_intent: Optional[StripePayload] = None,
) -> bool:
    """
    Updates the underlying Stripe Charge's receipt_email to trigger an automatic Stripe email receipt.
    """
    target_email = (email or sale.customer_email or "").strip()
    if not target_email or not sale.stripe_payment_intent_id:
        return False

    charge_id = extract_latest_charge_id(
        payment_intent, pi_id=sale.stripe_payment_intent_id
    )
    if not charge_id:
        logger.warning(
            f"Could not find latest_charge for POS Sale #{sale.id} (PI: {sale.stripe_payment_intent_id})"
        )
        return False

    try:
        stripe.Charge.modify(charge_id, receipt_email=target_email)
        sale.customer_email = target_email
        sale.receipt_sent = True
        sale.save(update_fields=["customer_email", "receipt_sent"])
        logger.info(
            f"Sent Stripe receipt for POS Sale #{sale.id} (charge: {charge_id}) to {target_email}"
        )
        return True
    except Exception as e:
        logger.warning(
            f"Failed to send Stripe receipt for POS Sale #{sale.id} (charge: {charge_id}): {e}"
        )
        return False


def complete_pos_sale(
    sale_id: int, payment_intent: Optional[StripePayload] = None
) -> bool:
    """
    Atomically marks a PENDING PosSale as COMPLETED, decrements item stock levels,
    enriches the Stripe PaymentIntent metadata/description, and triggers the customer receipt email.
    Returns True if the sale transitioned from PENDING to COMPLETED, False otherwise.
    """
    pi_id: Optional[str] = (
        get_attr_or_key(payment_intent, "id") if payment_intent else None
    )

    with transaction.atomic():
        try:
            sale = PosSale.objects.select_for_update().get(id=sale_id)
        except PosSale.DoesNotExist:
            logger.warning(f"PosSale #{sale_id} not found during completion")
            return False

        if sale.status != PosSale.STATUS_PENDING:
            logger.info(
                f"PosSale #{sale_id} already has status '{sale.status}'; skipping completion"
            )
            return False

        if (
            pi_id
            and PosSale.objects.filter(stripe_payment_intent_id=pi_id)
            .exclude(id=sale.id)
            .exists()
        ):
            logger.warning(
                f"PaymentIntent '{pi_id}' is already linked to another PosSale; skipping PosSale #{sale_id}"
            )
            return False

        for item in sale.items.all():
            Product.objects.filter(id=item.product_id).update(
                stock_quantity=F("stock_quantity") - item.quantity
            )

        sale.status = PosSale.STATUS_COMPLETED
        sale.completed_at = timezone.now()
        if pi_id:
            sale.stripe_payment_intent_id = pi_id
        sale.save()

    logger.info(f"Completed POS Sale #{sale.id} (PI: {sale.stripe_payment_intent_id})")

    summary = sale.items_summary()
    if sale.stripe_payment_intent_id:
        try:
            stripe.PaymentIntent.modify(
                sale.stripe_payment_intent_id,
                description=summary,
                metadata={
                    "pos_sale_id": str(sale.id),
                    "items": summary[:500],
                    "subtotal_chf": f"{sale.subtotal_in_chf:.2f}",
                    "discount_chf": f"{sale.discount_in_chf:.2f}",
                    "total_chf": f"{sale.total_in_chf:.2f}",
                },
            )
        except Exception as e:
            logger.warning(
                f"Failed to update metadata on PaymentIntent '{sale.stripe_payment_intent_id}' for POS Sale #{sale.id}: {e}"
            )

        if sale.customer_email and not sale.receipt_sent:
            send_pos_receipt(sale, payment_intent=payment_intent)

    return True


def handle_payment_intent_succeeded(payment_intent: StripePayload) -> None:
    """
    Reconciles a succeeded PaymentIntent with an active PosSale (from TWINT or Stripe Dashboard Tap to Pay).
    """
    pi_id: Optional[str] = get_attr_or_key(payment_intent, "id")
    amount: Optional[int] = get_attr_or_key(payment_intent, "amount")
    metadata: StripePayload = get_attr_or_key(payment_intent, "metadata", {}) or {}
    pos_sale_id_raw = get_attr_or_key(metadata, "pos_sale_id")

    logger.info(
        f"Handling payment_intent.succeeded for PI: {pi_id} (amount: {amount}, pos_sale_id: {pos_sale_id_raw})"
    )

    sale: Optional[PosSale] = None

    if pi_id:
        sale = PosSale.objects.filter(stripe_payment_intent_id=pi_id).first()

    if not sale and pos_sale_id_raw:
        try:
            sale = PosSale.objects.filter(id=int(pos_sale_id_raw)).first()
        except (ValueError, TypeError):
            pass

    if (
        not sale
        and amount is not None
        and is_card_present_payment_intent(payment_intent)
    ):
        cutoff = timezone.now() - datetime.timedelta(minutes=30)
        sale = (
            PosSale.objects.filter(
                status=PosSale.STATUS_PENDING,
                payment_method=PosSale.METHOD_TAP_TO_PAY,
                total_amount=amount,
                created_at__gte=cutoff,
            )
            .order_by("-created_at")
            .first()
        )

    if sale:
        complete_pos_sale(sale.id, payment_intent=payment_intent)
    else:
        logger.info(
            f"No matching pending PosSale found for PaymentIntent '{pi_id}' (ignoring)"
        )
