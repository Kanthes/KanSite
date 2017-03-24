# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0008_auto_20170310_1327'),
    ]

    operations = [
        migrations.CreateModel(
            name='Spambot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('messages', models.ManyToManyField(to='records.Message')),
                ('pattern', models.ForeignKey(to='records.SpamPattern')),
                ('reports', models.ManyToManyField(to='records.Report')),
                ('user', models.ForeignKey(to='records.User')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='spampattern',
            name='messages',
        ),
        migrations.RemoveField(
            model_name='spampattern',
            name='reports',
        ),
        migrations.RemoveField(
            model_name='spampattern',
            name='users',
        ),
        migrations.AddField(
            model_name='report',
            name='ip_ban',
            field=models.NullBooleanField(default=None),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='report',
            name='permanent_ban',
            field=models.NullBooleanField(default=None),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='report',
            name='tos_ban',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
