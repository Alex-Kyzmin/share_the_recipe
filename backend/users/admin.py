from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import TokenProxy

# настройка админ-зоны для импортируемых моделей
from users.models import ProjectUser, Subscribe


@admin.register(ProjectUser)
class UserAdmin(UserAdmin):
    list_display = (
        'username',
        'id',
        'email',
        'first_name',
        'last_name',
        'password',
    )
    list_filter = ('email', 'username',)
    search_fields = ('email', 'username',)


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author',)
    list_filter = ('user', 'author',)
    search_fields = ('user', 'author',)


admin.site.unregister(Group)
admin.site.unregister(TokenProxy)
