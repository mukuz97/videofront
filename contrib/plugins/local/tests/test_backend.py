import importlib
from io import BytesIO
import os
import shutil
import sys
import tempfile

from django.conf import settings
from django.core.urlresolvers import reverse, clear_url_caches
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch

from contrib.plugins.local import backend as local_backend
import pipeline.tasks


VIDEO_STORAGE_ROOT = tempfile.mkdtemp()


def media_path(*args):
    return os.path.join(VIDEO_STORAGE_ROOT, 'videos', *args)


@override_settings(VIDEO_STORAGE_ROOT=VIDEO_STORAGE_ROOT, BACKEND_URLS='contrib.plugins.local.urls')
class LocalBackendTests(TestCase):

    def setUp(self):
        # Create storage folder
        if os.path.exists(VIDEO_STORAGE_ROOT):
            shutil.rmtree(VIDEO_STORAGE_ROOT)
        os.makedirs(VIDEO_STORAGE_ROOT)

        # Reload project urls to make sure backend urls are loaded
        if settings.ROOT_URLCONF in sys.modules:
            importlib.reload(sys.modules[settings.ROOT_URLCONF])
        clear_url_caches()

    def tearDown(self):
        shutil.rmtree(VIDEO_STORAGE_ROOT)

    def test_attempt_to_create_directory_outside_of_video_storage_root(self):
        backend = local_backend.Backend()

        self.assertRaises(ValueError, backend.get_file_path, "../deleteme/somefile")
        self.assertRaises(ValueError, backend.make_file_path, "../deleteme/somefile")
        self.assertFalse(os.path.exists(media_path("../deleteme/somefile")))

    def test_upload_video(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")
        file_object.name = "somevideo.mp4"

        backend.upload_video('videoid', file_object)

        dst_path = media_path('videoid', 'src', 'somevideo.mp4')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual(b"some content", open(dst_path, 'rb').read())

    def test_delete_video(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")
        file_object.name = "somevideo.mp4"

        backend.upload_video('videoid', file_object)
        backend.delete_video('videoid')

        dst_path = media_path('videoid', 'src', 'somevideo.mp4')
        self.assertFalse(os.path.exists(dst_path))

    def test_delete_video_does_not_fail_on_non_existing_video(self):
        backend = local_backend.Backend()
        backend.delete_video('videoid')

    def test_video_url(self):
        backend = local_backend.Backend()
        video_url = backend.video_url('videoid', 'HD')
        video_file_path = backend.get_video_file_path('videoid', 'HD')

        # Create video file
        os.makedirs(os.path.dirname(video_file_path))
        with open(video_file_path, 'wb') as video_file:
            video_file.write(b'video content')

        response = self.client.get(video_url)

        self.assertEqual('/backend/storage/videos/videoid/HD.mp4', video_url)
        self.assertEqual(video_file_path, os.path.join(VIDEO_STORAGE_ROOT, video_url[len('/backend/storage/'):]))
        self.assertEqual(200, response.status_code)
        self.assertEqual(b'video content', response.getvalue())

    @override_settings(ASSETS_ROOT_URL="http://example.com")
    def test_video_url_with_root_url(self):
        backend = local_backend.Backend()
        self.assertEqual("http://example.com/backend/storage/videos/videoid/HD.mp4",
                         backend.video_url("videoid", "HD"))

    def test_download_urls(self):
        url = reverse('backend:storage-video', kwargs={'video_id': 'videoid', 'format_name': 'HD'})
        self.assertIsNotNone(url)

    def test_download_video(self):
        # Create temp video file
        directory = os.path.join(VIDEO_STORAGE_ROOT, 'videos', 'videoid')
        os.makedirs(directory)
        with open(os.path.join(directory, 'HD.mp4'), 'wb') as video_file:
            video_file.write(b"some content")

        url = reverse('backend:storage-video', kwargs={'video_id': 'videoid', 'format_name': 'HD'})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        self.assertEqual(b"some content", response.getvalue())

    @override_settings(FFMPEG_PRESETS={
        'HD': {
            'size': '1280x720',
            'video_bitrate': '5120k',
            'audio_bitrate': '384k',
        },
    })
    @patch("contrib.plugins.local.tasks.ffmpeg_transcode_video")
    def test_transcode_and_download_video(self, mock_ffmpeg_transcode_video):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")
        file_object.name = "somevideo.mp4"

        # Patch transcoding function
        def ffmpeg_transcode_video(src_path, dst_path, ffmpeg_settings):
            with open(dst_path, 'wb') as f:
                f.write(b'transcoded content')
        mock_ffmpeg_transcode_video.delay = ffmpeg_transcode_video

        backend.upload_video('videoid', file_object)
        jobs = backend.start_transcoding('videoid')

        # Download source video file
        url = reverse('backend:storage-video', kwargs={'video_id': 'videoid', 'format_name': 'HD'})
        response = self.client.get(url)

        self.assertEqual(1, len(jobs))
        self.assertEqual(200, response.status_code)
        self.assertEqual(b"transcoded content", response.getvalue())

    def test_upload_subtitle(self):
        backend = local_backend.Backend()

        backend.upload_subtitle("videoid", "subid", "fr", "some content")

        dst_path = media_path('videoid', 'subs', 'subid.fr.vtt')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual("some content", open(dst_path).read())

    def test_delete_subtitle(self):
        backend = local_backend.Backend()

        backend.upload_subtitle("videoid", "subid", "fr", "some content")
        backend.delete_subtitle("videoid", "subid")

        dst_path = media_path('videoid', 'subs', 'subid.fr.vtt')
        self.assertFalse(os.path.exists(dst_path))

    @override_settings(PLUGIN_BACKEND='contrib.plugins.local.backend.Backend')
    def test_upload_subtitle_compatibility(self):
        pipeline.tasks.upload_subtitle('videoid', 'subid', 'fr', b"WEBVTT")

        dst_path = media_path('videoid', 'subs', 'subid.fr.vtt')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual("WEBVTT", open(dst_path).read())

    def test_subtitle_url(self):
        backend = local_backend.Backend()
        subtitle_url = backend.subtitle_url('videoid', 'subid', 'fr')
        subtitle_file_path = backend.get_subtitle_file_path('videoid', 'subid', 'fr')

        # Create subtitle file
        os.makedirs(os.path.dirname(subtitle_file_path))
        with open(subtitle_file_path, 'w') as sub_file:
            sub_file.write('subtitle content')

        response = self.client.get(subtitle_url)

        self.assertEqual('/backend/storage/videos/videoid/subs/subid.fr.vtt', subtitle_url)
        self.assertEqual(subtitle_file_path, os.path.join(VIDEO_STORAGE_ROOT, subtitle_url[len('/backend/storage/'):]))
        self.assertEqual(200, response.status_code)
        self.assertEqual(b'subtitle content', response.getvalue())

    @override_settings(ASSETS_ROOT_URL="http://example.com")
    def test_subtitle_url_with_root_url(self):
        backend = local_backend.Backend()
        self.assertEqual('http://example.com/backend/storage/videos/videoid/subs/subid.fr.vtt',
                         backend.subtitle_url('videoid', 'subid', 'fr'))

    @override_settings(FFMPEG_THUMBNAILS_PRESET='HD', FFMPEG_PRESETS={'HD': {}})
    def test_create_thumbnail(self):
        # Patch thumbnail creation function
        def ffmpeg_create_thumbnail(src_path, dst_path):
            with open(dst_path, 'wb') as f:
                f.write(b'thumbnail content')

        backend = local_backend.Backend()
        with patch('contrib.plugins.local.tasks.ffmpeg_create_thumbnail', ffmpeg_create_thumbnail):
            backend.create_thumbnail("videoid", "thumbid")

        thumbnail_path = backend.get_file_path("videoid", backend.THUMBNAILS_DIRNAME, "thumbid.jpg")
        self.assertTrue(os.path.exists(thumbnail_path))
        with open(thumbnail_path, 'rb') as thumbnail_file:
            self.assertEqual(b'thumbnail content', thumbnail_file.read())

    def test_upload_thumbnail(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")

        backend.upload_thumbnail("videoid", "thumbid", file_object)

        dst_path = media_path('videoid', 'thumbs', 'thumbid.jpg')
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual(b"some content", open(dst_path, 'rb').read())

    def test_delete_thumbnail(self):
        backend = local_backend.Backend()
        file_object = BytesIO(b"some content")

        backend.upload_thumbnail("videoid", "thumbid", file_object)
        backend.delete_thumbnail("videoid", "thumbid")

        dst_path = media_path('videoid', 'thumbs', 'thumbid.jpg')
        self.assertFalse(os.path.exists(dst_path))

    def test_thumbnail_url(self):
        backend = local_backend.Backend()
        thumbnail_url = backend.thumbnail_url('videoid', 'thumbid')
        thumbnail_file_path = backend.get_thumbnail_file_path('videoid', 'thumbid')

        # Create thumbnail file
        os.makedirs(os.path.dirname(thumbnail_file_path))
        with open(thumbnail_file_path, 'wb') as thumb_file:
            thumb_file.write(b'thumbnail content')

        response = self.client.get(thumbnail_url)

        self.assertEqual('/backend/storage/videos/videoid/thumbs/thumbid.jpg', thumbnail_url)
        self.assertEqual(thumbnail_file_path,
                         os.path.join(VIDEO_STORAGE_ROOT, thumbnail_url[len('/backend/storage/'):]))
        self.assertEqual(200, response.status_code)
        self.assertEqual(b'thumbnail content', response.getvalue())

    @override_settings(ASSETS_ROOT_URL="http://example.com")
    def test_thumbnail_url_with_root_url(self):
        backend = local_backend.Backend()
        self.assertEqual('http://example.com/backend/storage/videos/videoid/thumbs/thumbid.jpg',
                         backend.thumbnail_url('videoid', 'thumbid'))

    @override_settings(FFMPEG_PRESETS={
        'HD': {
            'video_bitrate': '5120k',
            'audio_bitrate': '384k',
        },
        'LD': {
            'video_bitrate': '64',
            'audio_bitrate': '1',
        },
        'SD': {
            'video_bitrate': '128k',
            'audio_bitrate': '2',
        },
    })
    def test_iter_formats(self):
        backend = local_backend.Backend()

        # Create HD and SD definitions, but not LD
        with open(backend.make_file_path('videoid', 'HD.mp4'), 'wb') as f:
            f.write(b'HD content')
        with open(backend.make_file_path('videoid', 'SD.mp4'), 'wb') as f:
            f.write(b'SD content')

        formats = sorted(list(backend.iter_formats('videoid')))
        self.assertEqual(2, len(formats))
        self.assertEqual('HD', formats[0][0])
        self.assertEqual(5120*1024 + 384*1024, formats[0][1])
        self.assertEqual('SD', formats[1][0])
        self.assertEqual(128*1024 + 2, formats[1][1])
