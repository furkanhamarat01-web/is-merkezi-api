import base64
import os
import tempfile
import unittest

from app.talep.logic import ADMIN_EMAIL, ADMIN_ROLE, new_totp_secret, totp_codes


class TalepApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["API_TOKEN"] = "test-token"
        os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(cls.tmp.name, "talep.db")
        os.environ.pop("CORS_ORIGINS", None)
        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)
        cls.headers = {"Authorization": "Bearer test-token"}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.tmp.cleanup()

    def test_accounts_teams_and_requests(self):
        secret = new_totp_secret()
        created = self.client.post("/api/talep/users", headers=self.headers, json={
            "name": "Yonetici", "email": ADMIN_EMAIL, "password": "parola1", "secret": secret, "is_admin": True,
        })
        self.assertEqual(created.status_code, 201, created.text)
        denied = self.client.post("/api/talep/users", headers=self.headers, json={
            "name": "Baska", "email": "baska@firma.com", "password": "parola3",
            "secret": new_totp_secret(), "is_admin": True, "role": "Kullanıcı",
        })
        self.assertEqual(denied.status_code, 400)
        missing_role = self.client.post("/api/talep/users", headers=self.headers, json={
            "name": "Rolsuz", "email": "rolsuz@firma.com", "password": "parola3", "secret": new_totp_secret(),
        })
        self.assertEqual(missing_role.status_code, 400)

        other_secret = new_totp_secret()
        other = self.client.post("/api/talep/users", headers=self.headers, json={
            "name": "Ali", "email": "ali@firma.com", "password": "parola2",
            "secret": other_secret, "username": "ali", "role": "Sorumlu",
        })
        self.assertEqual(other.status_code, 201, other.text)
        admin = self.client.get("/api/talep/users/by-email", headers=self.headers, params={"email": ADMIN_EMAIL}).json()
        ali = self.client.get("/api/talep/users/by-email", headers=self.headers, params={"email": "ali@firma.com"}).json()
        self.assertNotIn("password", admin)
        self.assertEqual(admin["is_admin"], 1)
        self.assertEqual(admin["role"], ADMIN_ROLE)
        self.assertEqual(ali["must_change"], 1)
        self.assertEqual(ali["role"], "Sorumlu")

        saha = self.client.post("/api/talep/teams", headers=self.headers, json={"name": "Saha", "code": "SAHA"}).json()["id"]
        satin = self.client.post("/api/talep/teams", headers=self.headers, json={"name": "Satın alma", "code": "SATIN"}).json()["id"]
        self.client.post("/api/talep/members", headers=self.headers, json={"user_id": admin["id"], "team_id": saha})
        self.client.post("/api/talep/members", headers=self.headers, json={"user_id": ali["id"], "team_id": satin})
        edited = self.client.patch(f"/api/talep/teams/{saha}", headers=self.headers, json={
            "name": "Saha ekibi", "topic": "Saha işleri", "code": "SAHA",
        })
        self.assertEqual(edited.status_code, 200, edited.text)
        self.client.patch(f"/api/talep/users/{ali['id']}", headers=self.headers, json={
            "name": "Ali", "email": "ali@firma.com", "username": "ali", "team_id": satin, "role": "İzleyici",
        })
        ali = self.client.get("/api/talep/users/by-email", headers=self.headers, params={"email": "ali@firma.com"}).json()
        self.assertEqual(ali["role"], "İzleyici")

        code = self.client.post("/api/talep/request-codes", headers=self.headers, json={
            "code": "BT-03", "team_id": saha, "work_code": "BT-KURULUM", "title": "Bilgisayar kurulumu",
        })
        self.assertEqual(code.status_code, 201, code.text)
        shared = self.client.post("/api/talep/request-codes", headers=self.headers, json={
            "code": "ORTAK-1", "team_id": satin, "work_code": "ORTAK", "title": "Ortak iş", "all_teams": True,
        })
        self.assertEqual(shared.status_code, 201, shared.text)
        codes = self.client.get("/api/talep/request-codes", headers=self.headers).json()
        ortak = next(item for item in codes if item["code"] == "ORTAK-1")
        self.assertEqual(ortak["all_teams"], 1)
        self.assertEqual(ortak["team_code"], "SATIN")

        self.client.post(f"/api/talep/users/{ali['id']}/password", headers=self.headers, json={"password": "yeni-parola"})
        signed = self.client.post("/api/talep/login", headers=self.headers, json={
            "email": ADMIN_EMAIL, "password": "parola1", "code": totp_codes(secret, window=0)[0],
        }).json()["user"]
        self.assertEqual(signed["email"], ADMIN_EMAIL)
        self.assertIsNone(self.client.post("/api/talep/login", headers=self.headers, json={
            "email": ADMIN_EMAIL, "password": "parola1", "code": "000000",
        }).json()["user"])

        internal = self.client.post("/api/talep/requests", headers=self.headers, json={
            "author_id": admin["id"], "team_id": saha, "target_team_id": saha,
            "work_code": "IS-1", "title": "Saha isi", "description": "detay", "priority": "Normal",
        })
        self.assertEqual(internal.status_code, 201, internal.text)
        self.assertEqual(internal.json()["number"], "SAHA-1")
        outgoing = self.client.post("/api/talep/requests", headers=self.headers, json={
            "author_id": admin["id"], "team_id": saha, "target_team_id": satin,
            "work_code": "IS-2", "title": "Malzeme", "description": "detay", "priority": "Yüksek", "due_date": "2026-12-01",
        }).json()
        self.assertEqual(outgoing["number"], "SATIN-1")
        pending = {row["number"] for row in self.client.get("/api/talep/requests/pending-vkv", headers=self.headers).json()}
        self.assertEqual(pending, {"SAHA-1", "SATIN-1"})
        self.client.post(f"/api/talep/requests/{internal.json()['id']}/vkv", headers=self.headers, json={"task_id": 3, "issue_key": "SAHA-1"})
        pending = {row["number"] for row in self.client.get("/api/talep/requests/pending-vkv", headers=self.headers).json()}
        self.assertEqual(pending, {"SATIN-1"})
        held = self.client.post(
            f"/api/talep/requests/{internal.json()['id']}/status",
            headers=self.headers,
            json={"status": "Beklemede", "note": ""},
        )
        self.assertEqual(held.status_code, 400)
        saved = self.client.post(
            f"/api/talep/requests/{internal.json()['id']}/status",
            headers=self.headers,
            json={"status": "Beklemede", "note": "parça bekleniyor"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        row = self.client.get(f"/api/talep/requests/{internal.json()['id']}", headers=self.headers).json()
        self.assertEqual(row["status"], "Beklemede")
        uploaded = self.client.post(
            f"/api/talep/requests/{internal.json()['id']}/file",
            headers=self.headers,
            json={"name": "not.pdf", "data": base64.b64encode(b"%PDF-1.4").decode()},
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        self.assertEqual(uploaded.json()["file_path"], "not.pdf")
        downloaded = self.client.get(f"/api/talep/requests/{internal.json()['id']}/file", headers=self.headers)
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(downloaded.content, b"%PDF-1.4")
        ali_numbers = {
            item["number"]
            for item in self.client.get("/api/talep/requests", headers=self.headers, params={"user_id": ali["id"]}).json()
        }
        self.assertEqual(ali_numbers, {"SATIN-1"})
        admin_numbers = {
            item["number"]
            for item in self.client.get("/api/talep/requests", headers=self.headers, params={"user_id": admin["id"]}).json()
        }
        self.assertEqual(admin_numbers, {"SAHA-1", "SATIN-1"})
        signed_name = self.client.post("/api/talep/session", headers=self.headers, json={
            "username": "ali", "password": "yeni-parola",
        })
        self.assertEqual(signed_name.status_code, 200, signed_name.text)
        self.assertEqual(signed_name.json()["user"]["role"], "İzleyici")
        self.assertIn("İş takibi", signed_name.json()["user"]["screens"])
        self.assertNotIn("Kullanıcılar", signed_name.json()["user"]["screens"])
        forgot = self.client.post("/api/talep/forgot", headers=self.headers, json={"username": "ali"})
        self.assertEqual(forgot.status_code, 200, forgot.text)
        pending = self.client.get("/api/talep/resets", headers=self.headers).json()
        self.assertEqual(pending[0]["username"], "ali")
        granted = self.client.post(
            f"/api/talep/resets/{pending[0]['id']}/password",
            headers=self.headers,
            json={"password": "gecici1"},
        )
        self.assertEqual(granted.status_code, 200, granted.text)
        again = self.client.post("/api/talep/session", headers=self.headers, json={
            "username": "ali", "password": "gecici1",
        }).json()["user"]
        self.assertTrue(again["must_change"])


if __name__ == "__main__":
    unittest.main()
