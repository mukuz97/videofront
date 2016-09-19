import os

from django.views import static

from .backend import Backend

# In production, the following views should NOT be used. For efficiency
# reasons, the corresponding urls should be served directly by the web server
# (e.g: Nginx).

def storage_video(request, video_id, format_name):
    return serve_file(request, Backend.get_video_file_path(video_id, format_name))

def storage_subtitle(request, video_id, subtitle_id, language_code):
    return serve_file(request, Backend.get_subtitle_file_path(video_id, subtitle_id, language_code))

def storage_thumbnail(request, video_id, thumbnail_id):
    return serve_file(request, Backend.get_thumbnail_file_path(video_id, thumbnail_id))

def serve_file(request, path):
    """ Serve a file directly from the filesystem """
    document_root = os.path.dirname(path)
    filename = os.path.basename(path)
    return static.serve(request, filename, document_root=document_root)
