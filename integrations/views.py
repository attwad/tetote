import stripe
import datetime
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import F
from django.utils.text import slugify
from shop.models import Product, ProductImage
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the event
    if event["type"] in ["product.created", "product.updated"]:
        product_data = event["data"]["object"]
        sync_product(product_data)
    elif event["type"] in ["price.created", "price.updated"]:
        price_data = event["data"]["object"]
        sync_price(price_data)
    elif event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_completed(session)

    return HttpResponse(status=200)


def sync_product(product_data):
    """
    Syncs a single product from Stripe.
    """
    product_id = product_data["id"]
    metadata = product_data.get("metadata", {})

    # Extract images
    images = product_data.get("images", [])
    main_photo = images[0] if images else ""

    # Generate slug from Name if not in metadata
    stripe_name = product_data["name"]
    slug = metadata.get("slug") or slugify(stripe_name)

    with transaction.atomic():
        product, created = Product.objects.update_or_create(
            stripe_product_id=product_id,
            defaults={
                "stripe_name": stripe_name,
                "slug": slug,
                "main_photo": main_photo,
                "price": 0,  # To be updated by price event or sync
            },
        )

        # If it was just created, initialize name and public status
        if created:
            product.name = stripe_name
            # product.public uses the model default (settings.DEBUG)

        # Ingest created timestamp from stripe
        product.date_added = datetime.datetime.fromtimestamp(
            product_data["created"], tz=datetime.timezone.utc
        )
        product.save()

        # Update Gallery
        product.images.all().delete()
        for i, img_url in enumerate(images):
            ProductImage.objects.create(product=product, url=img_url, order=i)


def sync_price(price_data):
    """
    Syncs price info for a product.
    """
    product_id = price_data["product"]
    try:
        product = Product.objects.get(stripe_product_id=product_id)
        product.stripe_price_id = price_data["id"]
        product.price = price_data["unit_amount"]
        product.save()
    except Product.DoesNotExist:
        # If product doesn't exist yet, we can't sync price.
        # Usually product comes first or we sync everything later.
        pass


def handle_checkout_completed(session):
    """
    Decrement stock levels on successful checkout.
    """
    # Fetch line items to identify products
    line_items = stripe.checkout.Session.list_line_items(session["id"])

    with transaction.atomic():
        for item in line_items.data:
            # We need the product ID from the price object
            price_id = item.price.id
            try:
                # Decrement stock locally
                Product.objects.filter(stripe_price_id=price_id).update(
                    stock_quantity=F("stock_quantity") - item.quantity
                )
            except Exception as e:
                logger.error(f"Error updating stock for price_id {price_id}: {e}")
