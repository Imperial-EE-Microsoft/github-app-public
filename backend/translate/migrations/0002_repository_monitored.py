# Generated by Django 4.2.13 on 2024-06-19 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translate", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="repository",
            name="monitored",
            field=models.BooleanField(default=False),
        ),
    ]
