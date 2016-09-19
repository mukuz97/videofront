from glob import glob
import os
import shutil
import urllib.parse

from django.core.urlresolvers import reverse
from django.conf import settings

from pipeline.backend import BaseBackend
import pipeline.exceptions
from . import tasks


class Backend(BaseBackend):

    THUMBNAILS_DIRNAME = "thumbs"
    SUBTITLES_DIRNAME = "subs"

    @staticmethod
    def make_file_path(*args):
        """
        Same as get_file_path. Create the file directory if it does not exist.
        """
        path = Backend.get_file_path(*args)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        return path

    @staticmethod
    def get_video_file_path(video_id, video_format):
        return Backend.get_file_path(video_id, Backend.get_video_file_name(video_format))

    @staticmethod
    def get_video_file_name(video_format):
        return "{}.mp4".format(video_format)

    @staticmethod
    def get_subtitle_file_path(video_id, subtitle_id, language_code):
        file_name = Backend.get_subtitle_file_name(subtitle_id, language_code)
        return Backend.get_file_path(video_id, Backend.SUBTITLES_DIRNAME, file_name)

    @staticmethod
    def get_subtitle_file_name(subtitle_id, language_code):
        return "{}.{}.vtt".format(subtitle_id, language_code)

    @staticmethod
    def get_thumbnail_file_path(video_id, thumb_id):
        file_name = Backend.get_thumbnail_file_name(thumb_id)
        return Backend.get_file_path(video_id, Backend.THUMBNAILS_DIRNAME, file_name)

    @staticmethod
    def get_thumbnail_file_name(thumb_id):
        return "{}.jpg".format(thumb_id)

    @staticmethod
    def get_file_path(*args):
        """
        Get an absolute file path inside the VIDEO_STORAGE_ROOT directory.

        Args:
            *args (str): directory and file names
            create_dir (bool): if true, make sure the file directory exists
        """
        root_dir = os.path.abspath(os.path.join(settings.VIDEO_STORAGE_ROOT, 'videos'))
        path = os.path.abspath(os.path.join(root_dir, *args))

        # we check that the path is inside the VIDEO_STORAGE_ROOT/videos directory
        if not path.startswith(os.path.abspath(root_dir)):
            raise ValueError("Cannot create path {} outside of {}".format(
                path, settings.VIDEO_STORAGE_ROOT
            ))
        return path

    def _rm(self, *args):
        """
        Recursively delete a directory or file inside the video storage root.
        """
        path = self.get_file_path(*args)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


    ####################
    # Overridden methods
    ####################

    def upload_video(self, video_id, file_object):
        video_filename = os.path.basename(file_object.name)
        video_path = self.make_file_path(video_id, 'src', video_filename)
        copy_content(file_object, video_path)

    def delete_video(self, video_id):
        self._rm(video_id)

    def video_url(self, video_id, format_name):
        return urllib.parse.urljoin(
            getattr(settings, 'ASSETS_ROOT_URL', ''),
            reverse("backend:storage-video", kwargs={'video_id': video_id, 'format_name': format_name})
        )

    def upload_subtitle(self, video_id, subtitle_id, language_code, content):
        subtitle_path = self.make_file_path(
            video_id, self.SUBTITLES_DIRNAME,
            self.get_subtitle_file_name(subtitle_id, language_code)
        )
        with open(subtitle_path, "w") as out_f:
            out_f.write(content)

    def delete_subtitle(self, video_id, subtitle_id):
        subtitle_paths = self.get_subtitle_file_path(video_id, subtitle_id, '*')
        for path in glob(subtitle_paths):
            os.remove(path)

    def subtitle_url(self, video_id, subtitle_id, language_code):
        return urllib.parse.urljoin(
            getattr(settings, 'ASSETS_ROOT_URL', ''),
            reverse("backend:storage-subtitle", kwargs={
                'video_id': 'videoid',
                'subtitle_id': subtitle_id,
                'language_code': language_code
            })
        )

    def upload_thumbnail(self, video_id, thumb_id, file_object):
        thumb_filename = self.get_thumbnail_file_name(thumb_id)
        thumb_path = self.make_file_path(video_id, self.THUMBNAILS_DIRNAME, thumb_filename)
        copy_content(file_object, thumb_path)

    def delete_thumbnail(self, video_id, thumb_id):
        self._rm(video_id, self.THUMBNAILS_DIRNAME, self.get_thumbnail_file_name(thumb_id))

    def start_transcoding(self, video_id):
        # Note that this will trigger a KeyError if the file does not exist
        src_path = glob(self.get_file_path(video_id, "src", "*"))[0]
        jobs = []
        for format_name, ffmpeg_settings in settings.FFMPEG_PRESETS.items():
            dst_path = self.get_video_file_path(video_id, format_name)
            async_result = tasks.ffmpeg_transcode_video.delay(src_path, dst_path, ffmpeg_settings)
            jobs.append(async_result)
        return jobs

    def check_progress(self, job):
        """
        Here, the job is in fact a celery AsyncResult.
        """
        if job.failed():
            raise pipeline.exceptions.TranscodingFailed(job.result)

        progress = 100 if job.successful() else 0
        return progress, job.successful()

    def iter_formats(self, video_id):
        for format_name, ffmpeg_settings in settings.FFMPEG_PRESETS.items():
            if os.path.exists(self.get_video_file_path(video_id, format_name)):
                bitrate = bitrate_value(ffmpeg_settings['video_bitrate'])
                bitrate += bitrate_value(ffmpeg_settings['audio_bitrate'])
                yield format_name, bitrate

    def create_thumbnail(self, video_id, thumb_id):
        video_file_path = self.get_video_file_path(video_id, settings.FFMPEG_THUMBNAILS_PRESET)
        thumbnail_file_path = self.make_file_path(
            video_id,
            self.THUMBNAILS_DIRNAME,
            self.get_thumbnail_file_name(thumb_id)
        )
        tasks.ffmpeg_create_thumbnail(video_file_path, thumbnail_file_path)

    def thumbnail_url(self, video_id, thumb_id):
        return urllib.parse.urljoin(
            getattr(settings, 'ASSETS_ROOT_URL', ''),
            reverse("backend:storage-thumbnail", kwargs={
                'video_id': 'videoid',
                'thumbnail_id': thumb_id
            })
        )


def copy_content(file_object, path):
    """
    Copy content of file object to binary file. Write is performed chunk by
    chunk.
    """
    file_object.seek(0)
    with open(path, 'wb') as out_f:
        while True:
            chunk = file_object.read(1024)
            if not chunk:
                break
            out_f.write(chunk)

def bitrate_value(str_bitrate):
    """
    Convert a bitrate string to integer.
    """
    if 'k' in str_bitrate:
        return int(str_bitrate.replace("k", "")) * 1024
    return int(str_bitrate)
