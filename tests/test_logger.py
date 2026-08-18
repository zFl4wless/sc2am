import logging
import sys
import tempfile
import unittest
from pathlib import Path

from sc2am.logger import setup_logging


class LoggerSetupTests(unittest.TestCase):
    def test_console_handler_uses_stderr_and_warning_floor(self):
        logger = setup_logging("INFO", None)

        self.assertFalse(logger.propagate)
        self.assertEqual(len(logger.handlers), 1)

        console_handler = logger.handlers[0]
        self.assertIs(console_handler.stream, sys.stderr)
        self.assertEqual(console_handler.level, logging.WARNING)

    def test_console_handler_respects_higher_requested_level(self):
        logger = setup_logging("ERROR", None)

        self.assertEqual(len(logger.handlers), 1)
        self.assertEqual(logger.handlers[0].level, logging.ERROR)

    def test_file_handler_uses_requested_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "sc2am.log"
            logger = setup_logging("DEBUG", log_path)

        self.assertEqual(len(logger.handlers), 2)
        file_handlers = [handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]
        self.assertEqual(len(file_handlers), 1)
        self.assertEqual(file_handlers[0].level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
