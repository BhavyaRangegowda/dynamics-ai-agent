import os
import unittest

import config
from config import ConfigError, validate_environment


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.original_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_validate_environment_raises_on_missing_keys(self):
        for key in config._required_keys:
            os.environ.pop(key, None)

        with self.assertRaises(ConfigError) as context:
            validate_environment()

        self.assertIn("Missing required environment variables", str(context.exception))
        for key in config._required_keys:
            self.assertIn(key, str(context.exception))

    def test_validate_environment_passes_when_all_present(self):
        for key in config._required_keys:
            os.environ[key] = "value"

        self.assertTrue(validate_environment())
