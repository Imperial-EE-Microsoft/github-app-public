# Generated by Django 4.2.13 on 2024-06-25 00:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translate", "0003_alter_repository_id"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="lastcommit",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="lastcommit",
            name="repo",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="translate.repository"
            ),
        ),
    ]
