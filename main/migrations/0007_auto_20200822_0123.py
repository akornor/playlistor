# Generated by Django 2.2.15 on 2020-08-22 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_auto_20200822_0116"),
    ]

    operations = [
        migrations.AlterField(
            model_name="track",
            name="artist",
            field=models.CharField(db_index=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="track",
            name="featuring",
            field=models.CharField(db_index=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="track",
            name="name",
            field=models.CharField(db_index=True, max_length=255, null=True),
        ),
    ]
