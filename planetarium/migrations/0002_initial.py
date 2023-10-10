# Generated by Django 4.2.6 on 2023-10-10 23:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('planetarium', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='astronomyshow',
            name='show_theme',
            field=models.ManyToManyField(blank=True, to='planetarium.showtheme'),
        ),
        migrations.AlterUniqueTogether(
            name='ticket',
            unique_together={('show_session', 'row', 'seat')},
        ),
    ]
