from django.contrib.sitemaps import Sitemap
from .models import Product, Brand


class ProductSitemap(Sitemap):
    i18n = True
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(public=True)

    def lastmod(self, obj):
        return obj.date_added


class BrandSitemap(Sitemap):
    i18n = True
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Brand.objects.all()
