# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0004_report'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='category',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
    ]
