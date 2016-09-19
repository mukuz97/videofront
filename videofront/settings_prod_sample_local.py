import sys
from .settings import * # pylint: disable=unused-wildcard-import

if len(sys.argv) > 1 and sys.argv[1] == 'test':
    sys.stderr.write("You are running tests with production settings. I'm pretty sure you don't want to do that.\n")
    sys.exit(1)

SECRET_KEY = 'putsomerandomtextherehere' # FIXME
DEBUG = False
ALLOWED_HOSTS = ['example.com'] # FIXME

CELERY_ALWAYS_EAGER = False

INSTALLED_APPS += ['contrib.plugins.local']
PLUGIN_BACKEND = "contrib.plugins.local.backend.Backend"
BACKEND_URLS = 'contrib.plugins.local.urls'
# Root url from which static assets (videos, subs, thumbs) will be served.
# Assets will be served from the '/backend/storage' relative url. If you
# override this setting, make sure your web server is configured accordingly.
# I.e: 'http://static.yourdomain.com/backend/storage/' should load static files
# from VIDEO_STORAGE_ROOT.
# ASSETS_ROOT_URL = 'http://static.yourdomain.com'

# The absolute path to the directory where video assets will be stored
VIDEO_STORAGE_ROOT = '/opt/videofront/storage/' # FIXME

# Override this settings if ffmpeg is not in your path.
# Replace by 'avconv' on Ubuntu 14.04.
# FFMPEG_BINARY = 'ffmpeg'

# Presets suggestions:
# https://support.google.com/youtube/answer/1722171
# https://support.google.com/youtube/answer/6375112
FFMPEG_PRESETS = {
    'HD': {
        'size': '1280x720',
        'video_bitrate': '5120k',
        'audio_bitrate': '384k',
    },
    'SD': {
        'size': '854x480',
        'video_bitrate': '2560k',
        'audio_bitrate': '4096k',
    },
    'LD': {
        'size': '640x360',
        'video_bitrate': '1024k',
        'audio_bitrate': '426x240',
    },
}
