from django.contrib.sitemaps import Sitemap
from .models import Post


class PostSitemap(Sitemap):
    i18n = True
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Post.objects.all()

    def lastmod(self, obj):
        return obj.created_at
