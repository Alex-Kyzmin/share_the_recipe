from django_filters.rest_framework import FilterSet, filters

from recipes.models import Recipe


class RecipeFilter(FilterSet):
    """Фильтры к модели рецептов"""
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')
    is_favorited = filters.BooleanFilter(
        method='is_favorited_filter',
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='is_in_shopping_cart_filter',
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author',)

    def is_favorited_filter(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorites_recipe__user=user)
        return queryset

    def is_in_shopping_cart_filter(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset
