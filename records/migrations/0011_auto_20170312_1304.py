# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0010_auto_20170312_1032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spampattern',
            name='alt_text_pattern',
            field=models.CharField(default=b'', max_length=5000, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='spampattern',
            name='initial_text_pattern',
            field=models.CharField(default=b'', max_length=5000, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='spampattern',
            name='link_patterns',
            field=models.CharField(default=b'', max_length=5000, blank=True),
            preserve_default=True,
        ),
    ]
