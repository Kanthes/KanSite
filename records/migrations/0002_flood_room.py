# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='flood',
            name='room',
            field=models.CharField(default='', max_length=40),
            preserve_default=False,
        ),
    ]
