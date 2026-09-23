import unittest

from ai_agent import ai_decide_workflow, ai_generate_test_cases, extract_json, validate_user_story


class DummyGroqClient:
    class chat:
        class completions:
            @staticmethod
            def create(*args, **kwargs):
                raise RuntimeError("Should not be called")


class TestAiAgent(unittest.TestCase):
    def test_validate_user_story_rejects_invalid(self):
        valid, reason = validate_user_story("placeholder story needs details")
        self.assertFalse(valid)
        self.assertIn("placeholder", reason.lower())

    def test_validate_user_story_accepts_valid(self):
        story = "As a sales rep I want to create a lead so that I can track new customers."
        valid, reason = validate_user_story(story)
        self.assertTrue(valid)
        self.assertEqual(reason, "Valid")

    def test_extract_json_object_in_text(self):
        payload = 'Response:\n{"workflow":"create_lead","entity":"lead","test_data":{}}'
        result = extract_json(payload)
        self.assertEqual(result["workflow"], "create_lead")

    def test_extract_json_array_in_text(self):
        payload = 'Result:\n[{"action":"click"}]'
        result = extract_json(payload)
        self.assertEqual(result[0]["action"], "click")

    def test_ai_generate_test_cases_skips_invalid_story(self):
        dummy = DummyGroqClient()
        result = ai_generate_test_cases(dummy, "todo")
        self.assertTrue(result.startswith("SKIPPED - "))

    def test_ai_decide_workflow_skips_invalid_story(self):
        dummy = DummyGroqClient()
        result = ai_decide_workflow(dummy, "placeholder")
        self.assertEqual(result["workflow"], "skip")
        self.assertEqual(result["entity"], "none")
        self.assertIn("skip_reason", result)
