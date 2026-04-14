import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import sc2am.config_manager as config_manager
from sc2am.config_manager import ConfigManager


class ConfigDefaultTests(unittest.TestCase):
    def test_default_config_data_uses_shared_model_defaults(self):
        with tempfile.TemporaryDirectory() as temp_home:
            home = Path(temp_home)
            with patch.object(config_manager.Path, "home", return_value=home):
                default_config = ConfigManager.default_config_data()

        expected_download_dir = str(home / "Downloads" / "sc2am")
        self.assertEqual(default_config["download_dir"], expected_download_dir)
        self.assertIsNone(default_config["music_library_path"])
        self.assertIsNone(default_config["default_playlist"])
        self.assertTrue(default_config["keep_downloads"])
        self.assertTrue(default_config["open_music_app"])
        self.assertEqual(default_config["log_level"], "INFO")
        self.assertIsNone(default_config["log_file"])

    def test_create_default_config_writes_normalized_yaml(self):
        with tempfile.TemporaryDirectory() as temp_home, tempfile.TemporaryDirectory() as temp_config:
            home = Path(temp_home)
            config_dir = Path(temp_config) / ".sc2am"
            config_file = config_dir / "config.yaml"

            with patch.object(config_manager.Path, "home", return_value=home), patch.object(
                ConfigManager,
                "CONFIG_DIR",
                config_dir,
            ), patch.object(
                ConfigManager,
                "CONFIG_FILE",
                config_file,
            ):
                created_path = ConfigManager.create_default_config(force=True)

            self.assertEqual(created_path, config_file)
            self.assertTrue(config_file.exists())

            written_config = yaml.safe_load(config_file.read_text())
            expected_config = {
                "download_dir": str(home / "Downloads" / "sc2am"),
                "music_library_path": None,
                "default_playlist": None,
                "keep_downloads": True,
                "open_music_app": True,
                "log_level": "INFO",
                "log_file": None,
            }
            self.assertEqual(written_config, expected_config)

    def test_partial_config_load_still_fills_missing_defaults(self):
        with tempfile.TemporaryDirectory() as temp_home, tempfile.TemporaryDirectory() as temp_config:
            home = Path(temp_home)
            config_file = Path(temp_config) / "config.yaml"
            config_file.write_text(
                "default_playlist: Roadtrip\nkeep_downloads: false\n"
            )

            with patch.object(config_manager.Path, "home", return_value=home):
                cfg = ConfigManager.get_config(config_file)

        self.assertEqual(cfg.download_dir, home / "Downloads" / "sc2am")
        self.assertEqual(cfg.default_playlist, "Roadtrip")
        self.assertFalse(cfg.keep_downloads)
        self.assertTrue(cfg.open_music_app)
        self.assertEqual(cfg.log_level, "INFO")


if __name__ == "__main__":
    unittest.main()

