from modeltranslation.translator import register, TranslationOptions
from .models import Brand, Product, Yakikata, ProductType, StoreAnnouncement


@register(Brand)
class BrandTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(Yakikata)
class YakikataTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(ProductType)
class ProductTypeTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(StoreAnnouncement)
class StoreAnnouncementTranslationOptions(TranslationOptions):
    fields = ("text",)
