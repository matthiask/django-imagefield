from django.contrib import admin

from . import models


@admin.register(models.Model)
class ModelAdmin(admin.ModelAdmin):
    pass


@admin.register(models.ModelWithOptional)
class ModelWithOptionalAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    pass
