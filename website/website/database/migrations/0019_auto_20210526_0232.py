# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2021-05-26 02:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0018_auto_20210521_2220'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='created_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='pullrequest',
            name='created_at',
            field=models.DateTimeField(null=True),
        ),
    ]
