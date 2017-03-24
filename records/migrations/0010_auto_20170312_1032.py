# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0009_auto_20170312_1027'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='regexspambot',
            name='messages',
        ),
        migrations.RemoveField(
            model_name='regexspambot',
            name='user',
        ),
        migrations.DeleteModel(
            name='RegexSpambot',
        ),
        migrations.AddField(
            model_name='spambot',
            name='timestamp',
            field=models.DateTimeField(default=datetime.datetime(2017, 3, 12, 10, 32, 50, 798768)),
            preserve_default=False,
        ),
    ]
