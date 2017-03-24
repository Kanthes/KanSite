# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0011_auto_20170312_1304'),
    ]

    operations = [
        migrations.AddField(
            model_name='spampattern',
            name='enabled',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
