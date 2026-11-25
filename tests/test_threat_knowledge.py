import unittest
from unittest.mock import MagicMock, patch

from backend.app import create_app

SOURCE = {
    "title": "Containment",
    "text": "Preserve evidence and isolate the affected endpoint.",
    "url": "https://www.cisa.gov/stopransomware/ransomware-guide",
    "platform": "Windows",
    "stage": "Active",
    "embedding": [1, 0],
}


class ThreatChatTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.db = MagicMock()
        self.db.ai_messages.find.return_value.sort.return_value.limit.return_value = []
        self.query = self.db.threat_knowledge.find
        self.rows = self.query.return_value.sort.return_value.limit

    def test_rejects_unsupported_scope(self):
        response = self.client.post("/api/ai/chat", json={
            "message": "What should I do?", "platform": "Android", "threat_stage": "Active",
        })
        self.assertEqual(response.status_code, 400)

    @patch("backend.route.ai._installed_models", return_value=["qwen2.5:3b"])
    @patch("backend.route.ai._generate", return_value="Preserve evidence [1].")
    @patch("backend.services.threat_knowledge.embed", return_value=[[1, 0]])
    def test_ranks_sources_and_passes_only_relevant_context(self, embed, generate, models):
        self.rows.return_value = [dict(SOURCE, title="Unrelated", embedding=[0, 1]), SOURCE]
        with patch("backend.route.ai.get_db", return_value=self.db):
            response = self.client.post("/api/ai/chat", json={
                "message": "How should I contain ransomware?",
                "platform": "Windows",
                "threat_stage": "Active",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.query.call_args.args[0]["platform"], "Windows")
        self.assertEqual(self.query.call_args.args[0]["stage"], "Active")
        self.assertEqual([row["title"] for row in response.json["sources"]], ["Containment"])
        self.assertNotIn("embedding", response.json["sources"][0])
        self.assertIn(SOURCE["text"], generate.call_args.args[0][-1]["content"])
        self.db.ai_messages.insert_many.assert_called_once()

    @patch("backend.route.ai._installed_models", return_value=["qwen2.5:3b"])
    @patch("backend.route.ai._generate")
    def test_empty_catalog_does_not_generate_an_ungrounded_answer(self, generate, models):
        self.rows.return_value = []
        with patch("backend.route.ai.get_db", return_value=self.db):
            response = self.client.post("/api/ai/chat", json={
                "message": "What should I do?", "platform": "Linux", "threat_stage": "Evolving",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["sources"], [])
        generate.assert_not_called()
