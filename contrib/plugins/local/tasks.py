import subprocess
import time
import os

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

@shared_task(name='ffmpeg_create_poster_frames')
def ffmpeg_create_poster_frames(src_path, dst_path, pf_file):
    command = [
        utils.ffmpeg_binary(),
        '-y',# overwrite without asking
        '-loglevel', 'error',
        '-i', src_path,# input path
        '-vf', 'fps=1/10',# make thumbs every 10 seconds
        '-q:v', '2',#Set quality of thumbs(lower is better)
        dst_path + '_%d.jpg',
    ]
    subprocess.call(command)

    #Calculate video duration
    command = 'ffprobe -i {} -show_entries format=duration -v quiet -of csv="p=0"'.format(src_path)
    output = subprocess.check_output(
        command,
        shell=True, # Let this run in the shell
        stderr=subprocess.STDOUT
    )
    duration = float(output)
    thumb_count = int(duration / 10)
    if duration > thumb_count * 10:
        thumb_count += 1

    # resize thumbs
    for i in range(1, thumb_count+1):
        image_path = '{}_{}.jpg'.format(dst_path, i)
        if os.path.exists(image_path):
            utils.resize_image(image_path, image_path, 160)
        else:
            thumb_count -= 1#Number of thumbs were overestimated
    
    # Create the vtt file
    f = open(dst_path, 'w')
    f.write('WEBVTT\n\n')
    for i in range(1,thumb_count):
        f.write('{}.000 --> {}.000\n'.format(
            time.strftime('%H:%M:%S', time.gmtime((i-1) * 10)),
            time.strftime('%H:%M:%S', time.gmtime(i * 10))
        ))
        f.write('{}_{}.jpg#xywh=0,0,160,90\n\n'.format(pf_file, i))
    f.write('{}.000 --> {}.000\n'.format(
        time.strftime('%H:%M:%S', time.gmtime((thumb_count - 1) * 10)),
        time.strftime('%H:%M:%S', time.gmtime(duration))
    ))
    f.write('{}_{}.jpg#xywh=0,0,160,90'.format(pf_file, thumb_count))
