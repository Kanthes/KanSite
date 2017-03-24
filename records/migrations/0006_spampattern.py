# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0005_report_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpamPattern',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('initial_text_pattern', models.CharField(default=None, max_length=5000)),
                ('alt_text_pattern', models.CharField(default=None, max_length=5000)),
                ('link_patterns', models.CharField(default=b'{}', max_length=5000)),
                ('young_limit', models.IntegerField(default=5)),
                ('old_limit', models.IntegerField(default=10)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
