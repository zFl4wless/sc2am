"""
URL validation utilities for sc2am.
"""

import logging
from typing import List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLValidator:
    """Validates SoundCloud and other music platform URLs."""

    # Supported platforms
    SUPPORTED_DOMAINS = {
        'soundcloud.com': 'SoundCloud',
        'www.soundcloud.com': 'SoundCloud',
        'youtube.com': 'YouTube',
        'www.youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'spotify.com': 'Spotify',
        'www.spotify.com': 'Spotify',
    }

    SOUNDCLOUD_TRACK_HELP = (
        "Only SoundCloud track URLs are supported. Please use a URL like "
        "https://soundcloud.com/<artist>/<track>"
    )

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Validate if URL is a supported music platform.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, platform_name)
        """
        if not url or not isinstance(url, str):
            return False, "Please provide a valid URL."

        url = url.strip()

        if not url:
            return False, "Please provide a valid URL."

        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            
            if parsed.scheme not in ("http", "https"):
                return False, "Please use a URL that starts with http:// or https://."

            if not parsed.netloc:
                return False, "The URL is missing a domain name."

            domain = (parsed.hostname or "").lower()
            if not domain:
                return False, "The URL is missing a domain name."

            if domain in {"soundcloud.com", "www.soundcloud.com"}:
                path_segments = [segment for segment in parsed.path.split('/') if segment]
                if len(path_segments) != 2:
                    return False, URLValidator.SOUNDCLOUD_TRACK_HELP

                if any(not segment.strip() for segment in path_segments):
                    return False, URLValidator.SOUNDCLOUD_TRACK_HELP

                return True, "SoundCloud"

            for supported_domain, platform in URLValidator.SUPPORTED_DOMAINS.items():
                if domain == supported_domain:
                    if platform != "SoundCloud":
                        return False, "Only SoundCloud track URLs are supported right now."
                    return True, platform
            
            return False, "Only SoundCloud track URLs are supported right now."

        except Exception as e:
            logger.exception("URL validation failed")
            return False, "The URL could not be parsed. Please check the format and try again."

    @staticmethod
    def validate_batch_file(file_path: str) -> Tuple[bool, List[str], List[Tuple[int, str]]]:
        """
        Validate a file containing URLs (one per line).
        
        Args:
            file_path: Path to file with URLs
            
        Returns:
            Tuple of (all_valid, valid_urls, errors)
            errors: List of (line_number, error_message)
        """
        valid_urls = []
        errors = []
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):  # Skip empty lines and comments
                        continue
                    
                    is_valid, platform = URLValidator.validate_url(line)
                    if is_valid:
                        valid_urls.append(line)
                    else:
                        errors.append((line_num, platform))
        
        except FileNotFoundError:
            errors.append((0, "Batch file not found. Please check the file path and try again."))
        except Exception as e:
            logger.exception("Failed to read batch file")
            errors.append((0, "The batch file could not be read. Please check the file and try again."))

        return len(errors) == 0, valid_urls, errors

