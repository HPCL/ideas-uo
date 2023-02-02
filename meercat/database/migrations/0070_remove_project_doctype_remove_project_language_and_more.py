# Generated by Django 4.0.7 on 2023-02-02 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0069_project_complete_ignore_filenames_project_doctype_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='doctype',
        ),
        migrations.RemoveField(
            model_name='project',
            name='language',
        ),
        migrations.AddField(
            model_name='project',
            name='doctypes',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]