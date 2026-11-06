"""Fraud model for Indian vehicle claims: claim details plus checks on the claim photos.

The model learns from this app's own closed claims, using the outcome investigators
record (fraud / genuine) as the label. Photos are turned into a few signals that are
known to matter in motor fraud, instead of feeding raw pixels to a network, because
a few hundred labelled claims are far too few to teach a network what fraud looks like:

- the same damage photo already used on another claim (perceptual hash match)
- a photo taken before the incident date (old damage passed off as new)
- photos that went through an editing app, or with no camera date at all
- very small images (screenshots or pictures downloaded from the web)
"""
import json
import os
from datetime import date, datetime
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.tif', '.tiff'}
EDITING_SOFTWARE = (
    'photoshop', 'lightroom', 'snapseed', 'picsart', 'gimp', 'canva', 'photo editor',
    'pixlr', 'facetune', 'remini', 'polarr', 'vsco', 'paint',
)
# Two photos whose 64-bit difference hashes differ in at most this many bits are the same picture
# (re-saved, resized or lightly cropped).
DUPLICATE_HASH_BITS = 6
SMALL_IMAGE_PIXELS = 640 * 480

NUMERIC = [
    'vehicle_age_years', 'claim_amount_inr', 'claim_to_repair_ratio', 'claim_to_vehicle_price_ratio',
    'days_policy_to_incident', 'reporting_delay_days', 'police_report', 'witnesses', 'injuries',
    'number_of_vehicles', 'past_claims_count', 'incident_at_night',
    'photo_count', 'photos_reused_from_other_claims', 'photos_taken_before_incident',
    'photo_days_before_incident', 'photos_edited', 'photos_without_camera_date', 'photos_small',
]
CATEGORICAL = ['vehicle_make', 'fuel_type', 'body_style', 'incident_type', 'incident_severity', 'district']
FEATURES = NUMERIC + CATEGORICAL
LABELS = {'fraud': 1, 'genuine': 0}

FEATURE_LABELS = {
    'vehicle_age_years': 'Vehicle age (years)',
    'claim_amount_inr': 'Claimed amount (₹)',
    'claim_to_repair_ratio': 'Claim vs repair estimate',
    'claim_to_vehicle_price_ratio': 'Claim vs vehicle price',
    'days_policy_to_incident': 'Days from policy start to incident',
    'reporting_delay_days': 'Days taken to report',
    'police_report': 'Police report',
    'witnesses': 'Witnesses',
    'injuries': 'Injuries',
    'number_of_vehicles': 'Vehicles involved',
    'past_claims_count': 'Earlier claims by customer',
    'incident_at_night': 'Incident at night',
    'photo_count': 'Photos submitted',
    'photos_reused_from_other_claims': 'Photos already used on another claim',
    'photos_taken_before_incident': 'Photos taken before the incident',
    'photo_days_before_incident': 'Days a photo predates the incident',
    'photos_edited': 'Photos edited in an app',
    'photos_without_camera_date': 'Photos with no camera date',
    'photos_small': 'Low-resolution photos',
    'vehicle_make': 'Vehicle make',
    'fuel_type': 'Fuel type',
    'body_style': 'Body style',
    'incident_type': 'Incident type',
    'incident_severity': 'Damage severity',
    'district': 'District',
}

MODEL_FILENAME = 'vehicle_fraud.joblib'
REPORT_FILENAME = 'vehicle_fraud_report.json'


def models_dir():
    return Path(os.environ.get('VEHICLE_FRAUD_MODELS_DIR') or Path(settings.BASE_DIR).parent / 'ml' / 'models')


# ---------------------------------------------------------------- photo signals

def _difference_hash(image):
    """64-bit perceptual hash: stays the same when a photo is re-saved, resized or recompressed."""
    small = image.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    bits = 0
    for row in range(8):
        for column in range(8):
            left = pixels[row * 9 + column]
            right = pixels[row * 9 + column + 1]
            bits = (bits << 1) | (left > right)
    return bits


def _camera_date(exif):
    raw = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)  # DateTimeOriginal, then DateTime
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw).strip()[:19], '%Y:%m:%d %H:%M:%S').date()
    except ValueError:
        return None


_photo_cache = {}


def read_photo(path):
    """Hash, camera date, editing software and size of one image; None if it is not an image."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key in _photo_cache:
        return _photo_cache[key]
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            software = str(exif.get(0x0131) or '').lower()
            info = {
                'hash': _difference_hash(image),
                'camera_date': _camera_date(exif),
                'edited': any(name in software for name in EDITING_SOFTWARE),
                'pixels': image.width * image.height,
            }
    except (UnidentifiedImageError, OSError, ValueError):
        info = None
    _photo_cache[key] = info
    return info


def _claim_photo_paths(claim):
    paths = []
    for document in claim.documents.all():
        if not document.file:
            continue
        name = document.file.name or ''
        if document.document_type == 'photos' or Path(name).suffix.lower() in IMAGE_EXTENSIONS:
            try:
                paths.append(document.file.path)
            except (NotImplementedError, ValueError):
                continue
    return paths


def _other_claim_hashes(claim):
    """Hashes of photos on every other claim, for spotting the same picture used twice."""
    from apps.claims.models import ClaimDocument

    hashes = []
    others = ClaimDocument.objects.exclude(claim_id=claim.pk).exclude(file='').only('file', 'document_type')
    for document in others.iterator():
        if document.document_type != 'photos' and Path(document.file.name).suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        try:
            info = read_photo(document.file.path)
        except (NotImplementedError, ValueError):
            continue
        if info:
            hashes.append(info['hash'])
    return hashes


def photo_signals(claim, other_hashes=None):
    photos = [info for info in (read_photo(path) for path in _claim_photo_paths(claim)) if info]
    if other_hashes is None:
        other_hashes = _other_claim_hashes(claim)
    incident = claim.incident_date
    days_before = [
        (incident - info['camera_date']).days
        for info in photos if info['camera_date'] and incident and info['camera_date'] < incident
    ]
    return {
        'photo_count': len(photos),
        'photos_reused_from_other_claims': sum(
            any(bin(info['hash'] ^ other).count('1') <= DUPLICATE_HASH_BITS for other in other_hashes)
            for info in photos
        ),
        'photos_taken_before_incident': len(days_before),
        'photo_days_before_incident': max(days_before, default=0),
        'photos_edited': sum(info['edited'] for info in photos),
        'photos_without_camera_date': sum(info['camera_date'] is None for info in photos),
        'photos_small': sum(info['pixels'] < SMALL_IMAGE_PIXELS for info in photos),
    }


# ---------------------------------------------------------------- claim features

def _ratio(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator)


def claim_features(claim, other_hashes=None):
    """One feature row for a claim; only details known when the claim is filed."""
    from apps.claims.models import Claim

    vehicle = claim.vehicle
    policy = claim.policy
    incident = claim.incident_date
    reported = claim.submitted_at.date() if claim.submitted_at else None
    row = {
        'vehicle_make': (vehicle.make or '').strip().title() if vehicle else None,
        'fuel_type': vehicle.fuel_type if vehicle else None,
        'body_style': (vehicle.body_style or None) if vehicle else None,
        'vehicle_age_years': (incident.year - vehicle.year) if vehicle and vehicle.year and incident else None,
        'incident_type': claim.incident_type,
        'incident_severity': claim.incident_severity,
        'district': (claim.location or '').split(',')[0].strip().title() or None,
        'claim_amount_inr': float(claim.claim_amount or 0),
        'claim_to_repair_ratio': _ratio(claim.claim_amount, claim.estimated_repair_cost),
        'claim_to_vehicle_price_ratio': _ratio(claim.claim_amount, vehicle.purchase_price if vehicle else None),
        'days_policy_to_incident': (incident - policy.start_date).days if policy and policy.start_date and incident else None,
        'reporting_delay_days': (reported - incident).days if reported and incident else None,
        'police_report': int(bool(claim.police_report)),
        'witnesses': int(bool(claim.witnesses)),
        'injuries': int(bool(claim.injuries)),
        'number_of_vehicles': claim.number_of_vehicles,
        'past_claims_count': Claim.objects.filter(
            customer_id=claim.customer_id, incident_date__lt=incident,
        ).count() if incident else 0,
        'incident_at_night': int(bool(claim.incident_time and (claim.incident_time.hour >= 22 or claim.incident_time.hour < 5))),
    }
    row.update(photo_signals(claim, other_hashes))
    return row


def feature_frame(rows):
    return pd.DataFrame(rows, columns=FEATURES)


# ---------------------------------------------------------------- inference

_loaded = {'key': None, 'bundle': None}


def load_bundle():
    """The trained model with its threshold and baselines, reloaded after retraining."""
    path = models_dir() / MODEL_FILENAME
    try:
        stat = os.stat(path)
    except OSError:
        _loaded.update(key=None, bundle=None)
        return None
    key = (str(path), stat.st_mtime_ns)
    if _loaded['key'] != key:
        _loaded.update(key=key, bundle=joblib.load(path))
    return _loaded['bundle']


def _probability(model, frame):
    classes = list(model.classes_)
    return float(model.predict_proba(frame)[0][classes.index(1)])


def _reasons(model, frame, score, baselines, limit=3):
    """Points each value adds: the score drop when that value is reset to the typical one."""
    reasons = []
    for column in frame.columns:
        value = frame.at[0, column]
        if column not in baselines or value is None or pd.isna(value) or value == baselines[column]:
            continue
        typical = frame.copy()
        typical[column] = typical[column].astype(object)
        typical.at[0, column] = baselines[column]
        points = score - _probability(model, typical) * 100
        if points >= 1.0:
            shown = value.item() if hasattr(value, 'item') else value
            if isinstance(shown, float):
                shown = round(shown, 2)
            reasons.append({
                'feature': column,
                'value': shown,
                'points': round(points, 1),
                'text': f"{FEATURE_LABELS.get(column, column)} ({shown}) added {points:.0f} points",
            })
    reasons.sort(key=lambda reason: reason['points'], reverse=True)
    return reasons[:limit]


def score_claim(claim):
    """Fraud result for an app claim, or None when no vehicle fraud model has been trained yet."""
    bundle = load_bundle()
    if bundle is None:
        return None
    from ml_service import _fraud_result

    model = bundle['model']
    frame = feature_frame([claim_features(claim)])
    score = _probability(model, frame) * 100
    reasons = _reasons(model, frame, score, bundle.get('baselines', {}))
    result = _fraud_result(score, float(bundle['threshold']) * 100, reasons)
    result['model'] = 'vehicle_fraud'
    result['photo_signals'] = {name: int(frame.at[0, name]) for name in NUMERIC if name.startswith('photo')}
    return result


def training_report():
    try:
        return json.loads((models_dir() / REPORT_FILENAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, 'item'):
        return value.item()
    raise TypeError(f'Cannot serialise {type(value).__name__}')
