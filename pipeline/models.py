from django.conf.global_settings import LANGUAGES
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now

from . import backend
from . import cache
from . import managers
from . import utils


class Video(models.Model):
    title = models.CharField(max_length=100)
    public_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(1)],
        blank=False, null=True,
        default=utils.generate_random_id,
    )
    public_thumbnail_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(20)],
        blank=False, null=False,
        default=utils.generate_long_random_id,
    )
    public_poster_frames_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(20)],
        blank=False, null=False,
        default=utils.generate_long_random_id,
    )

    owner = models.ForeignKey(User)

    def __str__(self):
        return '{} - {}'.format(self.public_id, self.title)

    @property
    def processing_status(self):
        return self.processing_state.status if self.processing_state else None

    @property
    def processing_progress(self):
        return self.processing_state.progress if self.processing_state else None

    @property
    def processing_started_at(self):
        return self.processing_state.started_at if self.processing_state else None

    @property
    def thumbnail_url(self):
        return backend.get().thumbnail_url(self.public_id, self.public_thumbnail_id)

    @property
    def poster_frames_url(self):
        return backend.get().poster_frames_url(self.public_id, self.public_poster_frames_id)


@receiver(post_save, sender=Video)
def create_video_processing_state(sender, instance=None, created=False, **kwargs):
    """
    Create ProcessingState object automatically for every created Video object.
    """
    if created:
        ProcessingState.objects.create(video=instance)


class Playlist(models.Model):
    name = models.CharField(max_length=128, db_index=True)
    videos = models.ManyToManyField(Video, related_name='playlists')
    owner = models.ForeignKey(User)
    public_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(1)],
        blank=False, null=True,
        default=utils.generate_random_id,
    )

    def __str__(self):
        return '{} - {}'.format(self.public_id, self.name)


class VideoUploadUrl(models.Model):
    """
    Video upload urls are generated in order to upload new videos. To each url is
    associated an expiration date after which is cannot be used. Note however
    that an upload that has started just before the expiry date should proceed
    normally.
    """
    public_video_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(1)],
        blank=False, null=True,
        default=utils.generate_random_id,
    )
    expires_at = models.IntegerField(
        verbose_name="Timestamp at which the url expires",
        db_index=True
    )
    was_used = models.BooleanField(
        verbose_name="Was the upload url used?",
        default=False,
        db_index=True
    )
    owner = models.ForeignKey(User, related_name='video_upload_urls')
    playlist = models.ForeignKey(
        Playlist,
        verbose_name="Playlist to which the video will be added after upload",
        blank=True, null=True
    )
    origin = models.CharField(
        verbose_name="Access-Control-Allow-Origin header value to add to CORS responses",
        max_length=256,
        blank=True, null=True
    )

    objects = managers.VideoUploadUrlManager()

    def __str__(self):
        return self.public_video_id


class ProcessingState(models.Model):

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_FAILED = 'failed'
    STATUS_SUCCESS = 'success'
    STATUS_RESTART = 'restart'
    STATUSES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_RESTART, 'Restart'),
    )

    video = models.OneToOneField(Video, related_name='processing_state')
    started_at = models.DateTimeField(
        verbose_name="Time of processing job start",
        auto_now=True
    )
    progress = models.FloatField(
        verbose_name="Progress percentage",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    status = models.CharField(
        verbose_name="Status",
        max_length=32,
        choices=STATUSES,
        blank=False,
        default=STATUS_PENDING,
    )
    message = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        return '{} - {}'.format(self.video, self.status)

    def set_pending(self):
        self.progress = 0
        self.status = self.STATUS_PENDING
        self.started_at = now()
        self.save()

    def set_processing(self, progress):
        self.progress = progress
        self.status = self.STATUS_PROCESSING
        self.save()

    def set_success(self):
        self.status = self.STATUS_SUCCESS
        self.save()

    def set_errors(self, errors):
        self.message = "\n".join(errors)
        if errors:
            self.status = self.STATUS_FAILED
        self.save()

class Subtitle(models.Model):

    LANGUAGE_CHOICES = [(code, name) for code, name in LANGUAGES if len(code) == 2]

    video = models.ForeignKey(Video, related_name='subtitles')
    public_id = models.CharField(
        max_length=20, unique=True,
        validators=[MinLengthValidator(1)],
        blank=False, null=True,
        default=utils.generate_random_id,
    )
    language = models.CharField(
        max_length=2,
        validators=[MinLengthValidator(2)],
        choices=LANGUAGE_CHOICES,
        null=True,
        blank=False
    )

    @property
    def url(self):
        return backend.get().subtitle_url(
            self.video.public_id, self.public_id, self.language
        )

    def __str__(self):
        return '{} - {} [{}]'.format(self.public_id, self.video, self.language)


class VideoFormat(models.Model):

    video = models.ForeignKey(Video, related_name='formats')
    name = models.CharField(max_length=128)
    bitrate = models.FloatField(validators=[MinValueValidator(0)])

    @property
    def url(self):
        return backend.get().video_url(self.video.public_id, self.name)

    def __str__(self):
        return '{} - {} [{}]'.format(self.name, self.video, self.bitrate)


@receiver([post_save, post_delete], sender=Video)
def invalidate_video_cache(sender, instance=None, created=False, **kwargs):
    if instance:
        invalidate_cache(instance.public_id)

@receiver([post_save, post_delete], sender=Subtitle)
@receiver([post_save, post_delete], sender=ProcessingState)
@receiver([post_save, post_delete], sender=VideoFormat)
def invalidate_related_video_cache(sender, instance=None, created=False, **kwargs):
    """
    Invalidate the video cache whenever a related object is saved.
    """
    if instance:
        invalidate_cache(instance.video.public_id)

def invalidate_cache(public_video_id):
    cache.invalidate(public_video_id)
