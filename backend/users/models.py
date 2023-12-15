from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from foodgram.settings import MAX_LENGTH_EMAIL, MAX_LENGTH_USER_MODEL


class ProjectUser(AbstractUser):
    """Модель для данных - пользователь."""
    username = models.CharField(
        max_length=MAX_LENGTH_USER_MODEL,
        unique=True,
        verbose_name="Твой никнэйм",
        error_messages={
            "unique": "Пользователь с таким никнэймом уже зарегистрирован"
        },
    )
    email = models.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        unique=True,
        verbose_name='Твоя электронная почта',
        error_messages={
            "unique": "Пользователь с таким email уже зарегистрирован"
        },
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH_USER_MODEL,
        verbose_name='Твое имя'
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_USER_MODEL,
        verbose_name='Твоя фамилия'
    )
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = [
        'first_name',
        'last_name',
        'email',
    ]

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"],
                name="unique_username_email",
            )
        ]

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    """Модель для данных - подписка на автора."""
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
        ordering = ['author_id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription',
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Невозможно подписаться на себя')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'Подписчик {self.user} - автор {self.author}'
