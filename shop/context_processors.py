from django.conf import settings
from .models import StoreAnnouncement, StoreSettings


def announcement(request):
    """
    Returns the latest active announcement.
    """
    active_announcement = (
        StoreAnnouncement.objects.filter(is_active=True).order_by("-updated_at").first()
    )
    return {"active_announcement": active_announcement}


def store_settings(request):
    """
    Returns the store settings.
    """
    settings = StoreSettings.objects.first()
    return {"store_settings": settings}


def analytics(request):
    """
    Returns the Umami website ID for analytics.
    """
    return {"UMAMI_WEBSITE_ID": getattr(settings, "UMAMI_WEBSITE_ID", "")}


def shop_status(request):
    """
    Returns whether the shop is disabled via environment variable.
    """
    return {"SHOP_DISABLED": getattr(settings, "SHOP_DISABLED", False)}
