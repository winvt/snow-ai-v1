from datetime import datetime
import tempfile
import unittest

from sqlalchemy.orm import Session

from delivery_app.db import (
    DeliveryCustomer,
    DeliveryLocation,
    DeliveryUser,
    VisitReport,
    create_db_engine,
    create_session_factory,
    init_db,
)
from delivery_app.report_recovery import import_reports_from_sqlite


class DeliveryReportRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.source_db_path = f"{self.tmpdir.name}/source.db"
        self.destination_db_path = f"{self.tmpdir.name}/destination.db"
        self.source_db_url = f"sqlite:///{self.source_db_path}"
        self.destination_db_url = f"sqlite:///{self.destination_db_path}"

        self.source_engine = create_db_engine(self.source_db_url)
        self.destination_engine = create_db_engine(self.destination_db_url)
        init_db(self.source_engine)
        init_db(self.destination_engine)
        self.source_session_factory = create_session_factory(self.source_engine)
        self.destination_session_factory = create_session_factory(self.destination_engine)
        self._seed_source()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _seed_source(self):
        session: Session = self.source_session_factory()
        try:
            session.add(
                DeliveryLocation(
                    id="loc_1",
                    name="Alpha",
                    source_category_id="loc_1",
                    customer_count=1,
                    last_synced_at=datetime(2026, 3, 10, 1, 0, 0),
                )
            )
            session.add(
                DeliveryCustomer(
                    customer_id="cust_1",
                    name="Shop One",
                    customer_code="S1",
                    phone="081",
                    primary_location_id="loc_1",
                    last_synced_at=datetime(2026, 3, 10, 1, 0, 0),
                )
            )
            session.add(
                DeliveryUser(
                    id="user-1",
                    line_user_id="line-user-1",
                    display_name="Driver One",
                    picture_url=None,
                    status="active",
                    access_mode="all",
                    created_at=datetime(2026, 3, 10, 1, 0, 0),
                    last_login_at=datetime(2026, 3, 10, 2, 0, 0),
                )
            )
            session.add(
                VisitReport(
                    id="report-1",
                    client_submission_id="submission-1",
                    line_user_id="line-user-1",
                    customer_id="cust_1",
                    location_id="loc_1",
                    photo_object_key="reports/2026/03/10/cust_1/photo.jpg",
                    photo_url="https://delivery.example.com/api/photos/reports/2026/03/10/cust_1/photo.jpg",
                    latitude=13.7563,
                    longitude=100.5018,
                    accuracy_m=8.0,
                    captured_at_client=datetime(2026, 3, 10, 2, 3, 4),
                    received_at_server=datetime(2026, 3, 10, 2, 3, 10),
                )
            )
            session.commit()
        finally:
            session.close()

    def test_import_reports_from_sqlite_moves_records(self):
        result = import_reports_from_sqlite(self.source_db_path, self.destination_db_url)
        self.assertEqual(result["reports_imported"], 1)
        self.assertEqual(result["reports_skipped"], 0)
        self.assertEqual(result["users_imported"], 1)
        self.assertEqual(result["customers_imported"], 1)
        self.assertEqual(result["locations_imported"], 1)

        session: Session = self.destination_session_factory()
        try:
            self.assertEqual(session.query(DeliveryLocation).count(), 1)
            self.assertEqual(session.query(DeliveryCustomer).count(), 1)
            self.assertEqual(session.query(DeliveryUser).count(), 1)
            self.assertEqual(session.query(VisitReport).count(), 1)
            report = session.query(VisitReport).one()
            self.assertEqual(report.client_submission_id, "submission-1")
            self.assertEqual(report.photo_object_key, "reports/2026/03/10/cust_1/photo.jpg")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
