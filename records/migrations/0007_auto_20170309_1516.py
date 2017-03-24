# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0006_spampattern'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spampattern',
            name='alt_text_pattern',
            field=models.CharField(default=b'', max_length=5000),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='spampattern',
            name='initial_text_pattern',
            field=models.CharField(default=b'', max_length=5000),
            preserve_default=True,
        ),
    ]
