from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import (FavouriteRecipe, Ingredient, IngredientInRecipe,
                            Recipe, ShoppingCart, Tag)
from users.models import Subscribe
from .filters import RecipeFilter
from .pagination import ProjectPagination
from .permissions import IsAdminAuthorOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          ProjectUserSerializer, ReadRecipeSerializer,
                          RecordRecipeSerializer, SmallRecipeSerializer,
                          SubscribeSerializer, TagSerializer)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """
    Вьюсет для работы с пользователями
    (создание, редактирование, смена пароля),
    а так же  для авторизованных пользователей
    подписки(создание, удаление и демонстрации подписок).
    """
    queryset = User.objects.all()
    pagination_class = ProjectPagination

    @action(detail=False, methods=['GET'], url_path='me',
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = ProjectUserSerializer(self.request.user,
                                           context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)

        if Subscribe.objects.filter(user=request.user,
                                    author=author):
            return Response({'error': 'Вы уже подписаны'},
                            status=status.HTTP_400_BAD_REQUEST)

        if request.user == author:
            return Response({'error': 'Невозможно подписаться на себя'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = SubscribeSerializer(
            author,
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        Subscribe.objects.create(user=request.user, author=author)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        author = get_object_or_404(User, id=id)
        if not Subscribe.objects.filter(user=request.user,
                                        author=author):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        get_object_or_404(Subscribe, user=request.user,
                          author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=request.user)
        serializer = SubscribeSerializer(
            self.paginate_queryset(queryset),
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(ReadOnlyModelViewSet):
    """
    Вьюсет для работы с ингридиентами
    (редактирование - админ,
    использование - авторизированные пользователи).
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ('^name',)


class TagViewSet(ReadOnlyModelViewSet):
    """
    Вьюсет для работы с тэгами для рецептов
    (редактирование - админ,
    использование - авторизированные пользователи).
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    """
    Вьюсет для работы с основными возможностями проекта
    (создание, удаление и редактирование рецептов - админ и автор;
    добавление в избранное рецептов, а так же скачивание ингридиентов
    для приготовления рецептов - авторизированный пользователь;
    просмотр рецептов - для всех).
    """
    queryset = Recipe.objects.all()
    permission_classes = [IsAdminAuthorOrReadOnly]
    pagination_class = ProjectPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    http_method_names = ['get', 'post', 'patch', 'create', 'delete']

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ReadRecipeSerializer
        return RecordRecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = False
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, **kwargs):
        recipe = Recipe.objects.filter(id=kwargs['pk']).first()

        if not recipe:
            raise serializers.ValidationError('Рецепт не существует!')

        serializer = FavoriteSerializer(
            data={'user': request.user.id,
                  'recipe': recipe.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            SmallRecipeSerializer(recipe).data,
            status=status.HTTP_201_CREATED,
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, **kwargs):
        favorite = FavouriteRecipe.objects.filter(
            user=request.user,
            recipe=self.get_object()
        )

        if not favorite:
            raise serializers.ValidationError(
                'Рецепт не добавлен в избранное!'
            )

        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated],
            pagination_class=None)
    def shopping_cart(self, request, **kwargs):
        recipe = Recipe.objects.filter(id=kwargs['pk']).first()

        if recipe:
            serializer = SmallRecipeSerializer(
                recipe,
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)

            if not ShoppingCart.objects.filter(user=request.user,
                                               recipe=recipe,).exists():
                ShoppingCart.objects.create(user=request.user,
                                            recipe=recipe)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, **kwargs):
        recipe = self.get_object()
        shopping_cart = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe,
        ).first()

        if not shopping_cart:
            raise serializers.ValidationError(
                'Рецепт не добавлен в список покупок!'
            )

        shopping_cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],)
    def download_shopping_cart(self, request, **kwargs):
        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
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
