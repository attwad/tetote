import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet
from .models import Brand, Product


class ProductSitemap(Sitemap):
    i18n = True
    changefreq = "weekly"
    priority = 0.8

    def items(self) -> QuerySet[Product]:
        return Product.objects.filter(public=True)

    def lastmod(self, obj: Product) -> datetime.datetime:
        return obj.date_added


class BrandSitemap(Sitemap):
    i18n = True
    changefreq = "monthly"
    priority = 0.5

    def items(self) -> QuerySet[Brand]:
        return Brand.objects.all()
