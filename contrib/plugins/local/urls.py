from django.conf.urls import url

from . import views

from . import backend

urlpatterns = [
    # Note that these urls should be served by the webserver (ex: nginx) for efficiency reasons.
    url(r'^storage/videos/(?P<video_id>.+)/(?P<format_name>.+)\.mp4$', views.storage_video, name='storage-video'),
    url(
        r'^storage/videos/(?P<video_id>.+)/{}/(?P<subtitle_id>.+)\.(?P<language_code>.+)\.vtt$'.format(
            backend.Backend.SUBTITLES_DIRNAME
        ),
        views.storage_subtitle,
        name='storage-subtitle'
    ),
    url(
        r'^storage/videos/(?P<video_id>.+)/{}/(?P<thumbnail_id>.+)\.jpg$'.format(backend.Backend.THUMBNAILS_DIRNAME),
        views.storage_thumbnail,
        name='storage-thumbnail'
    ),
]
