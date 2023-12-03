from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from rest_framework import serializers,status
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
            raise serializers.ValidationError(
                detail='Вы подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user == self.instance:
            raise serializers.ValidationError(
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
            amount=models.F("ingredients_amount__amount")
        )
        return ingredients
    
    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if (user.is_authenticated
            and obj.favorites.filter(user=user).exists()):
            return True
        return False

    def get_is_in_shopping_list(self, obj):
        user = self.context['request'].user
        if (user.is_authenticated
            and obj.ingredients_list_recipes.filter(user=user).exists()):
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
                    'ingredients': '"Этот ингридиент уже добавлен"!'
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
        """Валидация времени приготовления."""
        if int(value) < 1:
            raise serializers.ValidationError(
                "Минимальное время приготовления 1 минута"
            )
        return value
    
    @transaction.atomic
    def add_ingredients_and_tags(self, instance, **validate_data):
        """Добавление ингредиентов тегов."""
        ingredients = validate_data['ingredients']
        tags = validate_data['tags']
        for tag in tags:
            instance.tags.add(tag)

        IngredientInRecipe.objects.bulk_create(
            [
                IngredientInRecipe(
                    recipe=instance,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount'),
                )
                for ingredient in ingredients
            ]
        )
        return instance
    
    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = super().create(validated_data)
        self.add_ingredients_and_tags(
            recipe,
            ingredients=ingredients,
            tags=tags,
        )
        return recipe
    
    @transaction.atomic
    def update(self, instance, validated_data):
        instance.ingredients.clear()
        instance.tags.clear()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = self.add_ingredients_and_tags(
            recipe=instance,
            ingredients=ingredients,
            tags=tags,
        )
        instance.save()
        return instance

    def to_representation(self, instance):
        context = {'request': self.context['request']}
        return ReadRecipeSerializer(instance, context=context).data
