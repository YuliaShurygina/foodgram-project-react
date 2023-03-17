from django_filters.rest_framework import (FilterSet,
                                           ModelMultipleChoiceFilter, filters)

from recipes.models import Recipe, Tag
from users.models import User


class RecipeFilter(FilterSet):
    """Фильтрация списка рецептов по тегам"""
    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    is_favorited = filters.BooleanFilter(method='favorited_filter')
    is_in_shopping_cart = filters.BooleanFilter(method='shopping_cart_filter')

    def filter_favorited(self, queryset, name, value):
        if value:
            return queryset.filter(favorite__user=self.request.user)
        return queryset

    def filter_shopping_cart(self, queryset, name, value):
        if value:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('tags', 'author')
