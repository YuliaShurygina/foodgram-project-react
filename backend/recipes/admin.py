from django.contrib import admin

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1
    extra = 0


class RecipeIngredientAdmin(admin.ModelAdmin):
    fields = ('ingredient', 'recipe', 'amount')
    search_fields = ('ingredient', 'recipe')


class RecipeAdmin(admin.ModelAdmin):

    def added_to_favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    added_to_favorite_count.short_description = 'Добавлений в избранное'
    list_display = ('id', 'name', 'author', 'added_to_favorite_count')
    readonly_fields = ('added_to_favorite_count',)
    search_fields = ('name',)
    list_filter = ('author', 'name', 'tags',)
    filter_horizontal = ('tags',)
    inlines = (RecipeIngredientInline,)
    empty_value_display = '-empty-'


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)
    empty_value_display = '-empty-'


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color',)
    empty_value_display = '-empty-'


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(ShoppingCart)
admin.site.register(Favorite)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
