from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer
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


class SubscribeSerializer(ProjectUserSerializer):
    recipes_count = SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta(ProjectUserSerializer.Meta):
        fields = ProjectUserSerializer.Meta.fields + (
            'recipes_count', 'recipes'
        )
        read_only_fields = ('email', 'username')

    def validate(self, data):
        user = self.context['request'].user
        if Subscribe.objects.filter(author=self.instance, user=user).exists():
            raise ValidationError(
                detail='Вы подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user == self.instance:
            raise ValidationError(
                detail='Вы не можете подписаться на самого себя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context['request']
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = SmallRecipeSerializer(
            recipes,
            many=True,
            read_only=True,
        )
        return serializer.data


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(ModelSerializer):
    id = IntegerField(write_only=True)

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'quantity')


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class ReadRecipeSerializer(ModelSerializer):
    tags = TagSerializer(
        many=True,
        read_only=True,
    )
    author = ProjectUserSerializer(read_only=True,)
    ingredients = SerializerMethodField()
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_list = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            quantity=F('ingredientinrecipe__quantity')
        )
        return ingredients

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated and
            user.favorites.filter(recipe=obj).exists()
        )

    def get_is_in_shopping_list(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated and
            user.shopping_list.filter(recipe=obj).exists()
        )


class RecordRecipeSerializer(ModelSerializer):
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                  many=True)
    author = ProjectUserCreateSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def validate_ingredients(self, value):
        ingredients = value
        if not ingredients:
            raise ValidationError({
                'ingredients': 'Нужен хотя бы один ингредиент!'
            })
        ingredients_list = []
        for i in ingredients:
            ingredient = get_object_or_404(Ingredient, id=i['id'])
            if ingredient in ingredients_list:
                raise ValidationError({
                    'ingredients': '"Этот ингридиент уже был"!'
                })
            if int(i['quantity']) <= 0:
                raise ValidationError({
                    'amount': 'Вы забыли ввести количество ингридиента!'
                })
            ingredients_list.append(ingredient)
        return value

    def validate_tags(self, value):
        tags = value
        if not tags:
            raise ValidationError({'tags': 'Выбирете тег для рецепта!'})
        tags_list = []
        for tag in tags:
            if tag in tags_list:
                raise ValidationError({'tags': 'Вы уже добавили этот тег к рецепту!'})
            tags_list.append(tag)
        return value

    @transaction.atomic
    def create_ingredients_quantity(self, ingredients, recipe):
        IngredientInRecipe.objects.bulk_create(
            [IngredientInRecipe(
                ingredient=Ingredient.objects.get(id=ingredient['id']),
                recipe=recipe,
                quantity=ingredient['quantity']
            ) for ingredient in ingredients]
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_quantity(recipe=recipe, ingredients=ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_quantity(recipe=instance, ingredients=ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        context = {'request': self.context['request']}
        return ReadRecipeSerializer(instance, context=context).data


class SmallRecipeSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
