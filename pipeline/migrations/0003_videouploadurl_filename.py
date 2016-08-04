# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-08-04 16:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0002_videotranscoding_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='videouploadurl',
            name='filename',
            field=models.CharField(default='video.mp4', max_length=128, verbose_name='Uploaded file name'),
            preserve_default=False,
        ),
    ]