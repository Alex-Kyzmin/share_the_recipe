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
    
    action(detail=False, methods=['get'],
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
        author = get_object_or_404(User, id=self.kwargs.get('pk'))
        context = {'request': self.request, 'author': author}

        if request.method == 'POST':
            serializer = SubscribeSerializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            Subscribe.objects.create(user=request.user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = get_object_or_404(Subscribe,
                                             user=request.user,
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

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated],)
    def favorite(self, request, **kwargs):
        recipe = self.get_object()

        if request.method == 'POST':
            context = {'request': request, "recipe": recipe}
            serializer = SmallRecipeSerializer(
                recipe,
                data=request.data,
                context=context,)
            if serializer.is_valid(raise_exception=True):
                serializer.save(user=request.user, recipe=recipe)
                return Response(data=serializer.data,
                                status=status.HTTP_201_CREATED,)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if request.method == 'DELETE':
            get_object_or_404(
                 FavouriteRecipe,
                 recipe=recipe,
                user=request.user,
            ).delete()
            return Response({'detail': 'Рецепт удален из избранного!'},
                            status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated],)
    def shopping_cart(self, request, **kwargs):
        recipe = self.get_object()
        
        if request.method == 'POST':
            context = {'request': request, "recipe": recipe}
            serializer = SmallRecipeSerializer(
                data=request.data,
                context=context,
            )
            if serializer.is_valid(raise_exception=True):
                serializer.save(user=request.user, recipe=recipe)
                return Response(data=serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if request.method == 'DELETE':
            get_object_or_404(
                 ShoppingCart,
                 recipe=recipe,
                user=request.user,
            ).delete()
            return Response({'detail': 'Рецепт удален из списка покупок!'},
                            status=status.HTTP_204_NO_CONTENT)
        

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],)
    def download_shopping_cart(self, request, **kwargs):
        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        shopping_cart = (
            f'Список покупок для: {request.user.get_full_name()}\n\n'
        )
        shopping_cart += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])

        filename = f'{request.user.username}_shopping_cart.txt'
        response = HttpResponse(shopping_cart, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
