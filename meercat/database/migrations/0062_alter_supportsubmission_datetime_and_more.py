# Generated by Django 4.0.7 on 2022-10-05 18:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0061_remove_supportsubmission_relatedurl_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supportsubmission',
            name='datetime',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='supportsubmission',
            name='feature',
            field=models.CharField(choices=[('GENERAL', 'General issue or feedback'), ('LOGIN', 'Logging in to MeerCAT'), ('LOGOUT', 'Logging out of MeerCAT'), ('PRA', 'Pull request assitant'), ('HOME', 'Home page'), ('SUPPORT', 'Support page')], max_length=64, verbose_name='Site feature'),
        ),
    ]