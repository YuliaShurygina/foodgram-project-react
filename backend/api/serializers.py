import base64

from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import Subscribtion, User


class Base64ImageField(serializers.ImageField):
    """Кастомный тип поля Base64ImageField."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


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
        username = self.context['request'].user
        if not username.is_authenticated:
            return False
        user = get_object_or_404(User, username=username)
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Получение поля рецепт в корзине или нет."""
        username = self.context['request'].user
        if not username.is_authenticated:
            return False
        user = get_object_or_404(User, username=username)
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()

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
    author = CustomUserSerializer(required=False)

    def validate_ingredients(self, value):
        """Валидация ингредиентов."""
        if len(value) < 1:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы один ингредиент!')
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Создание рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.save()
        recipe.tags.set(tags_data)
        create_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingred['id'],
                amount=ingred['amount']) for ingred in ingredients_data]
        RecipeIngredient.objects.bulk_create(create_ingredients)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        instance.name = validated_data.get('name', instance.name)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        ingredients_data = validated_data.pop('recipeingredient_set', None)
        tags_data = validated_data.pop('tags', None)
        if tags_data is not None:
            instance.tags.set(tags_data)
        if ingredients_data is not None:
            RecipeIngredient.objects.filter(recipe=instance).delete()
            create_ingredients = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient=ingred['id'],
                    amount=ingred['amount']
                )
                for ingred in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(create_ingredients)
        instance.save()
        return instance

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