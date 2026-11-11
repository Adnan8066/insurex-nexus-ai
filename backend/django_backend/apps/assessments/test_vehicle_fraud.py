import io
import os
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.assessments import vehicle_fraud as vf
from apps.assessments.ai_views import detect_fraud_internal
from apps.claims.models import Claim, ClaimDocument
from apps.claims.tests import make_customer_records

TEMP_MEDIA = tempfile.mkdtemp(prefix='vehicle-fraud-media-')


def photo_bytes(seed, camera_date, software=None, size=(800, 600), base=None):
    """JPEG with a camera date; `base` reuses one picture with slight noise (same photo re-saved)."""
    rng = np.random.default_rng(seed)
    if base is None:
        pixels = rng.integers(0, 255, (8, 8, 3), dtype=np.uint8)
    else:
        pixels = np.clip(base.astype(int) + rng.integers(-3, 4, base.shape), 0, 255).astype(np.uint8)
    image = Image.fromarray(pixels).resize(size, Image.Resampling.BICUBIC)
    exif = Image.Exif()
    # Set the Exif sub-IFD as a whole: writing through get_ifd() is dropped on save in Pillow 11.0.
    exif[0x8769] = {0x9003: camera_date.strftime('%Y:%m:%d 10:00:00')}
    if software:
        exif[0x0131] = software
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', exif=exif)
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class VehicleFraudModelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.customer, self.policy, self.vehicle = make_customer_records('vfcust', 'VINVEHFRAUD000001')
        self.vehicle.make, self.vehicle.model, self.vehicle.year = 'Maruti Suzuki', 'Swift', 2019
        self.vehicle.save()
        self.models_dir = tempfile.mkdtemp(prefix='vehicle-fraud-models-')
        self.addCleanup(shutil.rmtree, self.models_dir, True)
        env = mock.patch.dict(os.environ, {'VEHICLE_FRAUD_MODELS_DIR': self.models_dir})
        env.start()
        self.addCleanup(env.stop)
        self.reused = np.random.default_rng(999).integers(0, 255, (8, 8, 3), dtype=np.uint8)
        self.count = 0

    def make_claim(self, fraud_like, outcome=''):
        self.count += 1
        incident = timezone.localdate() - timedelta(days=30)
        claim = Claim.objects.create(
            claim_number=f'CLM-VF{self.count:05d}', customer=self.customer, policy=self.policy,
            vehicle=self.vehicle, incident_date=incident, incident_type='collision',
            incident_severity='major' if fraud_like else 'minor', location='Ernakulam, Kerala',
            claim_amount=Decimal('180000') if fraud_like else Decimal('30000'),
            estimated_repair_cost=Decimal('60000') if fraud_like else Decimal('28000'),
            police_report=not fraud_like, fraud_outcome=outcome,
        )
        if fraud_like:
            content = photo_bytes(self.count, incident - timedelta(days=90), 'Snapseed 2.0', base=self.reused)
        else:
            content = photo_bytes(self.count, incident)
        ClaimDocument.objects.create(
            claim=claim, document_type='photos', original_name='damage.jpg',
            file=SimpleUploadedFile(f'damage{self.count}.jpg', content, content_type='image/jpeg'),
        )
        return claim

    def test_photo_signals_catch_reused_backdated_edited_photos(self):
        self.make_claim(fraud_like=True)
        suspicious = self.make_claim(fraud_like=True)
        honest = self.make_claim(fraud_like=False)

        signals = vf.photo_signals(suspicious)
        self.assertEqual(signals['photo_count'], 1)
        self.assertEqual(signals['photos_reused_from_other_claims'], 1)
        self.assertEqual(signals['photos_taken_before_incident'], 1)
        self.assertEqual(signals['photo_days_before_incident'], 90)
        self.assertEqual(signals['photos_edited'], 1)

        clean = vf.photo_signals(honest)
        self.assertEqual(clean['photos_reused_from_other_claims'], 0)
        self.assertEqual(clean['photos_taken_before_incident'], 0)
        self.assertEqual(clean['photos_edited'], 0)

    def test_refuses_to_train_without_enough_investigated_claims(self):
        for _ in range(3):
            self.make_claim(True, 'fraud')
            self.make_claim(False, 'genuine')
        with self.assertRaisesMessage(CommandError, 'Not enough investigated claims'):
            call_command('train_vehicle_fraud_model', stdout=StringIO())
        self.assertIsNone(vf.score_claim(self.make_claim(True)))

    def test_trains_and_scores_new_claims(self):
        for _ in range(20):
            self.make_claim(True, 'fraud')
            self.make_claim(False, 'genuine')
        self.make_claim(True, 'unclear')  # excluded from training

        output = StringIO()
        call_command('train_vehicle_fraud_model', stdout=output)
        self.assertIn('Labelled claims: 40 (20 fraud, 20 genuine)', output.getvalue())
        report = vf.training_report()
        self.assertEqual(report['labelled_claims'], 40)
        self.assertEqual(report['claims_with_photos'], 40)
        self.assertGreater(report['metrics']['roc_auc'], 0.9)

        suspicious = self.make_claim(fraud_like=True)
        honest = self.make_claim(fraud_like=False)
        suspicious_result = vf.score_claim(suspicious)
        honest_result = vf.score_claim(honest)
        self.assertGreater(suspicious_result['score'], honest_result['score'])
        self.assertEqual(suspicious_result['level'], 'high')
        self.assertEqual(suspicious_result['photo_signals']['photos_reused_from_other_claims'], 1)
        self.assertTrue(suspicious_result['explanations'])

        combined = detect_fraud_internal(suspicious)
        self.assertEqual(combined['model'], 'vehicle_fraud')
