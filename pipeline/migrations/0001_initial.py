# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-08-04 09:46
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('public_id', models.CharField(max_length=20, unique=True, validators=[django.core.validators.MinLengthValidator(1)], verbose_name='Public video ID')),
            ],
        ),
        migrations.CreateModel(
            name='VideoTranscoding',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now=True, verbose_name='Time of transcoding job start')),
                ('progress', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Progress percentage')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('failed', 'Failed'), ('success', 'Success')], max_length=32, verbose_name='Status')),
                ('video', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='transcoding', to='pipeline.Video')),
            ],
        ),
        migrations.CreateModel(
            name='VideoUploadUrl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expires_at', models.IntegerField(db_index=True, verbose_name='Timestamp at which the url expires')),
                ('public_video_id', models.CharField(max_length=20, unique=True, validators=[django.core.validators.MinLengthValidator(1)], verbose_name='Public video ID')),
                ('was_used', models.BooleanField(db_index=True, default=False, verbose_name='Was the upload url used')),
                ('last_checked', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Last time it was checked if the url was used')),
            ],
        ),
    ]