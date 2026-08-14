import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.utils._os import safe_join


@login_required
def protected_media(request, path):
    """Serve client documents only to authenticated CRM users."""
    try:
        file_path = Path(safe_join(settings.MEDIA_ROOT, path))
    except ValueError as exc:
        raise Http404 from exc

    if not file_path.is_file():
        raise Http404

    content_type, _ = mimetypes.guess_type(file_path.name)
    return FileResponse(
        file_path.open('rb'),
        content_type=content_type or 'application/octet-stream',
        as_attachment=False,
        filename=file_path.name,
    )
