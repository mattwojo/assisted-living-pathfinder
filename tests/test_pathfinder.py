"""API coverage for listing, search, trust labels, and follow-up questions."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="pathfinder-"))
os.environ["PATHFINDER_DB"] = str(ROOT / "test.db")
os.environ["PATHFINDER_UPLOADS"] = str(ROOT / "uploads")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402
from backend.app.routes.facilities import sniff_image  # noqa: E402
from backend.app.seed import solid_png  # noqa: E402


class PathfinderApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def login(self, email: str) -> dict:
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "pathfinder"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def auth(self, email: str) -> dict[str, str]:
        token = self.login(email)["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")

    def test_memory_care_search_explains_matches(self):
        response = self.client.post(
            "/api/search",
            json={"query": "Find a memory care facility near Bothell under $6,000 per month with high staff ratios."},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["interpreted"]["care_levels"], ["memory_care"])
        self.assertEqual(body["interpreted"]["city"], "Bothell")
        self.assertEqual(body["interpreted"]["city_mode"], "near")
        self.assertEqual(body["interpreted"]["max_budget"], 6000)
        self.assertTrue(body["interpreted"]["wants_high_staff"])
        names = [item["facility"]["name"] for item in body["matches"]]
        self.assertIn("Cedar & Birch Memory Care", names)
        self.assertIn("Mill Creek Haven", names)
        self.assertNotIn("Evergreen House Memory Care", names)
        cedar = next(item for item in body["matches"] if item["facility"]["name"].startswith("Cedar"))
        self.assertTrue(any("5,400" in reason or "5400" in reason for reason in cedar["matched"]))
        self.assertTrue(any("Staff ratio" in reason for reason in cedar["matched"]))
        close_names = [item["facility"]["name"] for item in body["close"]]
        self.assertIn("Northshore Gardens", close_names)
        self.assertTrue(body["agent_logs"])

    def test_listing_requires_a_representative(self):
        denied = self.client.post("/api/facilities", json={"name": "Quiet Oaks"})
        self.assertEqual(denied.status_code, 401)
        family = self.client.post(
            "/api/facilities",
            json={"name": "Quiet Oaks", "city": "Olympia", "state": "WA"},
            headers=self.auth("family@example.com"),
        )
        self.assertEqual(family.status_code, 403)

    def test_representative_can_publish_and_family_cannot_edit(self):
        created = self.client.post(
            "/api/facilities",
            headers=self.auth("rep@example.com"),
            json={
                "name": "Quiet Oaks",
                "description": "A sample assisted living apartment community in Olympia with meals and a garden.",
                "city": "Olympia",
                "state": "WA",
                "postal_code": "98501",
                "care_levels": ["assisted_living"],
                "license_number": "WA-AL-10001",
                "license_state": "WA",
                "beds_available": 2,
                "pricing_tiers": [
                    {
                        "name": "Assisted living studio",
                        "care_level": "assisted_living",
                        "monthly_min": 4000,
                        "monthly_max": 4800,
                        "includes": "meals",
                    }
                ],
                "submit": True,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        facility = created.json()["facility"]
        self.assertEqual(facility["validation"]["status"], "pending_review")
        self.assertTrue(facility["facts"])
        self.assertTrue(any(fact["source_label"] == "Provided by the community" for fact in facility["facts"]))

        family_edit = self.client.put(
            f"/api/facilities/{facility['id']}",
            headers=self.auth("family@example.com"),
            json={"name": "Quiet Oaks", "city": "Olympia"},
        )
        self.assertEqual(family_edit.status_code, 403)

        found = self.client.post("/api/search", json={"query": "assisted living in Olympia"})
        self.assertIn("Quiet Oaks", [item["facility"]["name"] for item in found.json()["matches"]])

    def test_conflict_is_visible_and_question_cites_sources(self):
        listing = self.client.get("/api/facilities")
        search = self.client.post("/api/search", json={"query": "memory care in Edmonds"})
        harbor = next(item["facility"] for item in search.json()["matches"] if "Harbor Lights" in item["facility"]["name"])
        self.assertEqual(harbor["validation"]["status"], "conflict")
        self.assertTrue(harbor["validation"]["flags"])

        answer = self.client.post(
            f"/api/facilities/{harbor['id']}/questions",
            json={"question": "What does this community charge each month?"},
        )
        self.assertEqual(answer.status_code, 200, answer.text)
        body = answer.json()
        self.assertIn("not legal, medical, or financial advice", body["disclaimer"].lower())
        self.assertTrue(body["citations"])
        self.assertTrue(any(item["source_type"] == "external" or item["source_type"] == "facility_provided" for item in body["citations"]))
        self.assertTrue(body["uncertainty"])
        self.assertEqual(listing.status_code, 404)

        external = next(fact for fact in harbor["facts"] if fact["source_type"] == "external")
        reviewed = self.client.post(
            f"/api/facts/{external['id']}/set-aside",
            headers=self.auth("admin@example.com"),
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["facility"]["validation"]["status"], "pending_review")
        self.assertFalse(
            any(flag["severity"] == "conflict" for flag in reviewed.json()["facility"]["validation"]["flags"])
        )

    def test_photo_upload_rejects_non_images_and_accepts_png(self):
        search = self.client.post("/api/search", json={"query": "Cedar & Birch"})
        cedar = next(item["facility"] for item in search.json()["matches"] if item["facility"]["name"].startswith("Cedar"))
        headers = self.auth("rep@example.com")
        rejected = self.client.post(
            f"/api/facilities/{cedar['id']}/photos",
            headers=headers,
            files={"file": ("notes.txt", b"not a photo", "text/plain")},
            data={"caption": "nope"},
        )
        self.assertEqual(rejected.status_code, 400)
        accepted = self.client.post(
            f"/api/facilities/{cedar['id']}/photos",
            headers=headers,
            files={"file": ("court.png", solid_png(40, 30, (20, 80, 60)), "image/png")},
            data={"caption": "Courtyard path"},
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        photo = accepted.json()["photo"]
        downloaded = self.client.get(photo["url"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(sniff_image(downloaded.content), "image/png")


if __name__ == "__main__":
    unittest.main()
