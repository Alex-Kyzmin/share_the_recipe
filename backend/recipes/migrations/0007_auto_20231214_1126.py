# Generated by Django 3.2.15 on 2023-12-14 08:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_auto_20231214_1011'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='favouriterecipe',
            options={'verbose_name': 'Избранное', 'verbose_name_plural': 'Избранное'},
        ),
        migrations.AlterModelOptions(
            name='ingredientinrecipe',
            options={'verbose_name': 'Ингредиент в рецепте', 'verbose_name_plural': 'Ингредиенты в рецептах'},
        ),
        migrations.AlterModelOptions(
            name='shoppingcart',
            options={'ordering': ('-id',), 'verbose_name': 'Корзина покупок', 'verbose_name_plural': 'Корзина покупок'},
        ),
    ]
