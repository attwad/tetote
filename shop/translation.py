from modeltranslation.translator import register, TranslationOptions
from .models import Brand, Product, Glaze, ProductType, StoreAnnouncement


@register(Brand)
class BrandTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Glaze)
class GlazeTranslationOptions(TranslationOptions):
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
