# flake8: noqa
import os
from pathlib import Path

from dotenv import load_dotenv
from environs import Env

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
env = Env()
env.read_env

SECRET_KEY = os.getenv('SECRET_KEY', "default_key")

#DEBUG = env.bool('DEBUG_VALUE', False)
DEBUG = True

ALLOWED_HOSTS = [os.getenv('IP_HOST'), os.getenv('DOMAIN_HOST'), '127.0.0.1', 'localhost',]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Подключаем модули к проекту.
    'rest_framework', # фреймворк DRF.
    'rest_framework.authtoken', # модуль authtoken фреймворка DRF.
    'djoser', # библиотека djoser.
    # Подключаем приложение к проекту.
    'users.apps.UsersConfig', # приложение отвечеющее за пользователей проекта.
    'recipes.apps.RecipesConfig', # приложение проекта рецепты.
    'api.apps.ApiConfig', # приложение по взаимодействию программ.
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'foodgram.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'foodgram.wsgi.application'


# подключаем к проекту PostgreSQL
DATABASES = {
    #'default': {
        #'ENGINE': 'django.db.backends.postgresql',
        #'NAME': os.getenv('POSTGRES_DB', 'django'),
        #'USER': os.getenv('POSTGRES_USER', 'django'),
        #'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        #'HOST': os.getenv('DB_HOST', ''),
        #'PORT': os.getenv('DB_PORT', 5432)
    #}
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Указываем ссылку на модель "пользователя" проекта в константе.
AUTH_USER_MODEL = 'users.ProjectUser'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    # переопределяем дефолтный класс разрешения к path проекта
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}

DJOSER = {
    # переопределяем дефолтное поля авторизации для входа на сайт
    "LOGIN_FIELD": "email",
    'HIDE_USERS': False,
    # переопределяем дефолтные сериализаторы поля различных запросов к пользователям
    'SERIALIZERS': {
        'user_create': 'api.serializers.ProjectUserCreateSerializer',
        'user': 'api.serializers.ProjectUserSerializer',
        'current_user': 'api.serializers.ProjectUserSerializer',
    },

    'PERMISSIONS': {
        # переопределяем дефолтный класс разрешений к некоторым 
        # path проекта для вью - CustomUserViewSet
        'user': ['rest_framework.permissions.AllowAny'],
        'user_list': ['rest_framework.permissions.AllowAny'],
    },
}

# Обозначаем язык проекта.
LANGUAGE_CODE = 'ru-RU'

# Обозначаем временной пояс.
TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = '/static/'
# Обозначаем путь к статичным файлам проекта.
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

MEDIA_URL = '/media/'
# Обозначаем путь к медиа файлам проекта.
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Числовые константы проекта.
MAX_LENGTH_EMAIL = 254
MAX_LENGTH_USER_MODEL = 150
MAX_LENGTH_RECIPE_MODEL = 200
MAX_LENGTH_COLOR = 7
MIN_INGRREDIENT_VALUE = 1
MAX_INGRREDIENT_VALUE = 10*2
INLAIN_MIN = 1
INLAIN_MAX = 15
MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32000
