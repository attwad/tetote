from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from integrations.views import stripe_webhook

urlpatterns = [
    # Exempt from i18n_patterns (like webhooks)
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("markdownx/", include("markdownx.urls")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("shop.urls")),
    path("blog/", include("blog.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
