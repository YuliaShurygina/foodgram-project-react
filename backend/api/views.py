from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from users.models import Subscribtion, User

from .filters import RecipeFilter
from .pagination import CustomPageNumberPagination
from .permissions import AuthorOrReadOnly
from .serializers import (IngredientListSerializer,
                          RecipeCreateUpdateSerializer,
                          RecipeFavoriteAndCartSerializer,
                          RecipeLiteSerializer, SubscriptionSerializer,
                          TagSerializer)


class CustomUserViewSet(UserViewSet):
    """ViewSet для работы с пользователями."""

    http_method_names = ['get', 'post', 'delete']
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        if self.action in ['subscibe', 'subscriptions']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['subscibe', 'subscriptions']:
            return SubscriptionSerializer
        return super().get_serializer_class()

    @action(methods=['post', 'delete'], detail=True)
    def subscribe(self, request, *args, **kwargs):
        """Подписка и отписка от пользователя."""
        user = self.request.user
        author = get_object_or_404(User, id=self.kwargs.get('id'))
        if user == author:
            return Response(
                {'errors': 'На себя нельзя подписаться / отписаться'},
                status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscribtion.objects.filter(
            author=author, user=user)
        if request.method == 'POST':
            if subscription.exists():
                return Response(
                    {'errors': 'Нельзя подписаться повторно'},
                    status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscriptionSerializer(
                data=request.data, context={"request": request,
                                            "author": author})
            serializer.is_valid(raise_exception=True)
            serializer.save(author=author, user=user)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == "DELETE":
            if not subscription.exists():
                return Response(
                    {'errors': 'Нельзя отписаться повторно'},
                    status=status.HTTP_400_BAD_REQUEST)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def subscriptions(self, request):
        """Возвращает пользователей, на которых
            подписан текущий пользователь."""
        subscriptions = Subscribtion.objects.filter(user=self.request.user)
        pages = self.paginate_queryset(subscriptions)
        serializer = SubscriptionSerializer(
            pages,
            many=True,
            context={'request': request})
        return self.get_paginated_response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с рецептами."""

    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = RecipeFilter
    permission_classes = (AuthorOrReadOnly,)
    pagination_class = CustomPageNumberPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action in SAFE_METHODS:
            return RecipeFavoriteAndCartSerializer
        else:
            return RecipeCreateUpdateSerializer

    def delete_relation(self, model, user, pk, name):
        """"Удаление рецепта из списка пользователя."""
        recipe = get_object_or_404(Recipe, pk=pk)
        relation = model.objects.filter(user=user, recipe=recipe)
        if not relation.exists():
            return Response(
                {'errors': f'Нельзя повторно удалить рецепт из {name}'},
                status=status.HTTP_400_BAD_REQUEST)
        relation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def add(self, model, user, pk, name, request):
        """Добавление рецепта в список пользователя."""
        recipe = get_object_or_404(Recipe, pk=pk)
        relation = model.objects.filter(user=user, recipe=recipe)
        if relation.exists():
            return Response(
                {'errors': f'Нельзя повторно добавить рецепт в {name}'},
                status=status.HTTP_400_BAD_REQUEST)
        model.objects.create(user=user, recipe=recipe)
        serializer = RecipeLiteSerializer(recipe, data=request.data,
                                          context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['post', 'delete'], detail=True)
    def favorite(self, request, pk=None):
        """Избранное: добавление и удаление рецептов."""
        user = request.user
        if request.method == 'POST':
            name = 'Избранное'
            return self.add(Favorite, user, pk, name, request)
        if request.method == 'DELETE':
            name = 'избранного'
            return self.delete_relation(Favorite, user, pk, name)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(methods=['post', 'delete'], detail=True)
    def shopping_cart(self, request, pk=None):
        """Список покупок: добавление и удаление рецептов."""
        user = request.user
        if request.method == 'POST':
            name = 'список покупок'
            return self.add(ShoppingCart, user, pk, name, request)
        if request.method == 'DELETE':
            name = 'списка покупок'
            return self.delete_relation(ShoppingCart, user, pk, name)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(methods=['get'], detail=False,
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        """Cкачать список покупок."""
        items = RecipeIngredient.objects.select_related(
            'recipe', 'ingredient')
        items = items.filter(
            recipe__recipe_shopping_cart__user=request.user,)
        items = items.values('ingredient__name', 'ingredient__measurement_unit'
                             ).annotate(
            name=F('ingredient__name'),
            units=F('ingredient__measurement_unit'),
            total=Sum('amount'),
        ).order_by('-total')
        text = '\n'.join([
            f"{item['name']} {item['units']} - {item['total']}"
            for item in items
        ])
        filename = "foodgram_shopping_cart.txt"
        response = HttpResponse(text, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response


class IngredientViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с ингредиентами."""

    serializer_class = IngredientListSerializer
    pagination_class = None
    http_method_names = ['get']

    def get_queryset(self):
        queryset = Ingredient.objects
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset.all()


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с тэгами."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    http_method_names = ['get']
