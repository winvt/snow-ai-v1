import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

from delivery_app.db import DeliveryCustomer, DeliveryLocation, create_db_engine, create_session_factory, init_db
from delivery_app.metadata import sync_delivery_customers_from_api_payload
from delivery_app.repository import UNASSIGNED_LOCATION_ID
from scripts.sync_delivery_metadata import sync_delivery_metadata


SCHEMA_SQL = """
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT,
    customer_code TEXT,
    phone TEXT
);
CREATE TABLE receipts (
    receipt_id TEXT PRIMARY KEY,
    customer_id TEXT,
    receipt_date TEXT,
    created_at TEXT
);
CREATE TABLE line_items (
    line_item_id TEXT PRIMARY KEY,
    receipt_id TEXT,
    item_id TEXT
);
CREATE TABLE items (
    item_id TEXT PRIMARY KEY,
    category_id TEXT
);
CREATE TABLE categories (
    category_id TEXT PRIMARY KEY,
    name TEXT
);
"""


class DeliverySyncTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.source_path = Path(self.tmpdir.name) / "source.db"
        self.target_path = Path(self.tmpdir.name) / "target.db"

        conn = sqlite3.connect(self.source_path)
        conn.executescript(SCHEMA_SQL)
        conn.executescript(
            """
            INSERT INTO categories(category_id, name) VALUES
                ('loc_a', 'Alpha'),
                ('loc_b', 'Beta');
            INSERT INTO items(item_id, category_id) VALUES
                ('item_a', 'loc_a'),
                ('item_b', 'loc_b');
            INSERT INTO customers(customer_id, name, customer_code, phone) VALUES
                ('cust_1', 'Customer One', 'C1', '081'),
                ('cust_2', 'Customer Two', 'C2', '082'),
                ('cust_3', 'Customer Three', 'C3', '083');
            INSERT INTO receipts(receipt_id, customer_id, receipt_date, created_at) VALUES
                ('r1', 'cust_1', '2026-03-01T01:00:00', '2026-03-01T01:00:00'),
                ('r2', 'cust_1', '2026-03-02T01:00:00', '2026-03-02T01:00:00'),
                ('r3', 'cust_1', '2026-03-03T01:00:00', '2026-03-03T01:00:00'),
                ('r4', 'cust_2', '2026-03-03T01:00:00', '2026-03-03T01:00:00'),
                ('r5', 'cust_2', '2026-03-04T01:00:00', '2026-03-04T01:00:00'),
                ('r6', 'cust_2', '2026-03-05T01:00:00', '2026-03-05T01:00:00');
            INSERT INTO line_items(line_item_id, receipt_id, item_id) VALUES
                ('l1', 'r1', 'item_a'),
                ('l2', 'r2', 'item_b'),
                ('l3', 'r3', 'item_b'),
                ('l4', 'r4', 'item_a'),
                ('l5', 'r5', 'item_b'),
                ('l6', 'r6', 'item_a');
            """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_sync_assigns_primary_locations_and_unassigned_bucket(self):
        result = sync_delivery_metadata(str(self.source_path), f"sqlite:///{self.target_path}")
        self.assertEqual(result["customers"], 3)
        self.assertEqual(result["locations"], 3)
        self.assertEqual(result["unassigned_customers"], 1)

        engine = create_db_engine(f"sqlite:///{self.target_path}")
        session = create_session_factory(engine)()
        try:
            customers = {
                row.customer_id: row
                for row in session.execute(select(DeliveryCustomer)).scalars()
            }
            locations = {
                row.id: row
                for row in session.execute(select(DeliveryLocation)).scalars()
            }
            self.assertEqual(customers["cust_1"].primary_location_id, "loc_b")
            self.assertEqual(customers["cust_2"].primary_location_id, "loc_a")
            self.assertEqual(customers["cust_3"].primary_location_id, UNASSIGNED_LOCATION_ID)
            self.assertEqual(locations["loc_a"].customer_count, 1)
            self.assertEqual(locations["loc_b"].customer_count, 1)
            self.assertEqual(locations[UNASSIGNED_LOCATION_ID].customer_count, 1)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()


class DeliveryCustomerApiSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.target_path = Path(self.tmpdir.name) / "delivery.db"
        engine = create_db_engine(f"sqlite:///{self.target_path}")
        init_db(engine)
        self.session = create_session_factory(engine)()
        self.session.add(DeliveryLocation(id="loc_a", name="Alpha", source_category_id="loc_a", customer_count=1))
        self.session.add(
            DeliveryCustomer(
                customer_id="cust_1",
                name="Old Name",
                customer_code="OLD",
                phone="080",
                primary_location_id="loc_a",
            )
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.tmpdir.cleanup()

    def test_api_sync_preserves_existing_location_and_adds_new_customers_as_unassigned(self):
        result = sync_delivery_customers_from_api_payload(
            self.session,
            [
                {"id": "cust_1", "name": "Fresh Name", "customer_code": "C1", "phone": "081"},
                {"id": "cust_2", "name": "Brand New", "customer_code": "C2", "phone": "082"},
                {"name": "Missing Id"},
            ],
        )

        customers = {
            row.customer_id: row
            for row in self.session.execute(select(DeliveryCustomer)).scalars()
        }
        locations = {
            row.id: row
            for row in self.session.execute(select(DeliveryLocation)).scalars()
        }

        self.assertEqual(result["customers"], 2)
        self.assertEqual(result["new_customers"], 1)
        self.assertEqual(result["updated_customers"], 1)
        self.assertEqual(result["unchanged_customers"], 0)
        self.assertEqual(result["skipped_customers"], 1)
        self.assertEqual(customers["cust_1"].primary_location_id, "loc_a")
        self.assertEqual(customers["cust_1"].name, "Fresh Name")
        self.assertEqual(customers["cust_2"].primary_location_id, UNASSIGNED_LOCATION_ID)
        self.assertEqual(locations["loc_a"].customer_count, 1)
        self.assertEqual(locations[UNASSIGNED_LOCATION_ID].customer_count, 1)
