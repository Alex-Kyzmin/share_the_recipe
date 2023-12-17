from django.contrib.auth import get_user_model
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.db.models import UniqueConstraint

from foodgram.settings import (MAX_COOKING_TIME, MAX_INGRREDIENT_VALUE,
                               MAX_LENGTH_COLOR, MAX_LENGTH_RECIPE_MODEL,
                               MIN_COOKING_TIME, MIN_INGRREDIENT_VALUE)

User = get_user_model()


class Ingredient(models.Model):
    """Модель для данных - Ингридиент."""
    name = models.CharField(
        max_length=MAX_LENGTH_RECIPE_MODEL,
        verbose_name='Название',
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_RECIPE_MODEL,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Tag(models.Model):
    """Модель для данных - Тэг к рецепту."""
    name = models.CharField(
        max_length=MAX_LENGTH_RECIPE_MODEL,
        unique=True,
        verbose_name='Название тэга',
    )
    color = models.CharField(
        max_length=MAX_LENGTH_COLOR,
        unique=True,
        verbose_name="Цвет HEX",
        validators=[
            RegexValidator(
                "^#([a-fA-F0-9]{6})",
                message="Поле должно содержать 7-значный HEX-код цвета.",
            )
        ],
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH_RECIPE_MODEL,
        unique=True,
        null=True,
        verbose_name='Уникальный слаг',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """ Модель для данных - Рецепт."""
    name = models.CharField(
        max_length=MAX_LENGTH_RECIPE_MODEL,
        unique=True,
        verbose_name='Название блюда',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    image = models.ImageField(
        verbose_name='Изображение блюда',
        blank=True,
        upload_to='recipes/'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления блюда',
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message='Не менее 1 минуты!'),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message='Не более 32 000 минут!'),
        ]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        through_fields=('recipe', 'ingredient'),
        verbose_name='Список ингредиентов для рецепта',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name[:10]


class IngredientInRecipe(models.Model):
    """Модель для данных - связь Ингридиентов и Рецепта."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(
                MIN_INGRREDIENT_VALUE,
                message='Не менее 1 единицы'
            ),
            MaxValueValidator(
                MAX_INGRREDIENT_VALUE,
                message='Не менее 1 единицы'
            ),
        ]
    )

    class Meta:
        verbose_name = 'Ингредиенты в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ing_recipe',
            )
        ]

    def __str__(self):
        ingredient = self.ingredient.name
        ingredient_unit = self.ingredient.measurement_unit
        amount = self.amount
        return (
            f'{ingredient} ({ingredient_unit}) - {amount} '
        )


class FavouriteRecipe(models.Model):
    """Модель для данных - Избранное."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_autor',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites_recipe',
        verbose_name='Избранный рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = verbose_name
        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favourite',
            )
        ]

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Избранное'


class ShoppingCart(models.Model):
    """Модель для данных - список покупок."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_user',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт',
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Корзина покупок'
        verbose_name_plural = verbose_name
        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart',
            )
        ]

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в список для покупок'
