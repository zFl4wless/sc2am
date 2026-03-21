"""
SC2AM - SoundCloud to Apple Music automation tool
"""

__version__ = "0.1.0"
__author__ = "zFl4wless"
__description__ = "Automate downloading SoundCloud tracks and importing them to Apple Music"

from sc2am.config_manager import ConfigManager, AppConfig
from sc2am.logger import setup_logging
from sc2am.downloader import Downloader
from sc2am.apple_music import AppleMusicManager
from sc2am.metadata import MetadataWriter
from sc2am.validator import URLValidator

__all__ = [
    'ConfigManager',
    'AppConfig',
    'setup_logging',
    'Downloader',
    'AppleMusicManager',
    'MetadataWriter',
    'URLValidator',
]

