import requests
import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from shop.models import ProductImage


class Command(BaseCommand):
    help = "Download all images from Stripe URLs and save them to local storage"

    def handle(self, *args, **options):
        images_to_migrate = ProductImage.objects.filter(image_file="").exclude(url="")
        total = images_to_migrate.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No images to migrate."))
            return

        self.stdout.write(f"Migrating {total} images from Stripe to local storage...")

        success_count = 0
        error_count = 0

        for img in images_to_migrate:
            try:
                self.stdout.write(
                    f"Downloading image for {img.product.name} (order {img.order})..."
                )
                response = requests.get(img.url, timeout=10)
                response.raise_for_status()

                # Get filename from URL or use a default
                filename = os.path.basename(img.url.split("?")[0])
                if not filename or "." not in filename:
                    filename = f"product_{img.product.id}_{img.order}.jpg"

                img.image_file.save(filename, ContentFile(response.content), save=True)
                success_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to migrate image {img.id}: {e}")
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Migration completed! Success: {success_count}, Errors: {error_count}"
            )
        )
