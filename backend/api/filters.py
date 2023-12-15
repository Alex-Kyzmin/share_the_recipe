from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, filters
from recipes.models import Ingredient, Recipe, Tag

User = get_user_model()


class IngredientFilter(FilterSet):
    """Фильтры для вью - ингридиенты."""
    name = filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    """Фильтры для вью - рецепты."""
    tags = filters.AllValuesMultipleFilter(field_name="tags__slug", label="tags")
    author = filters.AllValuesFilter(field_name='author')
    is_favorited = filters.BooleanFilter(
        method='filter_is_favorited',
    )
    is_in_shopping_list = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'is_favorited',
            'is_in_shopping_list',
        )

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(author_id=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_user__user=user)
        return queryset
