from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Ingredient, IngredientInRecipe, FavouriteRecipe,
                            Recipe, ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from users.models import Subscribe

User = get_user_model()


class ProjectUserCreateSerializer(UserCreateSerializer):
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


class ProjectUserSerializer(UserSerializer):
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
        user = self.context['request'].user
        return (
            user.is_authenticated and
            Subscribe.objects.filter(user=user, author=obj).exists()
        )


class SubscribeSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscribe
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def validate(self, data):
        user = self.context['request'].user
        author = self.instance
        if author == user:
            raise serializers.ValidationError(
                {'error': 'Нельзя подписаться на самого себя'}
            )
        if Subscribe.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                {'error': 'Вы уже подписаны на этого автора'}
            )
        return data

    def get_is_subscribed(self, obj):
        return (
            Subscribe.objects.filter(
                user=self.context['request'].user,
                author=obj).exists()
        )

    @staticmethod
    def get_recipes(attrs):
        return SmallRecipeSerializer(
            Recipe.objects.filter(author=attrs.author),
            many=True,
        ).data

    @staticmethod
    def get_recipes_count(attrs):
        return Recipe.objects.filter(author=attrs.author).count()


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = IntegerField(write_only=True)

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class SmallRecipeSerializer(serializers.ModelSerializer):
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
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=models.F('ingredients_amount__amount')
        )
        return ingredients
    
    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if (user.is_authenticated
            and user.favorites.filter(recipe=obj).exists()):
            return True
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if (user.is_authenticated
            and user.shopping_cart.filter(recipe=obj).exists()):
            return True
        return False


class RecordRecipeSerializer(serializers.ModelSerializer):
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
        ingredients = value
        ingredients_list = []
        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Нужен минимум 1 ингредиент!'
            })
        ingredients_list = []
        for i in ingredients:
            ingredient = get_object_or_404(Ingredient, id=i['id'])
            if ingredient in ingredients_list:
                raise serializers.ValidationError({
                    'ingredients': 'Этот ингридиент уже добавлен!'
                })
            if int(i['amount']) <= 0:
                raise serializers.ValidationError({
                    'amount': 'Вы забыли ввести количество ингридиента!'
                })
            ingredients_list.append(ingredient)
        return value

    def validate_tags(self, value):
        tags = value
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Выбирете хотя бы 1 тег для рецепта!'}
            )
        tags_list = []
        for tag in tags:
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
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = FavouriteRecipe
        fields = ('id', 'name', 'cooking_time', 'image')

    def validate(self, data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        if FavouriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'error': 'Рецепт уже находится в избранном'}
            )
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'cooking_time', 'image')

    def validate(self, data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'error': 'Рецепт уже находится в списке покупок'}
            )
        return data
