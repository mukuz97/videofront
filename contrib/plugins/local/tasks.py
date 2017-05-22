import subprocess

from celery import shared_task

from . import utils


@shared_task(name='ffmpeg_transcode_video')
def ffmpeg_transcode_video(src_path, dst_path, ffmpeg_presets):
    # E.g:
    # ffmpeg -y -i src.mp4 -c:v libx264 -c:a aac -strict experimental \
    #   -r 30 -s 1280x720 -vb 5120k -ab 384k -ar 48000 dst.mp4
    command = [
        utils.ffmpeg_binary(),
        '-y',# overwrite without asking
        '-loglevel', 'error',
        '-i', src_path,# input path
        '-c:v', 'libx264',# video codec
        '-c:a', 'aac',# audio codec
        '-strict', 'experimental',# allow experimental 'aac' codec
        '-r', ffmpeg_presets.get('framerate', '30'),
        '-s', ffmpeg_presets['size'],# 16:9 video size
        '-vb', ffmpeg_presets['video_bitrate'],
        '-ab', ffmpeg_presets['audio_bitrate'],
        '-ar', ffmpeg_presets.get('audio_rate', '48000'),# audio sampling rate
        dst_path,
    ]
    subprocess.call(command)

@shared_task(name='ffmpeg_create_thumbnail')
def ffmpeg_create_thumbnail(src_path, dst_path):
    command = [
        utils.ffmpeg_binary(),
        '-y',# overwrite without asking
        '-loglevel', 'error',
        '-i', src_path,# input path
        '-ss', '00:00:00.000',
        '-vframes', '1',
        dst_path,
    ]
    subprocess.call(command)
