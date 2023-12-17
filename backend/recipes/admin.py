from django.contrib import admin

from foodgram.settings import INLINE_MAX, INLINE_MIN
# настройка админ-зоны для импортируемых моделей
from recipes.models import (FavouriteRecipe, Ingredient, IngredientInRecipe,
                            Recipe, ShoppingCart, Tag)


class IngredientInRecipeInline(admin.TabularInline):
    model = Recipe.ingredients.through
    list_display = (
        'id',
        'recipe',
        'ingredient',
        'amount',
    )
    min_num = INLINE_MIN
    max_num = INLINE_MAX


@admin.register(Recipe)
class RecipesAdmin(admin.ModelAdmin):
    inlines = (IngredientInRecipeInline,)
    list_display = (
        'id',
        'name',
        'author',
        'count_favorites',
        'text',
        'cooking_time',
        'image',
        'tags_list',
        'ingredients_list',
    )
    list_filter = ('author', 'name', 'tags',)
    readonly_fields = ('count_favorites',)
    search_fields = ('name',)

    @admin.display(description='Добавлено в избранное')
    def count_favorites(self, obj):
        return obj.favorites_recipe.count()

    @admin.display(description='Ингридиенты')
    def ingredients_list(self, obj):
        return ','.join([i.name for i in obj.ingredients.all()])

    @admin.display(description='Тэги')
    def tags_list(self, obj):
        return ','.join([i.name for i in obj.tags.all()])


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    search_fields = ('name', 'measurement_unit',)
    list_filter = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)


@admin.register(FavouriteRecipe)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    search_fields = ('user', 'recipe',)


@admin.register(IngredientInRecipe)
class IngredientInRecipe(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount',)
