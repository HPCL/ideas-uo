# Generated by Django 3.0.4 on 2020-12-23 03:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0009_auto_20201223_0323'),
    ]

    operations = [
        migrations.AddField(
            model_name='commit',
            name='hash',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
    ]