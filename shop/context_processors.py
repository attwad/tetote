from .models import StoreAnnouncement


def announcement(request):
    """
    Returns the latest active announcement.
    """
    active_announcement = (
        StoreAnnouncement.objects.filter(is_active=True).order_by("-updated_at").first()
    )
    return {"active_announcement": active_announcement}
