import stripe
from django.conf import settings
from django.core.management.base import BaseCommand
from integrations.views import sync_product, sync_price


class Command(BaseCommand):
    help = "Deep sync products and prices from Stripe"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        self.stdout.write("Fetching products from Stripe...")
        products = stripe.Product.list(active=True)

        for p in products.data:
            self.stdout.write(f"Syncing product: {p.name}")
            sync_product(p)

            # Fetch prices for this product
            prices = stripe.Price.list(product=p.id, active=True)
            for price in prices.data:
                sync_price(price)

        self.stdout.write(self.style.SUCCESS("Stripe sync completed!"))
