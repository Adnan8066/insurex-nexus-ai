import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.claims.tests import make_customer_records


def png_bytes():
    buffer = BytesIO()
    Image.new('RGB', (16, 16), (30, 80, 170)).save(buffer, 'PNG')
    return buffer.getvalue()


class VehicleImageUploadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin = User.objects.create_user(
            username='imgadmin', email='imgadmin@example.com', password='x', role=Role.ADMIN,
        )
        _, _, self.vehicle = make_customer_records('imagecust', 'VINIMAGE00000001')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.url = f'/api/v1/vehicles/{self.vehicle.pk}/'

    def test_png_upload_is_stored_and_returned(self):
        upload = SimpleUploadedFile('car.png', png_bytes(), content_type='image/png')
        response = self.client.patch(self.url, {'image': upload}, format='multipart')
        self.assertEqual(response.status_code, 200, response.content)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.image.name.startswith('vehicle_images/'))
        detail = self.client.get(self.url).json()
        self.assertIsNotNone(detail['image_url'])
        self.assertTrue(detail['image_url'].endswith('.png'))

    def test_non_image_file_is_rejected(self):
        upload = SimpleUploadedFile('evil.png', b'<html><script>x</script></html>', content_type='image/png')
        response = self.client.patch(self.url, {'image': upload}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.image)

    def test_pdf_is_not_accepted_as_vehicle_image(self):
        upload = SimpleUploadedFile('papers.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = self.client.patch(self.url, {'image': upload}, format='multipart')
        self.assertEqual(response.status_code, 400)
