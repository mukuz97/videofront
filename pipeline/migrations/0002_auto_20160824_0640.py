# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-08-24 06:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='VideoSubtitles',
            new_name='Subtitles',
        ),
    ]
