from django.contrib import admin
from .models import Product, Color, Size, ProductVariantImage

admin.site.register(Product)
admin.site.register(Color)
admin.site.register(Size)
admin.site.register(ProductVariantImage)

