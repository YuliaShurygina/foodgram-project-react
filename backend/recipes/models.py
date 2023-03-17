from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models

from users.models import User

ALPHANUMERIC = RegexValidator(
    r'^[0-9a-zA-Z]*$', 'Допустимы только буквы или цифры.'
)


class Tag(models.Model):
    """Модель для хранения тегов."""
    name = models.CharField(max_length=200, blank=False)
    slug = models.SlugField(
        unique=True, max_length=200, validators=[ALPHANUMERIC],
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        default='#00ff7f',)

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        ordering = ('name', )

    def __str__(self) -> str:
        return self.name


class Ingredient(models.Model):
    """Модель для хранения ингредиентов."""

    name = models.CharField(max_length=200, blank=False)
    measurement_unit = models.CharField(max_length=200, blank=False)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name', )
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_for_ingredient'
            ),)

    def __str__(self) -> str:
        return f'{self.name} {self.measurement_unit}'


class Recipe(models.Model):
    """Модель для хранения рецепта."""

    name = models.CharField(max_length=200, blank=False)
    text = models.TextField(
        'Текст рецепта',
        help_text='Текст нового рецепта',
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег',
        related_name='recipes')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты блюда',
    )
    image = models.ImageField(
        'Картинка',
        upload_to='recipes/images',
        blank=True
    )
    cooking_time = models.IntegerField(
        "Время приготовления в минутах",
        default=1,
        validators=(MinValueValidator(1, 'Минимум 1 минута'),),)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)
        constraints = [
            models.UniqueConstraint(
                fields=["name", "author"], name="unique_for_author"
            )
        ]

    def __str__(self) -> str:
        return f'{self.name}. Автор: {self.author.username}'


class RecipeIngredient(models.Model):
    """Модель для хранения ингредиентов в рецепте."""

    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Связанные ингредиенты',
        on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Ингредиенты рецепта',
        on_delete=models.CASCADE
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        default=0,
        validators=(
            MinValueValidator(0),
            MaxValueValidator(1000),
        ),
    )

    class Meta:
        verbose_name = 'Ингредиенты'
        verbose_name_plural = 'Количество ингредиентов'
        ordering = ('recipe', )
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_for_recipe'
            ),)

    def __str__(self):
        return f'{self.amount} {self.ingredient}'


class Favorite(models.Model):
    """Модель избранного."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Избранное',
        related_name='favorite_recipe',)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorite',
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "user", ], name="is_favorite_already"
            )
        ]

    def __str__(self) -> str:
        return f'{self.user} -> {self.recipe}'


class ShoppingCart(models.Model):
    """Модель корзины покупок."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь_списка',
        related_name='shopping_cart',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепты в список покупок',
        related_name='recipe_shopping_cart',)

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "user", ], name="is_in_cart_already"
            )
        ]

    def __str__(self) -> str:
        return f'{self.user} -> {self.recipe}'
