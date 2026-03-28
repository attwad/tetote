from django.db import migrations
import random


def populate_glazes(apps, schema_editor):
    Glaze = apps.get_model("shop", "Glaze")
    Product = apps.get_model("shop", "Product")

    # Clear old Glaze data that came from Yakikata rename
    Glaze.objects.all().delete()

    glaze_types = [
        ("Haiyu", "haiyu"),
        ("Kiseto", "kiseto"),
        ("Kohiki", "kohiki"),
        ("Oribe", "oribe"),
        ("Shino", "shino"),
        ("Nezumi-shino", "nezumi-shino"),
        ("Other", "other"),
    ]

    glaze_objs = []
    for name, slug in glaze_types:
        # We manually set all translation fields because apps.get_model
        # doesn't handle modeltranslation's name descriptor.
        glaze = Glaze.objects.create(
            name=name,
            name_en=name,
            name_de=name,
            name_fr=name,
            name_ja=name,
            slug=slug,
        )
        glaze_objs.append(glaze)

    # Randomly assign glazes to existing products
    products = Product.objects.all()
    for product in products:
        product.glaze = random.choice(glaze_objs)
        product.save()


def reverse_populate_glazes(apps, schema_editor):
    Glaze = apps.get_model("shop", "Glaze")
    Glaze.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0012_rename_yakikata_glaze_alter_glaze_options_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_glazes, reverse_populate_glazes),
    ]
