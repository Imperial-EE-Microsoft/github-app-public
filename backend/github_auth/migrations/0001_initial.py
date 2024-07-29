# Generated by Django 4.2.13 on 2024-06-17 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GitHubToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "github_id",
                    models.CharField(
                        default="default_github_id", max_length=255, unique=True
                    ),
                ),
                ("access_token", models.CharField(max_length=255)),
                ("refresh_token", models.CharField(default="-1", max_length=255)),
            ],
        ),
    ]
