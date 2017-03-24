# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0003_regexspambot'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(max_length=40, choices=[(b'crtd', b'Created'), (b'sent', b'Sent')])),
                ('from_username', models.CharField(max_length=40)),
                ('target_username', models.CharField(max_length=40)),
                ('target_id', models.IntegerField()),
                ('description', models.CharField(max_length=5000)),
                ('created_timestamp', models.DateTimeField()),
                ('updated_timestamp', models.DateTimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
