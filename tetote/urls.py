from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from integrations.views import stripe_webhook

from shop.sitemaps import ProductSitemap, BrandSitemap
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    i18n = True
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        items = [
            "shop:home",
            "shop:product_list",
            "shop:privacy_policy",
            "shop:return_policy",
            "shop:terms",
        ]
        if not getattr(settings, "SHOP_DISABLED", False):
            items.insert(1, "shop:cart")
        return items

    def location(self, item):
        return reverse(item)


sitemaps = {
    "static": StaticViewSitemap,
}

if not getattr(settings, "SHOP_DISABLED", False):
    sitemaps.update(
        {
            "products": ProductSitemap,
            "brands": BrandSitemap,
        }
    )


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    # Exempt from i18n_patterns (like webhooks)
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", robots_txt, name="robots_txt"),
]

urlpatterns += i18n_patterns(
    path("i18n/", include("django.conf.urls.i18n")),
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("shop.urls")),
    path("blog/", include("blog.urls")),
    path("news/", include("news.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
