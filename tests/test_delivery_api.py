import base64
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from delivery_app.auth import LineProfile
from delivery_app.config import DeliverySettings
from delivery_app.db import DeliveryCustomer, DeliveryLocation, create_db_engine, create_session_factory, init_db
from delivery_app.main import create_app
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
            s3_endpoint="",
            s3_bucket="bucket",
            s3_access_key_id="",
            s3_secret_access_key="",
            s3_region="auto",
            app_base_url="https://delivery.example.com",
            admin_password="admin-pass",
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
            files={"photo": ("shop.jpg", b"fake-image-bytes", "image/jpeg")},
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
            files={"photo": ("shop.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertTrue(duplicate_response.json()["duplicate"])

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
            s3_endpoint="",
            s3_bucket="bucket",
            s3_access_key_id="",
            s3_secret_access_key="",
            s3_region="auto",
            app_base_url="https://delivery.example.com",
            admin_password="admin-pass",
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
            files={"photo": ("shop.jpg", b"fake-image-bytes", "image/jpeg")},
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
            files={"photo": ("shop.jpg", b"fake-image-bytes", "image/jpeg")},
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


if __name__ == "__main__":
    unittest.main()
