import base64
import re

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (FavouriteRecipe, Ingredient, IngredientInRecipe,
                            Recipe, ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.relations import PrimaryKeyRelatedField
from users.models import Subscribe
from foodgram.settings import (MIN_INGRREDIENT_VALUE, MAX_INGRREDIENT_VALUE,
                               MIN_COOKING_TIME, MAX_COOKING_TIME)

User = get_user_model()


class ProjectUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
        )

    def validate_username(self, value):
        vald_value = r'^[\w.@+-]+\Z'
        if value == 'me':
            raise serializers.ValidationError(
                'Невозможно создать пользователя с таким именем!'
            )
        if not re.match(vald_value, value):
            raise serializers.ValidationError(
                'Имя не соответствующие регулярному выражению!'
            )
        return value


class ProjectUserSerializer(UserSerializer):
    """Сериализатор для использования данных пользователя."""
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return obj.subscribing.filter(user=user).exists()


class SubscribeSerializer(ProjectUserSerializer):
    """Сериализатор для демонстрации подписок пользователя."""
    recipes = SerializerMethodField(read_only=True)
    recipes_count = SerializerMethodField(read_only=True)

    class Meta(ProjectUserSerializer.Meta):
        fields = ProjectUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, object):
        request = self.context.get('request')
        context = {'request': request}
        limit = request.query_params.get('recipes_limit')
        queryset = object.recipes.all()
        if limit:
            queryset = queryset[:int(limit)]
        return SmallRecipeSerializer(
            queryset,
            context=context,
            many=True).data

    @staticmethod
    def get_recipes_count(obj):
        return obj.recipes.count()


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингридиенты."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингридиенты в рецептах."""
    id = IntegerField(write_only=True)

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели тэг к рецепту."""

    class Meta:
        model = Tag
        fields = '__all__'


class SmallRecipeSerializer(serializers.ModelSerializer):
    """
    Вспомогательный сериализатор к модели подписки
    для вывода данных по рецептам у подписчика.
    """
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class ReadRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для демонстрации рецепта."""
    tags = TagSerializer(
        many=True,
        read_only=True,
    )
    author = ProjectUserSerializer(read_only=True,)
    ingredients = SerializerMethodField(read_only=True,)
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_ingredients(self, obj):
        ingredients = obj.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=models.F('ingredients_amount__amount')
        )
        return ingredients

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if (
            user.is_authenticated
            and user.favorites.filter(recipe=obj).exists()
        ):
            return True
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if (
            user.is_authenticated
            and user.shopping_cart.filter(recipe=obj).exists()
        ):
            return True
        return False


class RecordRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта."""
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    author = ProjectUserCreateSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def validate_ingredients(self, value):
        ingredients_list = []
        if not value:
            raise serializers.ValidationError({
                'ingredients': 'Минимальное значение - 1 ингредиент!'
            })
        ingredients_list = []
        for element in value:
            ingredient = get_object_or_404(Ingredient, id=element['id'])
            if ingredient in ingredients_list:
                raise serializers.ValidationError({
                    'ingredients': 'Этот ингридиент уже добавлен!'
                })
            if int(element['amount']) <= 0:
                raise serializers.ValidationError({
                    'amount': 'Вы забыли ввести количество ингридиента!'
                })
            ingredients_list.append(ingredient)
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                {'tags': 'Выбирете хотя бы 1 тег для рецепта!'}
            )
        tags_list = []
        for tag in value:
            if tag in tags_list:
                raise serializers.ValidationError(
                    {'tags': 'Вы уже добавили этот тег к рецепту!'}
                )
            tags_list.append(tag)
        return value

    def validate_cooking_time(self, value):
        if int(value) < 1:
            raise serializers.ValidationError(
                'Минимальное время приготовления 1 минута'
            )
        return value

    @transaction.atomic
    def create_ingredients_amt(self, ingredients, recipe):
        IngredientInRecipe.objects.bulk_create(
            [IngredientInRecipe(
                ingredient=Ingredient.objects.get(id=ingredient['id']),
                recipe=recipe,
                amount=ingredient['amount']
            ) for ingredient in ingredients]
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amt(recipe=recipe, ingredients=ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amt(recipe=instance, ingredients=ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        context = {'request': self.context['request']}
        return ReadRecipeSerializer(instance, context=context).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для демонстрации избранных рецептов."""
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = FavouriteRecipe
        fields = (
            'id',
            'name',
            'cooking_time',
            'image',
        )

    def validate(self, data):
        user = self.context.get('request').user
        recipe = self.context['recipe']
        if FavouriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'error': 'Вы уже добавили этот рецепт в избранное'}
            )
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для демонстрации списков продуктов из рецептов."""
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = ShoppingCart
        fields = (
            'id',
            'name',
            'cooking_time',
            'image',
        )

    def validate(self, data):
        user = self.context.get('request').user
        recipe = self.context['recipe']
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'error': 'Вы уже добавили этот рецепт в список покупок'}
            )
        return data
