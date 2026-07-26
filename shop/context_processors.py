from typing import Any, Dict

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpRequest
from .models import Brand, StoreAnnouncement, StoreSettings


def announcement(request: HttpRequest) -> Dict[str, Any]:
    """
    Returns the latest active announcement.
    """
    active_announcement = (
        StoreAnnouncement.objects.filter(is_active=True).order_by("-updated_at").first()
    )
    return {"active_announcement": active_announcement}


def store_settings(request: HttpRequest) -> Dict[str, Any]:
    """
    Returns the store settings.
    """
    settings = StoreSettings.objects.first()
    return {"store_settings": settings}


def analytics(request: HttpRequest) -> Dict[str, Any]:
    """
    Returns the Umami website ID for analytics.
    """
    return {"UMAMI_WEBSITE_ID": getattr(settings, "UMAMI_WEBSITE_ID", "")}


def shop_status(request: HttpRequest) -> Dict[str, Any]:
    """
    Returns whether the shop is disabled via environment variable.
    """
    return {"SHOP_DISABLED": getattr(settings, "SHOP_DISABLED", False)}


def brands(request: HttpRequest) -> Dict[str, Any]:
    """
    Returns brands that have at least one public product.
    """
    return {
        "all_brands": Brand.objects.annotate(
            public_product_count=Count("products", filter=Q(products__public=True))
        )
        .filter(public_product_count__gt=0)
        .order_by("name")
    }
