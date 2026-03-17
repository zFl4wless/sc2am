"""
URL validation utilities for sc2am.
"""

import re
import logging
from typing import List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLValidator:
    """Validates SoundCloud and other music platform URLs."""
    
    # Supported platforms
    SOUNDCLOUD_PATTERN = re.compile(
        r'^https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+/?$',
        re.IGNORECASE
    )
    
    SUPPORTED_DOMAINS = {
        'soundcloud.com': 'SoundCloud',
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'spotify.com': 'Spotify',
    }
    
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
            return False, "Invalid URL format"
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            
            if not parsed.scheme or not parsed.netloc:
                return False, "URL is missing scheme or domain"
            
            # Extract domain without www
            domain = parsed.netloc.replace('www.', '')
            
            for supported_domain, platform in URLValidator.SUPPORTED_DOMAINS.items():
                if domain.endswith(supported_domain):
                    return True, platform
            
            return False, f"Unsupported platform: {domain}"
        
        except Exception as e:
            return False, f"URL parsing error: {str(e)}"
    
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
            errors.append((0, f"File not found: {file_path}"))
        except Exception as e:
            errors.append((0, f"Error reading file: {str(e)}"))
        
        return len(errors) == 0, valid_urls, errors

