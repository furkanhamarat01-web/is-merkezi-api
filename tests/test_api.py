import os
import tempfile
import unittest


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["IS_MERKEZI_HOME"] = cls.tmp.name
        os.environ["API_TOKEN"] = "test-token"
        os.environ.pop("CORS_ORIGINS", None)
        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)
        cls.headers = {"Authorization": "Bearer test-token"}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.tmp.cleanup()

    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_api_requires_token(self):
        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 401)

    def test_task_project_invoice_and_talep(self):
        project = self.client.post("/api/projects", headers=self.headers, json={"name": "Sunucu"}).json()
        self.assertEqual(project["proj_key"], "SUNU")

        task = self.client.post(
            "/api/tasks",
            headers=self.headers,
            json={"title": "Disk alarmı", "project_id": project["id"], "priority": "Yüksek"},
        )
        self.assertEqual(task.status_code, 201, task.text)
        body = task.json()
        self.assertEqual(body["issue_key"], "SUNU-1")
        self.assertEqual(body["status"], "Bekliyor")

        moved = self.client.patch(
            f"/api/tasks/{body['id']}",
            headers=self.headers,
            json={"status": "Devam ediyor"},
        )
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["status"], "Devam ediyor")

        invoice = self.client.post(
            "/api/invoices",
            headers=self.headers,
            json={"party": "Anadolu", "amount": 100, "invoice_no": "A-1"},
        )
        self.assertEqual(invoice.status_code, 201, invoice.text)
        invoice_id = invoice.json()["id"]
        partial = self.client.post(f"/api/invoices/{invoice_id}/payments", headers=self.headers, json={"amount": 40})
        self.assertEqual(partial.status_code, 200, partial.text)
        self.assertEqual(partial.json()["status"], "Kısmi ödendi")
        self.assertEqual(partial.json()["remaining"], 60)
        done = self.client.post(f"/api/invoices/{invoice_id}/payments", headers=self.headers, json={"amount": 60})
        self.assertEqual(done.json()["status"], "Ödendi")
        self.assertEqual(done.json()["remaining"], 0)
        too_much = self.client.post(f"/api/invoices/{invoice_id}/payments", headers=self.headers, json={"amount": 1})
        self.assertEqual(too_much.status_code, 400)

        talep = self.client.post(
            "/api/talepler",
            headers=self.headers,
            json={"title": "Yazıcı", "target_code": "BT", "target_name": "Bilgi İşlem"},
        )
        self.assertEqual(talep.status_code, 201, talep.text)
        self.assertEqual(talep.json()["number"], "BT-1")
        taken = self.client.post(
            f"/api/talepler/{talep.json()['id']}/take",
            headers=self.headers,
            json={"actor_id": 7, "actor_name": "Furkan"},
        )
        self.assertEqual(taken.status_code, 200, taken.text)
        self.assertEqual(taken.json()["status"], "Üzerinde")
        self.assertEqual(taken.json()["assignee_name"], "Furkan")

        board = self.client.get("/api/dashboard", headers=self.headers)
        self.assertEqual(board.status_code, 200)
        self.assertGreaterEqual(board.json()["open_invoices"], 0)

        setting = self.client.put("/api/settings/board_project", headers=self.headers, json={"value": "1"})
        self.assertEqual(setting.status_code, 200)
        read = self.client.get("/api/settings/board_project", headers=self.headers)
        self.assertEqual(read.json()["value"], "1")

        other = self.client.get("/api/tasks", headers={**self.headers, "X-Owner-Id": "99"})
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.json()["count"], 0)

    def test_store_keeps_partial_updates(self):
        denied = self.client.get("/api/store/tasks")
        self.assertEqual(denied.status_code, 401)
        created = self.client.post("/api/store/tasks", headers=self.headers, json={"title": "Kapı", "status": "Bekliyor"})
        self.assertEqual(created.status_code, 201, created.text)
        row_id = created.json()["id"]
        patched = self.client.patch(
            f"/api/store/tasks/{row_id}",
            headers=self.headers,
            json={"sla_next": "2026-11-16 10:00:00"},
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        self.assertEqual(patched.json()["title"], "Kapı")
        self.assertEqual(patched.json()["sla_next"], "2026-11-16 10:00:00")
        self.client.post("/api/store/workspace", headers=self.headers)
        projects = self.client.get("/api/store/projects", headers=self.headers).json()["items"]
        self.assertTrue(any(item["proj_key"] == "GEN" for item in projects))
        missing = self.client.get("/api/store/talepler/number", headers=self.headers, params={"number": "yok-0"})
        self.assertEqual(missing.status_code, 200)
        self.assertIsNone(missing.json())


if __name__ == "__main__":
    unittest.main()
