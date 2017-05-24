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

# Origins from which static assets (videos, subtitles) may be downloaded. By
# default, videos may be embedded in all websites. This value will be used to
# define the Access-Control-Allow-Origin header (see
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS)
# ALLOWED_ORIGIN = '*'

# The absolute path to the directory where video assets will be stored
VIDEO_STORAGE_ROOT = '/opt/videofront/storage/' # FIXME

# Override this settings if ffmpeg is not in your path.
# Replace by 'avconv' on Ubuntu 14.04.
# FFMPEG_BINARY = 'ffmpeg'

# Presets suggestions:
# https://support.google.com/youtube/answer/1722171
# https://support.google.com/youtube/answer/6375112
FFMPEG_PRESETS = {
    'HD': { # 720p
        'size': '1280x720',
        'video_bitrate': '2200k',
        'audio_bitrate': '128k',
    },
    'SD': { # 480p
        'size': '854x480',
        'video_bitrate': '1136k',
        'audio_bitrate': '64k',
    },
    'LD': { # 360p
        'size': '640x360',
        'video_bitrate': '896k',
        'audio_bitrate': '64k',
    },
}

# Name of the FFMPEG_PRESETS preset that will be used to generate a thumbnail.
# Note that the thumbnail will automatically be resized, so you should pick the
# preset with the best video size.
FFMPEG_THUMBNAILS_PRESET = 'HD'
