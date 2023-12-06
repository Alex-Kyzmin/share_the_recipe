from django.contrib.auth.models import AbstractUser
from django.db import models


class ProjectUser(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Твой никнэйм",
        error_messages={
            "unique": "Пользователь с таким никнэймом уже зарегистрирован"
        },
    )
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Твоя электронная почта',
        error_messages={
            "unique": "Пользователь с таким email уже зарегистрирован"
        },
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Твое имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Твоя фамилия'
    )
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = [
        'first_name',
        'last_name',
        'email',
    ]
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"], name="unique_username_email"
            )
        ]

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    user = models.ForeignKey(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name='subscriber',
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name='subscribing',
        verbose_name="Автор",
    )

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique_subscription'
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
    
    def __str__(self):
        return f"Подписчик {self.user} - автор {self.author}"
