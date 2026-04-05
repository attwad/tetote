import stripe
import os
from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin, TabbedTranslationAdmin
from .models import (
    Brand,
    Product,
    ProductImage,
    Glaze,
    ProductType,
    StoreAnnouncement,
    StoreSettings,
)

stripe.api_key = settings.STRIPE_SECRET_KEY


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    max_num = 8
    fields = ("image_file", "url", "order", "image_preview")
    readonly_fields = ("image_preview", "url")

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.url)
        return "-"

    image_preview.short_description = "Preview"


@admin.register(Brand)
class BrandAdmin(TranslationAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Glaze)
class GlazeAdmin(TranslationAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProductType)
class ProductTypeAdmin(TranslationAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(StoreAnnouncement)
class StoreAnnouncementAdmin(TranslationAdmin):
    list_display = ("text", "is_active", "updated_at")
    list_editable = ("is_active",)


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ("sales_paused",)

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True


@admin.register(Product)
class ProductAdmin(TabbedTranslationAdmin):
    list_display = (
        "name",
        "stripe_name",
        "public",
        "price",
        "stock_quantity",
        "brand",
        "glaze",
        "product_type",
        "is_in_stock",
        "date_added",
    )
    list_editable = ("public",)
    list_filter = ("public", "brand", "glaze", "product_type", "date_added")
    search_fields = ("name", "stripe_name", "description", "stripe_product_id")
    readonly_fields = (
        "stripe_product_id",
        "stripe_dashboard_url",
        "stripe_price_id",
        "stripe_name",
        "main_photo",
        "price",
        "date_added",
    )
    inlines = [ProductImageInline]

    def has_add_permission(self, request):
        return True

    @admin.display(description=_("Stripe Dashboard URL"))
    def stripe_dashboard_url(self, obj):
        if obj.stripe_product_id:
            url = f"https://dashboard.stripe.com/products/{obj.stripe_product_id}"
            return format_html(
                '<a href="{url}" target="_blank">{url}</a>',
                url=url,
            )
        return "-"

    def save_related(self, request, form, formsets, change):
        """
        After saving the product and its images, sync the images to Stripe.
        """
        super().save_related(request, form, formsets, change)

        product = form.instance

        # Handle file uploads to Stripe for each ProductImage
        for img in product.images.all():
            if img.image_file:
                try:
                    # 1. Upload file to Stripe
                    with open(img.image_file.path, "rb") as f:
                        stripe_file = stripe.File.create(
                            file=f, purpose="product_image"
                        )

                    # 2. Create a public FileLink to get a public URL
                    stripe_link = stripe.FileLink.create(file=stripe_file.id)

                    # 3. Store the public URL in the database
                    img.url = stripe_link.url
                    img.save()

                    # 4. Delete the local temporary file
                    if os.path.exists(img.image_file.path):
                        os.remove(img.image_file.path)
                        img.image_file = None
                        img.save()

                except Exception as e:
                    self.message_user(
                        request,
                        f"Warning: Failed to upload image for {product.name} to Stripe: {e}",
                        level="warning",
                    )

        if product.stripe_product_id:
            # Collect all image URLs: main_photo first, then gallery images in order
            images = []
            if product.main_photo:
                images.append(product.main_photo)

            # Add gallery images, excluding duplicates and limiting to 8 total
            for img in product.images.all().order_by("order"):
                if img.url and img.url not in images:
                    images.append(img.url)

            # Stripe allows up to 8 images
            final_images = images[:8]

            try:
                stripe.Product.modify(
                    product.stripe_product_id,
                    images=final_images,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Warning: Failed to sync images to Stripe: {e}",
                    level="warning",
                )

    # Note: price and main_photo are read-only as well but since they are common
    # we don't translate them. They are in fieldsets below.
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "stripe_product_id",
                    "stripe_dashboard_url",
                    "stripe_price_id",
                    "stripe_name",
                    "name",
                    "price",
                    "description",
                    "main_photo",
                    "date_added",
                )
            },
        ),
        (
            "Local Settings",
            {
                "fields": (
                    "public",
                    "brand",
                    "glaze",
                    "product_type",
                    "stock_quantity",
                )
            },
        ),
    )
