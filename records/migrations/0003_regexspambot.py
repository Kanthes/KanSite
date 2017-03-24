# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0002_flood_room'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegexSpambot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pattern', models.CharField(max_length=5000)),
                ('timestamp', models.DateTimeField()),
                ('messages', models.ManyToManyField(to='records.Message')),
                ('user', models.ForeignKey(to='records.User')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
