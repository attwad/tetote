import stripe
from django.conf import settings
from django.core.management.base import BaseCommand
from integrations.views import sync_product, sync_price


class Command(BaseCommand):
    help = "Surgically sync products and prices from Stripe"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        self.stdout.write("Fetching products from Stripe...")

        # Use auto_paging_iter to handle all products efficiently
        products = stripe.Product.list(active=True).auto_paging_iter()

        count = 0
        for p in products:
            self.stdout.write(f"Syncing product: {p.name} ({p.id})")
            sync_product(p)
            count += 1

            # Fetch all active prices for this product
            prices = stripe.Price.list(product=p.id, active=True).auto_paging_iter()
            for price in prices:
                sync_price(price)

        self.stdout.write(
            self.style.SUCCESS(f"Stripe sync completed! {count} products processed.")
        )
