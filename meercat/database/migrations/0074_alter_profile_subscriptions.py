# Generated by Django 4.1.7 on 2023-05-18 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0073_remove_profile_watchlist_profile_subscriptions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="subscriptions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]