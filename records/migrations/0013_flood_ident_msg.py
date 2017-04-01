# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0012_spampattern_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='flood',
            name='ident_msg',
            field=models.NullBooleanField(default=None),
            preserve_default=True,
        ),
    ]
