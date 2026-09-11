import unittest

from server.mia_tools.normalize import normalize_audits, normalize_projects


class NormalizeTest(unittest.TestCase):
    def test_projects_keep_business_fields_and_bound_nested_lists(self):
        raw = [{
            "id": "p1", "name": "Proyecto", "domain": "example.test",
            "type": "web", "status": "active", "description": "D" * 9000,
            "recommendations": [{"title": "A", "status": "todo", "extra": "x"}] * 30,
            "notes": "N" * 9000, "created_at": "2026-01-01", "updated_at": "2026-01-02",
            "secret": "must not pass",
        }]
        result = normalize_projects(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "p1")
        self.assertLessEqual(len(result[0]["description"]), 2000)
        self.assertLessEqual(len(result[0]["recommendations"]), 10)
        self.assertEqual(set(result[0]), {"id", "name", "domain", "type", "status", "description", "recommendations", "created_at", "updated_at"})
        self.assertNotIn("secret", result[0])

    def test_audits_omit_full_report_and_bound_lists(self):
        raw = [{
            "id": "a1", "client_id": "c1", "url": "https://example.test",
            "status": "done", "summary": "S" * 9000, "tech_stack": ["wp"] * 30,
            "seo_score": "88", "recommendations": ["R"] * 30,
            "full_report": {"secret": "private"}, "created_at": "2026-01-01",
            "plan_json": {"private": "data"}, "presentation_json": {"private": "data"},
        }]
        result = normalize_audits(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "a1")
        self.assertNotIn("full_report", result[0])
        self.assertNotIn("plan_json", result[0])
        self.assertNotIn("presentation_json", result[0])
        self.assertLessEqual(len(result[0]["recommendations"]), 10)
        self.assertLessEqual(len(result[0]["tech_stack"]), 10)

    def test_empty_lists_are_valid_and_non_lists_are_rejected(self):
        self.assertEqual(normalize_projects([]), [])
        self.assertEqual(normalize_audits([]), [])
        with self.assertRaises(ValueError):
            normalize_projects({"projects": []})
        with self.assertRaises(ValueError):
            normalize_audits("invalid")


if __name__ == "__main__":
    unittest.main()
