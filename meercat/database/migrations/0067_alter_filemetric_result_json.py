# Generated by Django 4.0.7 on 2023-01-23 22:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0066_alter_filemetric_branch_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filemetric',
            name='result_json',
            field=models.JSONField(blank=True, null=True),
        ),
    ]