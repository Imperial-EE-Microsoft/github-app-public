# Generated by Django 4.2.13 on 2024-06-25 00:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translate", "0002_repository_monitored"),
    ]

    operations = [
        migrations.AlterField(
            model_name="repository",
            name="id",
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
