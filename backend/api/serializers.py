from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import Subscribtion, User

from .fields import Base64ImageField


class RecipeLiteSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe с базовыми полями.
        Используется как вложенный сериализатор."""

    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'cooking_time')


class CustomUserSerializer(UserSerializer):
    """Сериализатор для пользователя."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        """Метод, который показывает,
            подписан ли текущий пользователь на просматриваемого."""
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscribtion.objects.filter(user=user, author=obj.id).exists()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор создания пользователя."""

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 'password', 'id'
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer для модели Subscribtion."""

    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscribtion
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        """Метод, который показывает,
            подписан ли текущий пользователь на просматриваемого."""
        user = self.context.get('request').user
        if not user.is_anonymous:
            return Subscribtion.objects.filter(
                user=obj.user,
                author=obj.author).exists()
        return False

    def get_recipes(self, obj):
        """Получение всех рецептов конкретного пользователя
            с учетом количества обЪектов внутри поля recipes."""
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.author)
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        return RecipeLiteSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Получение количества рецептов пользователя."""
        return Recipe.objects.filter(author=obj.author).count()


class IngredientListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка имеющихся ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Tag."""

    class Meta:
        model = Tag
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Cериализатор ингредиентов в рецепте."""

    name = serializers.StringRelatedField(
        source='ingredient.name')
    measurement_unit = serializers.StringRelatedField(
        source='ingredient.measurement_unit'
    )
    id = serializers.ReadOnlyField(source='ingredient.id')

    class Meta:
        model = RecipeIngredient
        fields = ('name', 'id', 'amount', 'measurement_unit')


class RecipeFavoriteAndCartSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe для чтения информации по рецептам."""

    author = CustomUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagSerializer(
        many=True,
        read_only=True)
    ingredients = serializers.SerializerMethodField()

    def get_ingredients(self, obj):
        """Получение поля ингредиентов."""
        return RecipeIngredientSerializer(
            RecipeIngredient.objects.filter(recipe=obj).all(), many=True
        ).data

    def get_is_favorited(self, obj):
        """Получение поля рецепт в избранном или нет."""
        user_id = self.context.get('request').user.id
        return Favorite.objects.filter(
            user=user_id, recipe=obj.id).exists()

    def get_is_in_shopping_cart(self, obj):
        """Получение поля рецепт в корзине или нет."""
        user_id = self.context.get('request').user.id
        return ShoppingCart.objects.filter(
            user=user_id, recipe=obj.id).exists()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'image', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart', 'name',
                  'text', 'cooking_time')


class IngredientAmountCreateSerializer(serializers.ModelSerializer):
    """Cериализатор количества ингредиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe для создания и обновления рецепта."""
    ingredients = IngredientAmountCreateSerializer(write_only=True, many=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    image = Base64ImageField()
    author = CustomUserSerializer(required=False, read_only=True)

    def validate(self, value):
        """Валидация ингредиентов."""
        if not value.get('ingredients'):
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы один ингредиент!')
        inrgedient_id_list = [item['id']
                              for item in value.get('ingredients')]
        unique_ingredient_id_list = set(inrgedient_id_list)
        if len(inrgedient_id_list) != len(unique_ingredient_id_list):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальны!')
        for ingredient in value.get('ingredients'):
            amount = int(ingredient.get('amount'))
            if amount < 1:
                raise serializers.ValidationError(
                    {'amount': ['Количество не может быть менее 1!']})
        return value

    @transaction.atomic
    def create_ingredients(self, ingredients_data, recipe):
        """Создание записей: ингредиент - рецепт - количество."""
        create_ingredients = [RecipeIngredient(
            recipe=recipe,
            ingredient=ingred['id'],
            amount=ingred['amount']) for ingred in ingredients_data]
        RecipeIngredient.objects.bulk_create(create_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        """Создание рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.save()
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)
        if 'tags' in validated_data:
            tags_data = validated_data.pop('tags')
            instance.tags.set(tags_data)
        return super().update(
            instance, validated_data)

    def to_representation(self, instance):
        """Добавление полей с ингредиентами."""
        ingredients = super().to_representation(instance)
        ingredients['ingredients'] = RecipeIngredientSerializer(
            instance.recipeingredient_set.all(), many=True).data
        return ingredients

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text', 'ingredients',
                  'tags', 'cooking_time')
