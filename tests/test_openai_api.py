import os
import unittest
from unittest.mock import MagicMock, patch

from backend.app import create_app
from backend.services import openai_api, threat_knowledge


class OpenAIProviderTests(unittest.TestCase):
    @patch.dict(os.environ, {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "test-placeholder"})
    @patch("backend.services.openai_api.post")
    def test_answers_and_stores_history_with_active_provider(self, post):
        post.return_value = {"choices": [{"message": {"content": "The answer."}}]}
        db = MagicMock()
        db.ai_messages.find.return_value.sort.return_value.limit.return_value = []
        with patch("backend.route.ai.get_db", return_value=db):
            client = create_app().test_client()
            self.assertEqual(client.get("/api/ai/status").json["provider"], "OPENAI")
            response = client.post("/api/ai/chat", json={"message": "What is MongoDB?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["answer"], "The answer.")
        self.assertEqual(response.json["provider"], "openai")
        self.assertEqual(post.call_args.args[0], "chat/completions")
        saved = db.ai_messages.insert_many.call_args.args[0]
        self.assertEqual([row["provider"] for row in saved], ["openai", "openai"])

    @patch.dict(os.environ, {"AI_PROVIDER": "openai"})
    @patch("backend.services.openai_api.post")
    def test_embedding_backend_restores_input_order(self, post):
        post.return_value = {"data": [{"index": 1, "embedding": [0, 1]},
                                      {"index": 0, "embedding": [1, 0]}]}
        self.assertEqual(threat_knowledge.embed(["one", "two"]), [[1, 0], [0, 1]])
        self.assertEqual(post.call_args.args[0], "embeddings")
        self.assertEqual(post.call_args.args[1]["model"], openai_api.embedding_model())

    @patch.dict(os.environ, {"AI_PROVIDER": "openai", "OPENAI_API_KEY": ""})
    def test_missing_key_has_clear_error(self):
        client = create_app().test_client()
        self.assertFalse(client.get("/api/ai/status").json["configured"])
        self.assertEqual(client.post("/api/ai/chat", json={"message": "Hello"}).status_code, 503)
