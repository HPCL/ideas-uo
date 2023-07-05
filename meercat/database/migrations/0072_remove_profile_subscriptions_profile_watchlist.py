# Generated by Django 4.1.7 on 2023-05-12 04:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0071_alter_filemetric_metric_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="subscriptions",
        ),
        migrations.AddField(
            model_name="profile",
            name="watchlist",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
