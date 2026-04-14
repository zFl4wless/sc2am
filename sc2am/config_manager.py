"""
Configuration management for sc2am.
Handles loading and validation of configuration from YAML files and environment variables.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def default_download_dir() -> Path:
    """Return the default download directory for fresh installs."""
    return Path.home() / "Downloads" / "sc2am"


class AppConfig(BaseModel):
    """Application configuration model with validation."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Paths
    download_dir: Path = Field(
        default_factory=default_download_dir,
        description="Directory where MP3s will be downloaded"
    )
    
    # Apple Music
    music_library_path: Optional[Path] = Field(
        default=None,
        description="Path to Apple Music library (auto-detected if not set)"
    )
    default_playlist: Optional[str] = Field(
        default=None,
        description="Default playlist to add imported tracks to"
    )
    
    # Behavior
    keep_downloads: bool = Field(
        default=True,
        description="Keep downloaded MP3 files after import"
    )
    open_music_app: bool = Field(
        default=True,
        description="Automatically open Apple Music after import"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Path to log file (if None, only console logging)"
    )
    
    @field_validator('download_dir', 'log_file', mode='before')
    @classmethod
    def expand_paths(cls, v):
        """Expand home directory and environment variables in paths."""
        if v is None:
            return v
        if isinstance(v, str):
            v = os.path.expandvars(os.path.expanduser(v))
        return Path(v) if isinstance(v, str) else v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        if v.upper() not in LOG_LEVELS:
            raise ValueError(f"Log level must be one of {list(LOG_LEVELS)}")
        return v.upper()


class ConfigManager:
    """Manages loading and merging configuration from multiple sources."""
    
    CONFIG_DIR = Path.home() / ".sc2am"
    CONFIG_FILE = CONFIG_DIR / "config.yaml"

    @staticmethod
    def _serialize_config_value(value: Any) -> Any:
        if isinstance(value, Path):
            return str(value)
        return value

    @staticmethod
    def default_config_data() -> Dict[str, Any]:
        """Build the canonical default configuration as plain YAML-safe data."""
        default_config = AppConfig().model_dump(mode="python")
        return {
            key: ConfigManager._serialize_config_value(value)
            for key, value in default_config.items()
        }

    @staticmethod
    def get_config(config_path: Optional[Path] = None) -> AppConfig:
        """
        Load configuration from file and environment variables.
        
        Priority (highest to lowest):
        1. Environment variables (SC2AM_*)
        2. Custom config file (if provided)
        3. Default config file (~/.sc2am/config.yaml)
        4. Built-in defaults
        
        Args:
            config_path: Optional path to custom config file
            
        Returns:
            AppConfig: Validated configuration object
        """
        config_dict = {}
        
        # Load from YAML file
        yaml_path = config_path or ConfigManager.CONFIG_FILE
        if yaml_path.exists():
            logger.debug(f"Loading config from {yaml_path}")
            try:
                with open(yaml_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config_dict.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file {yaml_path}: {e}")
        
        # Override with environment variables
        env_config = ConfigManager._get_env_config()
        config_dict.update(env_config)
        
        # Create and return validated config
        return AppConfig(**config_dict)
    
    @staticmethod
    def _get_env_config() -> Dict[str, Any]:
        """Extract configuration from environment variables (SC2AM_*)."""
        env_config = {}
        env_prefix = "SC2AM_"
        
        mapping = {
            f"{env_prefix}DOWNLOAD_DIR": "download_dir",
            f"{env_prefix}MUSIC_LIBRARY": "music_library_path",
            f"{env_prefix}PLAYLIST": "default_playlist",
            f"{env_prefix}KEEP_DOWNLOADS": "keep_downloads",
            f"{env_prefix}OPEN_MUSIC": "open_music_app",
            f"{env_prefix}LOG_LEVEL": "log_level",
            f"{env_prefix}LOG_FILE": "log_file",
        }
        
        for env_var, config_key in mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Handle boolean values
                if config_key in ["keep_downloads", "open_music_app"]:
                    env_config[config_key] = value.lower() in ['true', '1', 'yes']
                else:
                    env_config[config_key] = value
        
        return env_config
    
    @staticmethod
    def create_default_config(force: bool = False) -> Path:
        """
        Create default configuration file.
        
        Args:
            force: Overwrite existing config if True
            
        Returns:
            Path to created config file
        """
        ConfigManager.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        if ConfigManager.CONFIG_FILE.exists() and not force:
            logger.info(f"Config file already exists at {ConfigManager.CONFIG_FILE}")
            return ConfigManager.CONFIG_FILE
        
        with open(ConfigManager.CONFIG_FILE, 'w') as f:
            yaml.safe_dump(
                ConfigManager.default_config_data(),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        logger.info(f"Created default config at {ConfigManager.CONFIG_FILE}")
        return ConfigManager.CONFIG_FILE


