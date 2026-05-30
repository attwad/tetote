from django.views.generic import ListView, DetailView
from django.utils import translation
from django.shortcuts import get_object_or_404
from .models import BlogPage


class BlogListView(ListView):
    model = BlogPage
    template_name = "blog/blog_list.html"
    context_object_name = "posts"

    def get_queryset(self):
        current_lang = translation.get_language()
        # Get all unique translation keys for live, public blog pages
        # We clear ordering to ensure distinct() works correctly on translation_key
        keys = (
            BlogPage.objects.live()
            .public()
            .order_by()
            .values_list("translation_key", flat=True)
            .distinct()
        )

        posts = []
        for key in keys:
            # Try current language
            post = (
                BlogPage.objects.live()
                .public()
                .filter(translation_key=key, locale__language_code=current_lang)
                .first()
            )
            if not post:
                # Fallback to English
                post = (
                    BlogPage.objects.live()
                    .public()
                    .filter(translation_key=key, locale__language_code="en")
                    .first()
                )
            if not post:
                # Absolute fallback: just pick any translation if English doesn't exist
                post = (
                    BlogPage.objects.live().public().filter(translation_key=key).first()
                )

            if post:
                posts.append(post)

        # Sort by date (or first_published_at)
        posts.sort(key=lambda x: x.date or x.first_published_at, reverse=True)
        return posts


class BlogDetailView(DetailView):
    model = BlogPage
    template_name = "blog/blog_detail.html"
    context_object_name = "page"

    def get_object(self, queryset=None):
        slug = self.kwargs.get("slug")
        current_lang = translation.get_language()

        # First find ANY live, public blog page with this slug to get its translation key
        any_post = BlogPage.objects.live().public().filter(slug=slug).first()
        if not any_post:
            # Try to find by slug in any language if the one provided didn't match
            # (In case someone uses an EN slug in a JA URL or vice versa)
            any_post = get_object_or_404(BlogPage.objects.live().public(), slug=slug)

        key = any_post.translation_key
        # Now look for current language translation of this post
        post = (
            BlogPage.objects.live()
            .public()
            .filter(translation_key=key, locale__language_code=current_lang)
            .first()
        )
        if not post:
            # Fallback to English
            post = (
                BlogPage.objects.live()
                .public()
                .filter(translation_key=key, locale__language_code="en")
                .first()
            )

        # Final fallback to original found post if EN doesn't exist either
        return post or any_post
