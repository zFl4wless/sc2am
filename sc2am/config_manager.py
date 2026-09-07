"""
Configuration management for sc2am.
Handles loading and validation of configuration from YAML files and environment variables.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError

logger = logging.getLogger(__name__)
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class ConfigurationError(ValueError):
    """Invalid or unreadable user configuration."""


def default_download_dir() -> Path:
    """Return the default download directory for fresh installs."""
    return Path.home() / "Downloads" / "sc2am"


class AppConfig(BaseModel):
    """Application configuration model with validation."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    # Paths
    download_dir: Path = Field(
        default_factory=default_download_dir, description="Directory where MP3s will be downloaded"
    )

    # Apple Music
    music_library_path: Optional[Path] = Field(
        default=None, description="Compatibility setting; currently inactive"
    )
    default_playlist: Optional[str] = Field(
        default=None, description="Default playlist to add imported tracks to"
    )

    # Behavior
    keep_downloads: bool = Field(
        default=True, description="Compatibility setting; downloads are currently always retained"
    )
    open_music_app: bool = Field(
        default=True, description="Automatically open Apple Music after import"
    )
    # Batch behavior
    continue_on_error: bool = Field(
        default=False, description="When True, continue processing remaining URLs if one fails"
    )

    # Workflow defaults
    normalize_metadata: bool = Field(
        default=True,
        description="Compatibility setting; metadata tagging is currently always attempted",
    )
    skip_existing_tracks: bool = Field(
        default=False,
        description="Compatibility setting; Music-library duplicate detection is not implemented",
    )

    # Logging
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file: Optional[Path] = Field(
        default=None, description="Path to log file (if None, only console logging)"
    )

    @field_validator("download_dir", "music_library_path", "log_file", mode="before")
    @classmethod
    def expand_paths(cls, v):
        """Expand home directory and environment variables in paths."""
        if v is None:
            return v
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Path must not be empty")
            v = os.path.expandvars(os.path.expanduser(v))
        return Path(v) if isinstance(v, str) else v

    @field_validator("music_library_path", "log_file", "default_playlist", mode="before")
    @classmethod
    def normalize_optional_values(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator(
        "keep_downloads",
        "open_music_app",
        "continue_on_error",
        "normalize_metadata",
        "skip_existing_tracks",
        mode="before",
    )
    @classmethod
    def normalize_booleans(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            raise ValueError("Use true/false, yes/no, on/off, or 1/0")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        v = v.strip().upper()
        if v not in LOG_LEVELS:
            raise ValueError(f"Log level must be one of {list(LOG_LEVELS)}")
        return v


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
    def get_config(
        config_path: Optional[Path] = None, overrides: Optional[Dict[str, Any]] = None
    ) -> AppConfig:
        """
        Load configuration from file and environment variables.

        Priority (highest to lowest):
        1. Explicit CLI overrides
        2. Environment variables (SC2AM_*)
        3. Selected config file (custom replaces ~/.sc2am/config.yaml)
        4. Built-in defaults

        Args:
            config_path: Optional path to custom config file

        Returns:
            AppConfig: Validated configuration object
        """
        config_dict = {}

        # Load from YAML file
        yaml_path = Path(config_path).expanduser() if config_path else ConfigManager.CONFIG_FILE
        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
        except FileNotFoundError as exc:
            if config_path is not None:
                raise ConfigurationError(f"Configuration file not found: {yaml_path}") from exc
            file_config = None
        except (OSError, UnicodeError) as exc:
            raise ConfigurationError(f"Could not read configuration file: {yaml_path}") from exc
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            location = f" at line {mark.line + 1}" if mark is not None else ""
            raise ConfigurationError(f"Invalid YAML in {yaml_path}{location}.") from exc
        if file_config is not None:
            if not isinstance(file_config, dict) or any(
                not isinstance(key, str) for key in file_config
            ):
                raise ConfigurationError(
                    f"Configuration in {yaml_path} must be a mapping of setting names to values."
                )
            config_dict.update(file_config)

        # Override with environment variables
        env_config = ConfigManager._get_env_config()
        config_dict.update(env_config)
        config_dict.update(overrides or {})

        # Create and return validated config
        try:
            return AppConfig(**config_dict)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
                for error in exc.errors(include_input=False, include_url=False)
            )
            raise ConfigurationError(f"Invalid configuration: {details}") from exc

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
            f"{env_prefix}CONTINUE_ON_ERROR": "continue_on_error",
            f"{env_prefix}NORMALIZE_METADATA": "normalize_metadata",
            f"{env_prefix}SKIP_EXISTING": "skip_existing_tracks",
            f"{env_prefix}LOG_LEVEL": "log_level",
            f"{env_prefix}LOG_FILE": "log_file",
        }

        for env_var, config_key in mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                env_config[config_key] = value

        return env_config

    @staticmethod
    def create_default_config(force: bool = False, config_path: Optional[Path] = None) -> Path:
        """
        Create default configuration file.

        Args:
            force: Overwrite existing config if True

        Returns:
            Path to created config file
        """
        target = Path(config_path).expanduser() if config_path else ConfigManager.CONFIG_FILE
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() and not force:
            logger.info(f"Config file already exists at {target}")
            return target

        with target.open("w" if force else "x", encoding="utf-8") as f:
            yaml.safe_dump(
                ConfigManager.default_config_data(),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        logger.info(f"Created default config at {target}")
        return target
