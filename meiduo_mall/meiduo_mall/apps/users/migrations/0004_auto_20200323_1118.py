# Generated by Django 3.0.4 on 2020-03-23 11:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('areas', '0001_initial'),
        ('users', '0003_auto_20200323_0745'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='city',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='city_addresses', to='areas.Area', verbose_name='市'),
        ),
        migrations.AlterField(
            model_name='address',
            name='district',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='district_addresses', to='areas.Area', verbose_name='区'),
        ),
        migrations.AlterField(
            model_name='address',
            name='province',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='province_addresses', to='areas.Area', verbose_name='省'),
        ),
        migrations.AlterField(
            model_name='address',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to=settings.AUTH_USER_MODEL, verbose_name='用户'),
        ),
    ]
