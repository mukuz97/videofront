from django.conf import settings

def ffmpeg_binary():
    return getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')
