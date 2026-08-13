from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class QrScannerInterfaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="scanner-admin",
            email="scanner@example.com",
            password="secret",
        )
        self.client.force_login(self.user)

    def test_scanner_page_exposes_live_photo_and_manual_modes(self):
        response = self.client.get(reverse("core:ticket_scanner"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="start-camera"')
        self.assertContains(response, 'id="scanner-photo"')
        self.assertContains(response, 'capture="environment"')
        self.assertContains(response, "Escanear desde foto")
        self.assertContains(response, 'id="scanner-value"')
        self.assertContains(response, "vendor/qr-scanner/qr-scanner.umd.min.js")
        self.assertContains(response, "/static/js/ticket-scanner.")

    def test_scanner_client_diagnoses_insecure_context_and_camera_errors(self):
        source = (Path(settings.BASE_DIR) / "static/js/ticket-scanner.js").read_text()

        self.assertIn("window.isSecureContext", source)
        self.assertIn("navigator.mediaDevices", source)
        self.assertIn("NotAllowedError", source)
        self.assertIn("NotReadableError", source)
        self.assertIn("QrScanner.scanImage", source)
        self.assertIn("BarcodeDetector", source)

    def test_docker_image_bundles_qr_scanner_and_worker(self):
        dockerfile = (Path(settings.BASE_DIR) / "Dockerfile").read_text()

        self.assertIn("qr-scanner@1.4.2", dockerfile)
        self.assertIn("qr-scanner.umd.min.js", dockerfile)
        self.assertIn("qr-scanner-worker.min.js", dockerfile)
        self.assertIn("qr-scanner/LICENSE", dockerfile)
