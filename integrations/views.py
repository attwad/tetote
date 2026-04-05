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
    Only updates fields present in the Stripe Product object.
    """
    product_id = product_data["id"]

    # Extract images
    images = product_data.get("images", [])
    main_photo = images[0] if images else ""

    # Generate slug from Name
    stripe_name = product_data["name"]
    slug = product_data.get("metadata", {}).get("slug") or slugify(stripe_name)

    with transaction.atomic():
        product, created = Product.objects.get_or_create(
            stripe_product_id=product_id,
            defaults={
                "name": stripe_name,  # Initial name
                "stripe_name": stripe_name,
                "slug": slug,
                "main_photo": main_photo,
                "price": 0,  # Placeholder until price event arrives
            },
        )

        # Surgical update: only touch fields that belong to the Stripe Product object
        product.stripe_name = stripe_name
        product.slug = slug

        # Ingest created timestamp
        product.date_added = datetime.datetime.fromtimestamp(
            product_data["created"], tz=datetime.timezone.utc
        )

        # Only update images from Stripe if the product is being created for the first time
        if created:
            product.main_photo = main_photo
            product.save()

            # Update Gallery
            product.images.all().delete()
            for i, img_url in enumerate(images):
                ProductImage.objects.create(product=product, url=img_url, order=i)
        else:
            product.save()


def sync_price(price_data):
    """
    Syncs price info for a product.
    Only updates if the price is active.
    """
    if not price_data.get("active", True):
        logger.info(
            f"Ignoring inactive price {price_data['id']} for product {price_data['product']}"
        )
        return

    product_id = price_data["product"]
    try:
        product = Product.objects.get(stripe_product_id=product_id)
        product.stripe_price_id = price_data["id"]
        product.price = price_data["unit_amount"]
        product.save()
    except Product.DoesNotExist:
        # Product will be created by product.created event
        pass


def handle_checkout_completed(session):
    """
    Decrement stock levels on successful checkout.
    """
    line_items = stripe.checkout.Session.list_line_items(session["id"])

    with transaction.atomic():
        for item in line_items.data:
            price_id = item.price.id
            try:
                Product.objects.filter(stripe_price_id=price_id).update(
                    stock_quantity=F("stock_quantity") - item.quantity
                )
            except Exception as e:
                logger.error(f"Error updating stock for price_id {price_id}: {e}")
