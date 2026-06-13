import stripe
from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin, TabbedTranslationAdmin
from markdownx.admin import MarkdownxModelAdmin
from adminsortable2.admin import (
    SortableAdminBase,
    SortableInlineAdminMixin,
    SortableAdminMixin,
)
from .models import (
    Brand,
    Product,
    ProductImage,
    Glaze,
    ProductType,
    StoreAnnouncement,
    StoreSettings,
    CarouselImage,
)

stripe.api_key = settings.STRIPE_SECRET_KEY

# tetote Admin Branding
admin.site.site_header = _("tetote admin room")
admin.site.site_title = _("tetote Admin")
admin.site.index_title = _("tetote admin room")


class ProductImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image_file", "url", "image_preview")
    readonly_fields = ("image_preview", "url")

    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height: 100px;"/>', obj.image_url
            )
        return "-"

    image_preview.short_description = "Preview"


@admin.register(Brand)
class BrandAdmin(TranslationAdmin):
    list_display = ("name", "slug", "content_slug")
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


@admin.register(CarouselImage)
class CarouselImageAdmin(SortableAdminMixin, TabbedTranslationAdmin):
    list_display = ("image_preview", "alt_text", "created_at")
    list_filter = ()

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px;"/>', obj.image.url
            )
        return "-"

    image_preview.short_description = _("Preview")


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ("sales_paused",)

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True


@admin.register(Product)
class ProductAdmin(SortableAdminBase, TabbedTranslationAdmin, MarkdownxModelAdmin):
    list_display = (
        "name",
        "stripe_name",
        "public",
        "price",
        "stock_quantity",
        "soon_in_stock",
        "brand",
        "glaze",
        "product_type",
        "is_in_stock",
        "date_added",
    )
    list_editable = ("public", "soon_in_stock")
    list_filter = (
        "public",
        "soon_in_stock",
        "brand",
        "glaze",
        "product_type",
        "date_added",
    )
    search_fields = (
        "name",
        "stripe_name",
        "description",
        "details",
        "stripe_product_id",
    )
    readonly_fields = (
        "stripe_product_id",
        "stripe_dashboard_url",
        "stripe_price_id",
        "stripe_name",
        "price",
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
        After saving the product and its images, sync the first image to Stripe.
        Django is the source of truth for images and hosts them locally.
        """
        super().save_related(request, form, formsets, change)

        product = form.instance

        # 1. Detect if any image_file has changed in the formset
        # and clear its 'url' so it gets re-uploaded if it's the first one.
        for formset in formsets:
            if formset.model == ProductImage:
                for f in formset.forms:
                    if f.instance.pk and "image_file" in f.changed_data:
                        f.instance.url = ""
                        f.instance.save()

        # 2. Sync images with Stripe
        # Only the first image is sent to Stripe (required for Checkout)
        images = product.images.all().order_by("order")
        if images.exists():
            first_img = images[0]

            # Ensure the first image has a Stripe URL if it has a local file
            if first_img.image_file and not first_img.url:
                try:
                    with open(first_img.image_file.path, "rb") as f:
                        stripe_file = stripe.File.create(
                            file=f, purpose="product_image"
                        )

                    stripe_link = stripe.FileLink.create(file=stripe_file.id)
                    first_img.url = stripe_link.url
                    first_img.save()
                except Exception as e:
                    self.message_user(
                        request,
                        f"Warning: Failed to upload first image to Stripe: {e}",
                        level="warning",
                    )

            # Sync only the first image's URL to Stripe Product
            if product.stripe_product_id:
                try:
                    stripe_images = [first_img.url] if first_img.url else []
                    stripe.Product.modify(
                        product.stripe_product_id,
                        images=stripe_images,
                    )
                except Exception as e:
                    self.message_user(
                        request,
                        f"Warning: Failed to sync first image to Stripe: {e}",
                        level="warning",
                    )
        elif product.stripe_product_id:
            # No images left, clear Stripe images
            try:
                stripe.Product.modify(product.stripe_product_id, images=[])
            except Exception:
                pass

    # Note: price is read-only as well but since it is common
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
                    "details",
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
                    "soon_in_stock",
                )
            },
        ),
    )
