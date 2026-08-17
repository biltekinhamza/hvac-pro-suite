from __future__ import annotations

from pathlib import Path
import gc
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.main as main_module
import app.mobile.repository as mobile_repository_module
import app.repository as repository_module
from app.config import settings
from app.database import Database


class MobileApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "mobile.sqlite3")
        self.patches = [
            patch.object(main_module, "db", self.database),
            patch.object(repository_module, "db", self.database),
            patch.object(mobile_repository_module, "db", self.database),
        ]
        for item in self.patches:
            item.start()
        self.old_settings = (settings.app_env, settings.mobile_activation_code, settings.mobile_tenant_id, settings.company_name)
        settings.app_env = "test"
        settings.mobile_activation_code = "test-activation"
        settings.mobile_tenant_id = "tenant-a"
        settings.company_name = "Test HVAC"
        self.client_context = TestClient(main_module.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        settings.app_env, settings.mobile_activation_code, settings.mobile_tenant_id, settings.company_name = self.old_settings
        for item in reversed(self.patches):
            item.stop()
        gc.collect()
        self.temp_dir.cleanup()

    def activate(self) -> str:
        response = self.client.post("/api/v1/activate", json={
            "activation_code": "test-activation",
            "device_id": "android-1",
            "device_name": "Test phone",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["tenant_id"], "tenant-a")
        return response.json()["token"]

    def test_activation_stores_only_hash_and_catalog_requires_bearer(self) -> None:
        token = self.activate()

        with self.database.connect() as conn:
            saved = conn.execute("SELECT token_hash FROM mobile_device").fetchone()["token_hash"]
        self.assertNotEqual(saved, token)
        self.assertEqual(len(saved), 64)
        self.assertEqual(self.client.get("/api/v1/catalog").status_code, 401)
        catalog = self.client.get("/api/v1/catalog", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(catalog.status_code, 200)
        self.assertTrue(any(item["code"] == "kare_kapak" for item in catalog.json()["parts"]))

    def test_submit_quote_is_idempotent_and_uses_real_quote_tables(self) -> None:
        token = self.activate()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "operation_id": "77777777-7777-4777-8777-777777777777",
            "type": "submit_quote",
            "draft": {
                "local_id": "draft-1",
                "customer_name": "Mobil Musteri",
                "customer_phone": "+90 555 123 45 67",
                "profit_rate": 20,
                "shipping_amount": 50,
                "items": [{
                    "part_code": "kare_kapak",
                    "quantity": 2,
                    "inputs": {"en": 50, "boy": 40, "sac_kalinlik_mm": "0.60"},
                }],
            },
        }

        first = self.client.post("/api/v1/operations", headers=headers, json=payload)
        second = self.client.post("/api/v1/operations", headers=headers, json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["quote_id"], second.json()["quote_id"])
        self.assertFalse(first.json()["replayed"])
        self.assertTrue(second.json()["replayed"])
        with self.database.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM quote").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT customer_phone FROM quote").fetchone()[0], "+90 555 123 45 67")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM quote_item").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT status FROM cart").fetchone()[0], "converted")

        payload["draft"]["customer_name"] = "Baska Musteri"
        conflict = self.client.post("/api/v1/operations", headers=headers, json=payload)
        self.assertEqual(conflict.status_code, 409)

    def test_production_rejects_plain_http(self) -> None:
        settings.app_env = "production"
        response = self.client.post("/api/v1/activate", json={
            "activation_code": "test-activation", "device_id": "android-2", "device_name": "phone"
        })
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
