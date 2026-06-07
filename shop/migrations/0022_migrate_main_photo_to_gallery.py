from django.db import migrations


def migrate_main_photo(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    ProductImage = apps.get_model("shop", "ProductImage")

    for product in Product.objects.all():
        main_url = product._main_photo_temp
        if main_url:
            # Check if an image with this URL already exists in gallery
            # We use filter on ProductImage directly since reverse relation might be tricky in migrations
            existing = ProductImage.objects.filter(
                product=product, url=main_url
            ).first()
            if existing:
                # Move to 0 and shift others
                other_images = (
                    ProductImage.objects.filter(product=product)
                    .exclude(id=existing.id)
                    .order_by("order")
                )
                existing.order = 0
                existing.save()
                for i, img in enumerate(other_images, 1):
                    img.order = i
                    img.save()
            else:
                # Shift all existing images and create new at 0
                all_images = ProductImage.objects.filter(product=product).order_by(
                    "order"
                )
                for i, img in enumerate(all_images, 1):
                    img.order = i
                    img.save()
                ProductImage.objects.create(product=product, url=main_url, order=0)


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0021_rename_main_photo_temp"),
    ]

    operations = [
        migrations.RunPython(
            migrate_main_photo, reverse_code=migrations.RunPython.noop
        ),
    ]
