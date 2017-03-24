# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0007_auto_20170309_1516'),
    ]

    operations = [
        migrations.AddField(
            model_name='spampattern',
            name='messages',
            field=models.ManyToManyField(to='records.Message'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='spampattern',
            name='name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='spampattern',
            name='reports',
            field=models.ManyToManyField(to='records.Report'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='spampattern',
            name='users',
            field=models.ManyToManyField(to='records.User'),
            preserve_default=True,
        ),
    ]
