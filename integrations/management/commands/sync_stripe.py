import stripe
import time
from django.conf import settings
from django.core.management.base import BaseCommand
from integrations.views import sync_product, sync_price


class Command(BaseCommand):
    help = "Surgically sync products and prices from Stripe"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                self.stdout.write("Fetching products from Stripe...")
                # Use auto_paging_iter to handle all products efficiently
                products = stripe.Product.list(active=True).auto_paging_iter()

                count = 0
                for p in products:
                    self.stdout.write(f"Syncing product: {p.name} ({p.id})")
                    sync_product(p.to_dict())
                    count += 1

                    # Fetch all active prices for this product
                    prices = stripe.Price.list(
                        product=p.id, active=True
                    ).auto_paging_iter()
                    for price in prices:
                        sync_price(price.to_dict())

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Stripe sync completed! {count} products processed."
                    )
                )
                return  # Success
            except (stripe.error.APIError, stripe.error.APIConnectionError) as e:
                if attempt < max_retries - 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Stripe API error: {e}. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})"
                        )
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Stripe API error after {max_retries} attempts: {e}"
                        )
                    )
                    raise e
