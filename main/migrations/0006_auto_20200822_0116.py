# Generated by Django 2.2.15 on 2020-08-22 01:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_auto_20200822_0053"),
    ]

    operations = [
        migrations.AlterField(
            model_name="track",
            name="apple_music_id",
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="track",
            name="spotify_id",
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
    ]
