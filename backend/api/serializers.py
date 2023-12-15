import base64
import re

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.validators import (MinValueValidator, MaxValueValidator,
                                    RegexValidator)
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (FavouriteRecipe, Ingredient, IngredientInRecipe,
                            Recipe, ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from rest_framework.relations import PrimaryKeyRelatedField
from api.pagination import SubscribePagination
from users.models import Subscribe
from foodgram.settings import (MIN_INGRREDIENT_VALUE, MAX_INGRREDIENT_VALUE,
                               MIN_COOKING_TIME, MAX_COOKING_TIME, MAX_LENGTH_USER_MODEL, MAX_LENGTH_EMAIL)

User = get_user_model()


class ProjectUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""
    id = serializers.ReadOnlyField()
    username = serializers.CharField(
        max_length=MAX_LENGTH_USER_MODEL,
        required=True,
    )
    email = serializers.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        required=True,
    )
    first_name = serializers.CharField(
        max_length=MAX_LENGTH_USER_MODEL,
        required=True,
    )
    last_name = serializers.CharField(
        max_length=MAX_LENGTH_USER_MODEL,
        required=True,
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
    )


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
    is_subscribed = SerializerMethodField()

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
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta(ProjectUserSerializer.Meta):
        fields = ProjectUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def validate(self, attrs):
        user = self.context['request'].user
        if user == self.instance:
            raise serializers.ValidationError(
                {'errors': 'Вы пытаетесь подписаться на самого себя'},
            )
        if Subscribe.objects.filter(
            autor=self.instance,
            user=user
        ).exists():
            raise serializers.ValidationError(
                {'errors': 'Вы уже подписаны на этого автора'},
            )
        return super().validate(attrs)

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = SubscribePagination().paginate_queryset(
            obj.recipes.all(),
            request,
        )
        return SmallRecipeSerializer(
            recipes,
            many=True,
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингридиенты."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингридиенты в рецептах."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecordIngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингридиенты в рецептах."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
    )
    amount = serializers.IntegerField(
        min_value = MIN_INGRREDIENT_VALUE,
        max_value = MAX_INGRREDIENT_VALUE,
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount',)


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
    image = Base64ImageField(read_only=True)
    cooking_time = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()

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
    author = ProjectUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        read_only=True,
        source='recipes',

    )
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'image',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'text',
            'cooking_time',
        )

    def general_value(self, model, obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and model.objects.filter(user=user, recipe=obj).exists())

    def get_is_favorited(self, obj):
        return self.general_value(ShoppingCart, obj)
        

    def get_is_in_shopping_cart(self, obj):
        return self.general_value(FavouriteRecipe, obj)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class RecordRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта."""
    id = serializers.ReadOnlyField()
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
        allow_null=False,
    )
    author = ProjectUserSerializer(read_only=True)
    ingredients = RecordIngredientInRecipeSerializer(
        many=True,
        required=True,
        allow_null=False,
        )
    image = Base64ImageField()
    cooking_time =serializers.IntegerField(
        min_value = MIN_COOKING_TIME,
        max_value = MAX_COOKING_TIME,
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def validate_ingredients(self, value):
        if len(value) != len(set([element['id'] for element in value])):
            raise serializers.ValidationError(
                {'ingredients': 'Этот ингридиент уже добавлен!'}
            )
        return value

    def validate_tags(self, value):
        if len(value) != len(set(element.id for element in value)):
            raise serializers.ValidationError(
                {'ingredients': 'Этот тэг уже добавлен!'}
            )
        return value

    @transaction.atomic
    def add_ingredients_tags(self, recipe, tags, ingredients):
        recipe.tags.set(tags)
        ingredients = [IngredientInRecipe(
            ingredient=Ingredient.objects.get(id=ingredient['id'].id),
            recipe=recipe,
            amount=ingredient['amount']
        ) for ingredient in ingredients]
        IngredientInRecipe.objects.bulk_create(
            sorted(
                ingredients,
                key=lambda obj: obj.ingredient.name
            )
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            **validated_data,
        )
        self.add_ingredients_tags(recipe, tags, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time,
        )
        IngredientInRecipe.objects.filter(
            recipe=instance,
            ingredient=instance.ingredients.all()
        ).delete
        self.add_ingredients_tags(instance, tags, ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        return ReadRecipeSerializer(
            instance,
            context=self.context
        ).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для демонстрации избранных рецептов."""

    class Meta:
        model = FavouriteRecipe
        fields = (
            'user',
            'recipe',
        )

    def validate(self, data):
        if FavouriteRecipe.objects.filter(**data).exists():
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
