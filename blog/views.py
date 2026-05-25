from django.shortcuts import render, get_object_or_404
from .models import BlogPost


def blog_list(request):
    posts = BlogPost.objects.all()
    return render(
        request, "blog/blog_index_page.html", {"blogpages": posts, "title": "Blog"}
    )


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    return render(request, "blog/blog_page.html", {"page": post})
