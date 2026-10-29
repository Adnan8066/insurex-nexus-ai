"""Validation shared by every user-facing file upload (claim, policy, vehicle,
customer documents and investigation evidence).

Policy:
* size limit: MAX_UPLOAD_BYTES (25 MB, matching the client-side check);
* allow-list: JPEG, PNG, WEBP, BMP images and PDF documents (investigation
  evidence additionally accepts MP4/MOV/M4A/MP3/WAV);
* the file content (magic bytes, and a Pillow decode for images) must match the
  extension, so e.g. an HTML file renamed to ``.jpg`` is rejected;
* the stored file name is replaced with a random name, so uploaded paths are not
  guessable from the original file name (the original name is kept separately).

EXIF metadata is intentionally left intact: GPS/time metadata on claim photos is
evidence used by adjusters and investigators.
"""
import os
import uuid

from django.conf import settings
from rest_framework import serializers

MAX_UPLOAD_BYTES = getattr(settings, 'MAX_UPLOAD_BYTES', 25 * 1024 * 1024)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS | {'.pdf'}
# Investigation evidence may also be video/audio (EvidenceType.VIDEO/AUDIO).
EVIDENCE_EXTENSIONS = DOCUMENT_EXTENSIONS | {'.mp4', '.mov', '.m4a', '.mp3', '.wav'}


def _matches_signature(extension, head):
    if extension in ('.jpg', '.jpeg'):
        return head.startswith(b'\xff\xd8\xff')
    if extension == '.png':
        return head.startswith(b'\x89PNG\r\n\x1a\n')
    if extension == '.webp':
        return head[:4] == b'RIFF' and head[8:12] == b'WEBP'
    if extension == '.bmp':
        return head.startswith(b'BM')
    if extension == '.pdf':
        return head.startswith(b'%PDF-')
    if extension in ('.mp4', '.mov', '.m4a'):
        return head[4:8] in (b'ftyp', b'moov', b'mdat', b'wide', b'free')
    if extension == '.mp3':
        return head.startswith(b'ID3') or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    if extension == '.wav':
        return head[:4] == b'RIFF' and head[8:12] == b'WAVE'
    return False


def validate_upload(file, allowed_extensions=DOCUMENT_EXTENSIONS):
    """Validate an uploaded file and give it a random storage name."""
    if file is None:
        return file
    extension = os.path.splitext(file.name or '')[1].lower()
    if extension not in allowed_extensions:
        raise serializers.ValidationError(
            'Unsupported file type. Allowed types: ' + ', '.join(sorted(allowed_extensions)) + '.'
        )
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError(
            f'File is too large. The maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.'
        )
    if file.size == 0:
        raise serializers.ValidationError('The submitted file is empty.')

    position = file.tell() if hasattr(file, 'tell') else 0
    file.seek(0)
    head = file.read(16)
    file.seek(0)
    if not _matches_signature(extension, head):
        raise serializers.ValidationError('File content does not match its extension.')

    if extension in IMAGE_EXTENSIONS:
        from PIL import Image
        try:
            with Image.open(file) as image:
                image.verify()
        except Exception:
            raise serializers.ValidationError('The uploaded image is corrupt or not a valid image.')
        finally:
            file.seek(position)

    file.name = f'{uuid.uuid4().hex}{extension}'
    return file
