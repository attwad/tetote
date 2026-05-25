from django.shortcuts import render, get_object_or_404
from .models import NewsItem


def news_list(request):
    newsitems = NewsItem.objects.all()[:5]
    return render(
        request, "news/news_index_page.html", {"newsitems": newsitems, "title": "News"}
    )


def news_detail(request, slug):
    item = get_object_or_404(NewsItem, slug=slug)
    return render(request, "news/news_item.html", {"page": item})
