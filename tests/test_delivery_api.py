import base64
from datetime import datetime, timedelta
from io import BytesIO
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image, ExifTags
from sqlalchemy.orm import Session

from delivery_app.auth import LineProfile
from delivery_app.config import DeliverySettings
from delivery_app.db import DeliveryCustomer, DeliveryLocation, VisitReport, create_db_engine, create_session_factory, init_db
from delivery_app.main import create_app
from delivery_app.photo_metadata import build_variant_object_key
from delivery_app.repository import count_reports
from delivery_app.storage import InMemoryStorage


class StubLineVerifier:
    def verify_id_token(self, id_token: str) -> LineProfile:
        if id_token != "valid-token":
            raise ValueError("LINE token verification failed")
        return LineProfile(
            line_user_id="line-user-1",
            display_name="Driver One",
            picture_url="https://example.com/pic.jpg",
        )


class DeliveryApiTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_url = f"sqlite:///{self.tmpdir.name}/delivery.db"
        self.settings = DeliverySettings(
            delivery_database_url=self.db_url,
            line_liff_id="test-liff-id",
            line_channel_id="test-channel-id",
            line_channel_secret="test-secret",
            loyverse_token="test-loyverse-token",
            s3_endpoint="",
            s3_bucket="bucket",
            s3_access_key_id="",
            s3_secret_access_key="",
            s3_region="auto",
            app_base_url="https://delivery.example.com",
            admin_password="admin-pass",
            sync_secret="sync-secret",
            source_sqlite_path="loyverse_data.db",
            bootstrap_seed_metadata=False,
        )
        self.engine = create_db_engine(self.db_url)
        init_db(self.engine)
        self.session_factory = create_session_factory(self.engine)
        self.storage = InMemoryStorage()
        self.app = create_app(self.settings, session_factory=self.session_factory, storage=self.storage, line_verifier=StubLineVerifier())
        self.client = TestClient(self.app, base_url="https://testserver")
        self._seed_customer()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _seed_customer(self):
        session: Session = self.session_factory()
        try:
            session.add(DeliveryLocation(id="loc_1", name="Alpha", source_category_id="loc_1", customer_count=1))
            session.add(DeliveryLocation(id="loc_2", name="Beta", source_category_id="loc_2", customer_count=1))
            session.add(
                DeliveryCustomer(
                    customer_id="cust_1",
                    name="Shop One",
                    customer_code="S1",
                    phone="081",
                    primary_location_id="loc_1",
                )
            )
            session.add(
                DeliveryCustomer(
                    customer_id="cust_2",
                    name="Shop Two",
                    customer_code="S2",
                    phone="082",
                    primary_location_id="loc_2",
                )
            )
            session.commit()
        finally:
            session.close()

    def _login(self):
        response = self.client.post("/api/session", json={"id_token": "valid-token"})
        self.assertEqual(response.status_code, 200)

    def _build_test_jpeg(self, color="red", size=(16, 16)):
        image = Image.new("RGB", size, color)
        output = BytesIO()
        image.save(output, format="JPEG")
        return output.getvalue()

    def test_login_location_customer_and_report_flow(self):
        self._login()

        session_response = self.client.get("/api/session")
        self.assertEqual(session_response.status_code, 200)
        self.assertTrue(session_response.json()["authenticated"])

        locations_response = self.client.get("/api/locations")
        self.assertEqual(locations_response.status_code, 200)
        self.assertEqual(len(locations_response.json()["locations"]), 2)

        customers_response = self.client.get("/api/customers", params={"location_id": "loc_1", "q": "Shop"})
        self.assertEqual(customers_response.status_code, 200)
        self.assertEqual(len(customers_response.json()["customers"]), 1)

        upload_response = self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-1",
                "customer_id": "cust_1",
                "latitude": "13.7563",
                "longitude": "100.5018",
                "accuracy_m": "8",
                "captured_at_client": "2026-03-10T02:03:04Z",
            },
            files={"photo": ("shop.jpg", self._build_test_jpeg(), "image/jpeg")},
        )
        self.assertEqual(upload_response.status_code, 200)
        self.assertFalse(upload_response.json()["duplicate"])

        duplicate_response = self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-1",
                "customer_id": "cust_1",
                "latitude": "13.7563",
                "longitude": "100.5018",
                "captured_at_client": "2026-03-10T02:03:04Z",
            },
            files={"photo": ("shop.jpg", self._build_test_jpeg(), "image/jpeg")},
        )
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertTrue(duplicate_response.json()["duplicate"])
        self.assertEqual(len(self.storage.objects), 3)

        session = self.session_factory()
        try:
            self.assertEqual(count_reports(session), 1)
        finally:
            session.close()

    def test_guest_mode_can_access_picker_without_liff_login(self):
        session_response = self.client.get("/api/session")
        self.assertEqual(session_response.status_code, 200)
        self.assertTrue(session_response.json()["authenticated"])
        self.assertTrue(session_response.json()["guestMode"])

        locations_response = self.client.get("/api/locations")
        self.assertEqual(locations_response.status_code, 200)
        self.assertEqual(len(locations_response.json()["locations"]), 2)

        customers_response = self.client.get("/api/customers", params={"location_id": "loc_1"})
        self.assertEqual(customers_response.status_code, 200)
        self.assertEqual(len(customers_response.json()["customers"]), 1)

    def test_assigned_location_access_is_enforced(self):
        self.settings = DeliverySettings(
            delivery_database_url=self.db_url,
            line_liff_id="test-liff-id",
            line_channel_id="test-channel-id",
            line_channel_secret="test-secret",
            loyverse_token="test-loyverse-token",
            s3_endpoint="",
            s3_bucket="bucket",
            s3_access_key_id="",
            s3_secret_access_key="",
            s3_region="auto",
            app_base_url="https://delivery.example.com",
            admin_password="admin-pass",
            sync_secret="sync-secret",
            source_sqlite_path="loyverse_data.db",
            bootstrap_seed_metadata=False,
            enforce_location_access=True,
        )
        self.app = create_app(self.settings, session_factory=self.session_factory, storage=self.storage, line_verifier=StubLineVerifier())
        self.client = TestClient(self.app, base_url="https://testserver")
        self._login()
        credentials = base64.b64encode(b"admin:admin-pass").decode("utf-8")
        assign_response = self.client.put(
            "/admin/access/users/line-user-1/locations",
            headers={"Authorization": f"Basic {credentials}"},
            json={"access_mode": "assigned", "location_ids": ["loc_1"]},
        )
        self.assertEqual(assign_response.status_code, 200)
        self.assertEqual(assign_response.json()["allowedLocationIds"], ["loc_1"])

        session_response = self.client.get("/api/session")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json()["user"]["accessMode"], "assigned")
        self.assertEqual(session_response.json()["user"]["allowedLocationIds"], ["loc_1"])

        locations_response = self.client.get("/api/locations")
        self.assertEqual(locations_response.status_code, 200)
        self.assertEqual([row["id"] for row in locations_response.json()["locations"]], ["loc_1"])

        allowed_customers = self.client.get("/api/customers", params={"location_id": "loc_1"})
        self.assertEqual(allowed_customers.status_code, 200)
        self.assertEqual(len(allowed_customers.json()["customers"]), 1)

        blocked_customers = self.client.get("/api/customers", params={"location_id": "loc_2"})
        self.assertEqual(blocked_customers.status_code, 403)

        blocked_upload = self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-blocked",
                "customer_id": "cust_2",
                "latitude": "13.7563",
                "longitude": "100.5018",
                "captured_at_client": "2026-03-10T02:03:04Z",
            },
            files={"photo": ("shop.jpg", self._build_test_jpeg(), "image/jpeg")},
        )
        self.assertEqual(blocked_upload.status_code, 403)

    def test_assigned_location_access_is_disabled_by_default(self):
        self._login()
        credentials = base64.b64encode(b"admin:admin-pass").decode("utf-8")
        assign_response = self.client.put(
            "/admin/access/users/line-user-1/locations",
            headers={"Authorization": f"Basic {credentials}"},
            json={"access_mode": "assigned", "location_ids": ["loc_1"]},
        )
        self.assertEqual(assign_response.status_code, 200)

        session_response = self.client.get("/api/session")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json()["user"]["accessMode"], "all")
        self.assertEqual(session_response.json()["user"]["allowedLocationIds"], [])

        locations_response = self.client.get("/api/locations")
        self.assertEqual(locations_response.status_code, 200)
        self.assertEqual(len(locations_response.json()["locations"]), 2)

        customers_response = self.client.get("/api/customers", params={"location_id": "loc_2"})
        self.assertEqual(customers_response.status_code, 200)
        self.assertEqual(len(customers_response.json()["customers"]), 1)

    def test_admin_reports_requires_basic_auth_and_returns_results(self):
        self._login()
        self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-2",
                "customer_id": "cust_1",
                "latitude": "13.7563",
                "longitude": "100.5018",
                "captured_at_client": "2026-03-10T02:03:04Z",
            },
            files={"photo": ("shop.jpg", self._build_test_jpeg(), "image/jpeg")},
        )

        unauthenticated = self.client.get("/admin/reports")
        self.assertEqual(unauthenticated.status_code, 401)

        credentials = base64.b64encode(b"admin:admin-pass").decode("utf-8")
        authenticated = self.client.get(
            "/admin/reports",
            headers={"Authorization": f"Basic {credentials}"},
        )
        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(len(authenticated.json()["reports"]), 1)

        access_users = self.client.get(
            "/admin/access/users",
            headers={"Authorization": f"Basic {credentials}"},
        )
        self.assertEqual(access_users.status_code, 200)
        self.assertGreaterEqual(len(access_users.json()["users"]), 1)

    def test_admin_reports_can_filter_multiple_locations(self):
        self._login()
        self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-loc-1",
                "customer_id": "cust_1",
                "latitude": "13.7563",
                "longitude": "100.5018",
                "captured_at_client": "2026-03-10T02:03:04Z",
            },
            files={"photo": ("shop-a.jpg", self._build_test_jpeg("blue"), "image/jpeg")},
        )
        self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-loc-2",
                "customer_id": "cust_2",
                "latitude": "13.8563",
                "longitude": "100.6018",
                "captured_at_client": "2026-03-10T03:03:04Z",
            },
            files={"photo": ("shop-b.jpg", self._build_test_jpeg("green"), "image/jpeg")},
        )

        credentials = base64.b64encode(b"admin:admin-pass").decode("utf-8")
        filtered = self.client.get(
            "/admin/reports",
            headers={"Authorization": f"Basic {credentials}"},
            params=[("location_ids", "loc_1"), ("location_ids", "loc_2")],
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.json()["reports"]), 2)

        single_location = self.client.get(
            "/admin/reports",
            headers={"Authorization": f"Basic {credentials}"},
            params=[("location_ids", "loc_2")],
        )
        self.assertEqual(single_location.status_code, 200)
        self.assertEqual([row["locationId"] for row in single_location.json()["reports"]], ["loc_2"])

    def test_admin_reports_can_paginate_older_results(self):
        self._login()
        session = self.session_factory()
        try:
            base_time = datetime(2026, 3, 10, 0, 0, 0)
            reports = [
                VisitReport(
                    client_submission_id=f"submission-{index}",
                    line_user_id="line-user-1",
                    customer_id="cust_1",
                    location_id="loc_1",
                    photo_object_key=f"reports/test/{index}.jpg",
                    photo_url=f"https://delivery.example.com/api/photos/reports/test/{index}.jpg",
                    latitude=13.75,
                    longitude=100.50,
                    accuracy_m=5.0,
                    captured_at_client=base_time - timedelta(minutes=index),
                    received_at_server=base_time - timedelta(minutes=index),
                )
                for index in range(65)
            ]
            session.add_all(reports)
            session.commit()
        finally:
            session.close()

        credentials = base64.b64encode(b"admin:admin-pass").decode("utf-8")
        first_page = self.client.get(
            "/admin/reports",
            headers={"Authorization": f"Basic {credentials}"},
        )
        self.assertEqual(first_page.status_code, 200)
        first_payload = first_page.json()
        self.assertEqual(len(first_payload["reports"]), 60)
        self.assertTrue(first_payload["hasMore"])
        self.assertIsNotNone(first_payload["nextCursor"])

        second_page = self.client.get(
            "/admin/reports",
            headers={"Authorization": f"Basic {credentials}"},
            params={
                "before_received_at": first_payload["nextCursor"]["beforeReceivedAt"],
                "before_id": first_payload["nextCursor"]["beforeId"],
            },
        )
        self.assertEqual(second_page.status_code, 200)
        second_payload = second_page.json()
        self.assertEqual(len(second_payload["reports"]), 5)
        self.assertFalse(second_payload["hasMore"])

        first_ids = {report["id"] for report in first_payload["reports"]}
        second_ids = {report["id"] for report in second_payload["reports"]}
        self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_admin_access_users_excludes_guest_and_includes_last_login(self):
        guest_session = self.client.get("/api/session")
        self.assertEqual(guest_session.status_code, 200)
        self.assertTrue(guest_session.json()["guestMode"])

        self._login()
        credentials = base64.b64encode(b"admin:admin-pass").decode("utf-8")
        response = self.client.get(
            "/admin/access/users",
            headers={"Authorization": f"Basic {credentials}"},
        )
        self.assertEqual(response.status_code, 200)
        users = response.json()["users"]
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["lineUserId"], "line-user-1")
        self.assertIsNotNone(users[0]["lastLoginAt"])
        self.assertNotIn("guest-preview", [user["lineUserId"] for user in users])

    def test_uploaded_jpeg_contains_exif_gps_and_capture_time(self):
        self._login()
        upload_response = self.client.post(
            "/api/reports",
            data={
                "client_submission_id": "submission-exif",
                "customer_id": "cust_1",
                "latitude": "13.7563",
                "longitude": "100.5018",
                "accuracy_m": "8.5",
                "captured_at_client": "2026-03-10T02:03:04Z",
            },
            files={"photo": ("shop.jpg", self._build_test_jpeg("purple", size=(2400, 1800)), "image/jpeg")},
        )
        self.assertEqual(upload_response.status_code, 200)

        original_key = [key for key in self.storage.objects.keys() if "__display" not in key and "__thumb" not in key][0]

        original_payload = self.storage.objects[original_key]["payload"]
        display_payload = self.storage.objects[build_variant_object_key(original_key, "display")]["payload"]
        thumb_payload = self.storage.objects[build_variant_object_key(original_key, "thumb")]["payload"]

        image = Image.open(BytesIO(original_payload))
        exif = image.getexif()
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)

        self.assertEqual(exif.get(ExifTags.Base.DateTimeOriginal), "2026:03:10 02:03:04")
        self.assertEqual(gps[ExifTags.GPS.GPSLatitudeRef], "N")
        self.assertEqual(gps[ExifTags.GPS.GPSLongitudeRef], "E")
        self.assertAlmostEqual(float(gps[ExifTags.GPS.GPSHPositioningError]), 8.5, places=2)
        self.assertEqual(
            tuple(round(float(value), 4) for value in gps[ExifTags.GPS.GPSLatitude]),
            (13.0, 45.0, 22.68),
        )
        self.assertEqual(image.size, (2400, 1800))
        self.assertEqual(Image.open(BytesIO(display_payload)).size, (1600, 1200))
        self.assertEqual(Image.open(BytesIO(thumb_payload)).size, (640, 480))

    @patch("delivery_app.main.sync_delivery_customers_from_loyverse")
    def test_internal_customer_sync_requires_secret_and_runs(self, mock_sync):
        mock_sync.return_value = {
            "customers": 10,
            "new_customers": 2,
            "updated_customers": 1,
            "unchanged_customers": 7,
            "skipped_customers": 0,
            "unassigned_customers": 3,
        }

        unauthenticated = self.client.post("/internal/sync/customers")
        self.assertEqual(unauthenticated.status_code, 401)

        authenticated = self.client.post(
            "/internal/sync/customers",
            headers={"X-Delivery-Sync-Secret": "sync-secret"},
        )
        self.assertEqual(authenticated.status_code, 200)
        self.assertTrue(authenticated.json()["ok"])
        self.assertEqual(authenticated.json()["result"]["new_customers"], 2)
        self.assertEqual(mock_sync.call_count, 1)


if __name__ == "__main__":
    unittest.main()
