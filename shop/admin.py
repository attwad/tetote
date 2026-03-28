from django.contrib import admin
from django.utils.html import format_html
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


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ("image_preview",)

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
        "stripe_price_id",
        "stripe_name",
        "date_added",
    )
    inlines = [ProductImageInline]

    def has_add_permission(self, request):
        return False

    # Note: price and main_photo are read-only as well but since they are common
    # we don't translate them. They are in fieldsets below.
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "stripe_product_id",
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
