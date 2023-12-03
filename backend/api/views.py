from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (FavouriteRecipe, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from users.models import Subscribe

from .filters import IngredientFilter, RecipeFilter
from .pagination import ProjectPagination
from .permissions import IsAdminOrReadOnly, IsAdminAuthorOrReadOnly
from .serializers import (IngredientSerializer, ProjectUserCreateSerializer, ProjectUserSerializer,
                          ReadRecipeSerializer, RecordRecipeSerializer, SubscribeSerializer,
                          SmallRecipeSerializer, TagSerializer,)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = ProjectPagination

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ProjectUserSerializer
        return ProjectUserCreateSerializer
    
    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],)
    def me(self, request):
        serializer = ProjectUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'],
        permission_classes=[IsAuthenticated],)
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=request.user)
        serializer = SubscribeSerializer(
            self.paginate_queryset(queryset),
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated],)
    def subscribe(self, request, **kwargs):
        user = request.user
        author_id = self.kwargs['id']
        author = get_object_or_404(User, id=author_id)

        if request.method == 'POST':
            serializer = SubscribeSerializer(author,
                                             data=request.data,
                                             context={"request": request})
            serializer.is_valid(raise_exception=True)
            Subscribe.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = get_object_or_404(Subscribe,
                                             user=user,
                                             author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAdminAuthorOrReadOnly]
    pagination_class = ProjectPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ReadRecipeSerializer
        return RecordRecipeSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.add_to(FavouriteRecipe, request.user, pk)
        else:
            return self.delete_from(FavouriteRecipe, request.user, pk)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.add_to(ShoppingCart, request.user, pk)
        else:
            return self.delete_from(ShoppingCart, request.user, pk)

    def add_to(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = SmallRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_from(self, model, user, pk):
        obj = model.objects.filter(user=user, recipe__id=pk)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Рецепт удален!'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        if not user.shopping_cart.exists():
            return Response(status=HTTP_400_BAD_REQUEST)

        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        shopping_cart = (
            f'Список покупок для: {user.get_full_name()}\n\n'
        )
        shopping_cart += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])

        filename = f'{user.username}_shopping_cart.txt'
        response = HttpResponse(shopping_cart, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
